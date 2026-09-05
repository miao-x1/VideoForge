import { Button, InputNumber, Slider, Space, Typography, message } from 'antd';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { useDirectorStore } from '../store/useDirectorStore';
import type { CharacterAsset } from '../characters/types';
import type { SceneObject } from '../types';

const { Text } = Typography;

export default function AnimationTimeline({ object, asset }: { object: SceneObject; asset: CharacterAsset }) {
  const updateObject = useDirectorStore((s) => s.updateObject);
  const saveCustomAnimation = useCharacterLibrary((s) => s.saveCustomAnimation);
  const removeCustomAnimation = useCharacterLibrary((s) => s.removeCustomAnimation);
  const allAnims = useCharacterLibrary((s) => s.customAnimations);
  const mine = allAnims.filter((a) => !a.characterId || a.characterId === asset.id);
  const current = mine.find((a) => a.id === object.customAnimationId) ?? null;
  const time = object.customAnimationTime ?? 0;
  const duration = current?.duration ?? 2;

  return (
    <div>
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
        用当前姿势作为关键帧。保存后进入「我的动作」，可在任意分镜回放。
      </Text>
      <Space wrap style={{ marginBottom: 8 }}>
        <Button
          size="small"
          onClick={() => {
            const keys = current?.keys ?? [];
            const nextKeys = [...keys, { time, bones: { ...(object.bonePose ?? {}) } }].sort((a, b) => a.time - b.time);
            const saved = saveCustomAnimation({
              id: current?.id,
              name: current?.name ?? `${asset.name} 动作`,
              characterId: asset.id,
              skeletonType: asset.skeletonType,
              duration,
              keys: nextKeys,
            });
            updateObject(object.id, { customAnimationId: saved.id, pose: 'custom', animationPlaying: false });
            message.success(`已加入第 ${nextKeys.length} 帧`);
          }}
        >
          添加关键帧
        </Button>
        <Button
          size="small"
          disabled={!current || current.keys.length === 0}
          onClick={() => {
            if (!current) return;
            const keys = current.keys.filter((k) => Math.abs(k.time - time) > 0.04);
            saveCustomAnimation({ ...current, keys });
          }}
        >
          删除当前帧
        </Button>
        <Button
          size="small"
          disabled={!current || current.keys.length === 0}
          onClick={() => {
            if (!current) return;
            const nearest = [...current.keys].sort((a, b) => Math.abs(a.time - time) - Math.abs(b.time - time))[0];
            if (!nearest) return;
            const keys = [...current.keys, { time: Math.min(duration, nearest.time + 0.2), bones: { ...nearest.bones } }].sort((a, b) => a.time - b.time);
            saveCustomAnimation({ ...current, keys });
          }}
        >
          复制当前帧
        </Button>
      </Space>
      <Text type="secondary" style={{ fontSize: 12 }}>时长（秒）</Text>
      <InputNumber
        size="small"
        min={0.4}
        max={30}
        step={0.2}
        style={{ width: '100%', margin: '4px 0 8px' }}
        value={duration}
        onChange={(v) => {
          if (!current || typeof v !== 'number') return;
          saveCustomAnimation({ ...current, duration: v });
        }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>时间轴 {time.toFixed(2)}s · {current?.keys.length ?? 0} 帧</Text>
      <Slider
        min={0}
        max={duration}
        step={0.02}
        value={time}
        onChange={(v) => updateObject(object.id, { customAnimationTime: v, customAnimationPlaying: false, customAnimationId: current?.id ?? object.customAnimationId, animationPlaying: false, pose: 'custom' })}
      />
      <Space style={{ marginTop: 6 }}>
        <Button
          size="small"
          type="primary"
          disabled={!current || current.keys.length < 2}
          onClick={() => updateObject(object.id, { customAnimationPlaying: true, customAnimationId: current?.id, animationPlaying: false, pose: 'custom' })}
        >
          播放
        </Button>
        <Button size="small" onClick={() => updateObject(object.id, { customAnimationPlaying: false })}>
          暂停
        </Button>
        <Button
          size="small"
          onClick={() => {
            const name = window.prompt('动作名称', current?.name ?? `${asset.name} 动作`);
            if (!name) return;
            const saved = saveCustomAnimation({
              id: current?.id,
              name,
              characterId: asset.id,
              skeletonType: asset.skeletonType,
              duration,
              keys: current?.keys ?? [{ time: 0, bones: { ...(object.bonePose ?? {}) } }],
            });
            updateObject(object.id, { customAnimationId: saved.id });
            message.success('已保存到我的动作');
          }}
        >
          保存动作
        </Button>
      </Space>
      {mine.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>我的动作</Text>
          {mine.map((a) => (
            <div key={a.id} style={{ display: 'flex', gap: 4, marginTop: 4 }}>
              <Button
                size="small"
                type={object.customAnimationId === a.id ? 'primary' : 'default'}
                style={{ flex: 1 }}
                onClick={() => updateObject(object.id, { customAnimationId: a.id, customAnimationTime: 0, customAnimationPlaying: false, pose: 'custom', animationPlaying: false })}
              >
                {a.name}（{a.keys.length}帧）
              </Button>
              <Button size="small" danger onClick={() => {
                if (object.customAnimationId === a.id) updateObject(object.id, { customAnimationId: null });
                removeCustomAnimation(a.id);
              }}>删</Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
