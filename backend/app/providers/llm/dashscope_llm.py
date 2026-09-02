"""DashScope LLM Provider(通过 OpenAI 兼容接口)。

DashScope 提供 OpenAI 兼容端点 https://dashscope.aliyuncs.com/compatible-mode/v1,
因此用 openai SDK 即可调用通义千问系列模型。
该实现同样适用于任何 OpenAI 兼容服务(DeepSeek 等),仅需改 base_url/api_key/model 配置。

调用约定:
- system prompt 由 providers/llm/prompts.py 按 task 提供,严格约束输出 JSON schema
- user message 为 context 的 JSON 序列化
- 开启 response_format={"type":"json_object"} 强制 JSON 输出
- 解析失败时容错:用正则提取首个 {...} 块,仍失败则抛错让 Orchestrator 标记 FAILED
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict

from ...core.config import settings
from ...core.logging import logger
from .base import LLMProvider
from .prompts import PROMPTS


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Dict[str, Any]:
    """从模型输出中提取 JSON dict,容错处理 markdown 代码块与多余文字。"""
    text = text.strip()
    # 去掉可能的 ```json ... ``` 包裹
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 退而求其次:正则提取首个 {} 块
    m = _JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 返回非合法 JSON: {e}\n原始: {text[:300]}")
    raise ValueError(f"LLM 返回中未找到 JSON: {text[:300]}")


class DashScopeLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        # 延迟 import,避免未配置真实 LLM 时也强依赖 openai 包
        from openai import OpenAI

        self.api_key = api_key or settings.llm_api_key or settings.dashscope_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        if not self.api_key:
            raise RuntimeError("DashScope LLM 缺少 API Key(请配置 .env: LLM_API_KEY 或 DASHSCOPE_API_KEY)")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=120)

    async def generate(self, *, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if task not in PROMPTS:
            raise ValueError(f"未知 LLM 任务类型: {task}")
        system_prompt = PROMPTS[task]
        # 占位符替换:让 prompt 模板可注入 settings 配置(如 {tts_language} → zh-CN)
        # 这是通用机制,不在 prompt 里写死业务参数,通过 .env 切换即可改变 LLM 输出
        if "{tts_language}" in system_prompt:
            system_prompt = system_prompt.replace("{tts_language}", settings.tts_language)
        # context 序列化为 user message
        user_msg = json.dumps(context, ensure_ascii=False, indent=2)
        logger.info("LLM 调用 task=%s model=%s tts_language=%s", task, self.model, settings.tts_language)

        # openai SDK 是同步接口,用 asyncio.to_thread 包裹避免阻塞 event loop
        import asyncio

        def _call() -> str:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            return resp.choices[0].message.content or ""

        # Retry:DashScope 偶发超时/限流时重试,指数退避,耗尽抛错让 Orchestrator 标记 FAILED
        max_retries = 2
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                content = await asyncio.to_thread(_call)
                logger.debug("LLM 原始返回(task=%s): %s", task, content[:200])
                return _extract_json(content)
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    wait = 1.5 ** attempt
                    logger.warning(
                        "LLM 调用失败 task=%s attempt=%d/%d,%.1fs 后重试: %s",
                        task, attempt + 1, max_retries + 1, wait, e,
                    )
                    await asyncio.sleep(wait)
        raise RuntimeError(
            f"LLM 调用 {max_retries + 1} 次仍失败 task={task}: {last_err}"
        )
