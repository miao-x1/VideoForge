import { useState } from 'react';
import { Alert, Input, Modal, Tabs, Typography, message } from 'antd';
import { CHARACTER_TEMPLATES, officialReadyCount } from '../characters/templates';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { useDirectorStore } from '../store/useDirectorStore';
import { autoRigFromUrl } from '../characters/rig/autoRig';
import { colors, radius } from '../../theme';

const { Text } = Typography;

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsDataURL(file);
  });
}

function OfficialPane({ onDone }: { onDone: () => void }) {
  const addOfficialTemplate = useDirectorStore((s) => s.addOfficialTemplate);
  const groups = [
    { key: 'human', label: '人物', items: CHARACTER_TEMPLATES.filter((t) => t.characterType === 'human') },
    { key: 'animal', label: '动物', items: CHARACTER_TEMPLATES.filter((t) => t.characterType === 'animal') },
    { key: 'special', label: '特殊角色', items: CHARACTER_TEMPLATES.filter((t) => t.characterType === 'special') },
  ];
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 10 }}>
        官方只提供 {officialReadyCount()} 个已绑定骨骼的基础角色。点选后会写入「我的角色」并放入当前分镜。
      </Text>
      {groups.map((group) => (
        <div key={group.key} style={{ marginBottom: 14 }}>
          <Text strong style={{ fontSize: 13 }}>{group.label}</Text>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
            {group.items.filter((t) => t.available).map((t) => (
              <button
                key={t.id}
                type="button"
                disabled={!t.available}
                title={t.note}
                onClick={() => {
                  const id = addOfficialTemplate(t.id);
                  if (id) {
                    message.success(`已加入镜头：${t.name}`);
                    onDone();
                  }
                }}
                style={{
                  textAlign: 'left',
                  padding: 10,
                  borderRadius: radius.item,
                  border: `1px solid ${colors.border}`,
                  background: t.available ? '#fff' : '#f5f5f5',
                  cursor: t.available ? 'pointer' : 'not-allowed',
                  opacity: t.available ? 1 : 0.65,
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{t.name}</div>
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  {t.available ? 'Animation Ready' : '未实现'}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ModelPane({ onDone }: { onDone: () => void }) {
  const createFromRiggedModel = useCharacterLibrary((s) => s.createFromRiggedModel);
  const instanceCharacter = useDirectorStore((s) => s.instanceCharacter);
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string>('');
  const [name, setName] = useState('');

  return (
    <div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="目前稳定支持 GLB / GLTF。FBX 尚未接入。"
        description="有骨骼则直接使用，不会重复绑定。没有骨骼会明确失败，不会假装成功。"
      />
      <Text type="secondary" style={{ fontSize: 12 }}>角色名称</Text>
      <Input size="small" value={name} onChange={(e) => setName(e.target.value)} placeholder="我的角色" style={{ margin: '4px 0 10px' }} />
      <input
        type="file"
        accept=".glb,.gltf"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          e.target.value = '';
          if (!file) return;
          setBusy(true);
          setLog('正在检查模型…');
          try {
            const url = await readAsDataUrl(file);
            setLog('模型检查 → 骨骼检测 → 自动绑定…');
            const result = await autoRigFromUrl(url);
            if (!result.ok) {
              setLog(result.error ?? '绑定失败');
              message.error(result.error ?? '该模型无法自动绑定');
              return;
            }
            const asset = createFromRiggedModel({
              name: name.trim() || file.name.replace(/\.(glb|gltf)$/i, ''),
              modelUrl: url,
              sourceType: 'uploaded_3d',
              skeletonType: result.skeletonType,
              animationSetId: result.animationSetId,
              rigStatus: result.rigStatus,
              animationStatus: result.animationStatus,
              note: result.inspection.message,
            });
            instanceCharacter(asset.id);
            setLog(`${result.inspection.message} 已进入我的角色：${asset.id}`);
            message.success('角色已准备完成');
            onDone();
          } catch (err: unknown) {
            const text = err instanceof Error ? err.message : '模型读取失败';
            setLog(text);
            message.error(text);
          } finally {
            setBusy(false);
          }
        }}
      />
      {busy && <div style={{ marginTop: 8, fontSize: 12 }}>处理中…</div>}
      {log && <Alert style={{ marginTop: 10 }} type={log.includes('失败') || log.includes('无法') ? 'error' : 'success'} message={log} />}
    </div>
  );
}

export default function CreateCharacterModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal title="创建角色" open={open} onCancel={onClose} footer={null} width={640} destroyOnClose>
      <Tabs
        items={[
          { key: 'official', label: '基础角色', children: <OfficialPane onDone={onClose} /> },
          { key: 'model', label: '上传3D模型', children: <ModelPane onDone={onClose} /> },
        ]}
      />
    </Modal>
  );
}
