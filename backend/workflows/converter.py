"""UI Workflow → API Format 转换器。

官方模板是 UI Format(带坐标/连线表/子图定义),程序调用 Cloud ComfyUI 必须用 API Format:
  { "<node_id>": {"class_type": "...", "inputs": {"widget": value | ["<origin_id>", slot]}} }

打包子图(subgraph)在 API Format 中不存在,必须展开:
  - 子图内部节点以 "<实例ID>:<内部ID>" 作为新节点键
  - 子图输入槽(内部连线 origin_id == -10)由外部连线或提升 widget 值填充
  - 子图输出槽(target_id == -20)重定向到内部源节点

返回的 subgraph_inputs 映射供 Adapter 做业务参数注入:
  {(实例ID, 输入名): [(内部节点键, 输入字段名), ...]}
"""
from __future__ import annotations


def _link_parts(link) -> tuple:
    """兼容两种连线格式:list [id, origin, slot, target, slot, type] 或 dict。"""
    if isinstance(link, dict):
        return link["origin_id"], link["origin_slot"], link["target_id"], link["target_slot"]
    return link[1], link[2], link[3], link[4]


def _input_field(node_inputs: list[dict], slot: int) -> str:
    """节点输入槽号 → 输入字段名。"""
    if 0 <= slot < len(node_inputs):
        return node_inputs[slot]["name"]
    raise ValueError(f"输入槽越界: slot={slot}, fields={[i.get('name') for i in node_inputs]}")


def ui_to_api(workflow: dict) -> tuple[dict, dict]:
    """UI Format Workflow → (API Format prompt, 子图输入映射)。

    Args:
        workflow: 官方模板 JSON(已解析的 dict)

    Returns:
        api_prompt: {"<node_id>": {"class_type", "inputs"}}
        subgraph_inputs: {(instance_id, input_name): [(api_key, field_name), ...]}
    """
    subgraph_defs = {
        sg["id"]: sg for sg in (workflow.get("definitions") or {}).get("subgraphs", [])
    }
    nodes_by_id = {n["id"]: n for n in workflow.get("nodes", [])}
    api: dict = {}
    subgraph_inputs: dict = {}
    # 子图实例输出映射: instance_id -> {输出槽: (内部节点键, 内部输出槽)}
    instance_outputs: dict = {}

    # ---- Pass 1: 建立所有节点骨架 + 子图内部连线 + 输入映射 ----
    for node in workflow.get("nodes", []):
        if node["type"] not in subgraph_defs:
            entry = {"class_type": node["type"], "inputs": {}}
            for wname, wval in (node.get("widgets_values_named") or {}).items():
                entry["inputs"][wname] = wval
            api[str(node["id"])] = entry

    for node in workflow.get("nodes", []):
        if node["type"] not in subgraph_defs:
            continue
        sg = subgraph_defs[node["type"]]
        prefix = str(node["id"])
        inner_inputs = {n["id"]: n.get("inputs", []) for n in sg.get("nodes", [])}

        for inner in sg.get("nodes", []):
            key = f"{prefix}:{inner['id']}"
            entry = {"class_type": inner["type"], "inputs": {}}
            for wname, wval in (inner.get("widgets_values_named") or {}).items():
                entry["inputs"][wname] = wval
            api[key] = entry

        sg_input_names = {i: inp["name"] for i, inp in enumerate(sg.get("inputs", []))}
        outputs: dict = {}
        for link in sg.get("links", []):
            origin_id, origin_slot, target_id, target_slot = _link_parts(link)
            if origin_id == -10:
                # 子图输入槽 → 内部目标
                iname = sg_input_names[origin_slot]
                key = f"{prefix}:{target_id}"
                field = _input_field(inner_inputs[target_id], target_slot)
                subgraph_inputs.setdefault((node["id"], iname), []).append((key, field))
            elif target_id == -20:
                # 子图输出 ← 内部源
                outputs[target_slot] = (f"{prefix}:{origin_id}", origin_slot)
            else:
                key = f"{prefix}:{target_id}"
                field = _input_field(inner_inputs[target_id], target_slot)
                api[key]["inputs"][field] = [f"{prefix}:{origin_id}", origin_slot]
        instance_outputs[node["id"]] = outputs

    # ---- Pass 2: 外部连线(普通↔普通 / 普通→子图 / 子图→普通 / 子图→子图) ----
    for link in workflow.get("links", []):
        origin_id, origin_slot, target_id, target_slot = _link_parts(link)
        origin_node = nodes_by_id.get(origin_id)
        target_node = nodes_by_id.get(target_id)
        if origin_node is None or target_node is None:
            continue

        # 解析连线起点(子图实例 → 输出槽映射后的内部节点)
        if origin_node["type"] in subgraph_defs:
            out = instance_outputs[origin_id].get(origin_slot)
            if out is None:
                raise ValueError(f"子图实例 {origin_id} 缺少输出槽 {origin_slot}")
            origin_ref: list = [out[0], out[1]]
        else:
            origin_ref = [str(origin_id), origin_slot]

        # 解析连线终点(子图实例 → 输入名映射后的内部节点)
        if target_node["type"] in subgraph_defs:
            target_inputs = target_node.get("inputs", [])
            iname = _input_field(target_inputs, target_slot)
            for key, field in subgraph_inputs.get((target_id, iname), []):
                api[key]["inputs"][field] = origin_ref
        else:
            field = _input_field(target_node.get("inputs", []), target_slot)
            api[str(target_id)]["inputs"][field] = origin_ref

    # ---- Pass 3: 子图实例上的提升 widget 值(未被外部连线覆盖的输入) ----
    for node in workflow.get("nodes", []):
        if node["type"] not in subgraph_defs:
            continue
        for wname, wval in (node.get("widgets_values_named") or {}).items():
            for key, field in subgraph_inputs.get((node["id"], wname), []):
                # 外部连线(Pass 2)已写入 list 引用则跳过,否则填充默认 widget 值
                current = api[key]["inputs"].get(field)
                if not isinstance(current, list):
                    api[key]["inputs"][field] = wval

    return api, subgraph_inputs
