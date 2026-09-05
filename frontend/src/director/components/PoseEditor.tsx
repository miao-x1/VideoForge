import { Button, Collapse, InputNumber, Space, Typography, message } from 'antd';
import type { BonePoseMap, CharacterAsset } from '../characters/types';
import { controlsForSkeleton } from '../characters/bones';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { useDirectorStore } from '../store/useDirectorStore';
import type { SceneObject } from '../types';

const { Text } = Typography;

const PRIMARY = new Set(['head', 'neck', 'spine', 'leftArm', 'rightArm', 'leftUpLeg', 'rightUpLeg']);

const IK_POSES: Record<string, BonePoseMap> = {
  rightHandUp: { rightArm: [-2.2, 0.1, -0.2], rightForeArm: [0, 0, -0.45], rightHand: [0, 0, -0.15] },
  leftHandUp: { leftArm: [-2.2, -0.1, 0.2], leftForeArm: [0, 0, 0.45], leftHand: [0, 0, 0.15] },
  rightReach: { rightArm: [-1.2, 0.4, -0.1], rightForeArm: [-0.6, 0, -0.2] },
  leftReach: { leftArm: [-1.2, -0.4, 0.1], leftForeArm: [-0.6, 0, 0.2] },
};

function BoneRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: [number, number, number];
  onChange: (next: [number, number, number]) => void;
}) {
  return (
    <div style={{ marginBottom: 8 }}>
      <Text type="secondary" style={{ fontSize: 11 }}>{label}</Text>
      <div style={{ display: 'flex', gap: 4, marginTop: 2 }}>
        {(['X', 'Y', 'Z'] as const).map((axis, i) => (
          <InputNumber
            key={axis}
            size="small"
            addonBefore={axis}
            step={0.05}
            value={Number(value[i].toFixed(2))}
            style={{ flex: 1 }}
            onChange={(v) => {
              const next: [number, number, number] = [value[0], value[1], value[2]];
              next[i] = typeof v === 'number' ? v : 0;
              onChange(next);
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function PoseEditor({ object, asset }: { object: SceneObject; asset: CharacterAsset }) {
  const updateObject = useDirectorStore((s) => s.updateObject);
  const savePose = useCharacterLibrary((s) => s.savePose);
  const savedPosesAll = useCharacterLibrary((s) => s.savedPoses);
  const savedPoses = savedPosesAll.filter((p) => p.characterId === asset.id);
  const removePose = useCharacterLibrary((s) => s.removePose);
  const pose = object.bonePose ?? {};
  const controls = controlsForSkeleton(asset.skeletonType);
  const humanoid = asset.characterType !== 'animal';

  const setBone = (id: string, value: [number, number, number]) => {
    updateObject(object.id, {
      bonePose: { ...pose, [id]: value },
      pose: 'custom',
      animationPlaying: false,
      customAnimationId: null,
    });
  };

  const applyIk = (key: keyof typeof IK_POSES) => {
    updateObject(object.id, {
      bonePose: { ...pose, ...IK_POSES[key] },
      pose: 'custom',
      animationPlaying: false,
      customAnimationId: null,
    });
  };

  const renderControls = (ids?: Set<string>) =>
    controls
      .filter((c) => !ids || ids.has(c.id))
      .map((control) => (
        <BoneRow
          key={control.id}
          label={control.label}
          value={pose[control.id] ?? [0, 0, 0]}
          onChange={(v) => setBone(control.id, v)}
        />
      ));

  return (
    <div>
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
        姿势写在当前分镜实例上。保存后进入「我的姿势」，下次打开仍在。
      </Text>
      {humanoid && (
        <Space wrap style={{ marginBottom: 10 }}>
          <Button size="small" onClick={() => applyIk('rightHandUp')}>右手抬起</Button>
          <Button size="small" onClick={() => applyIk('leftHandUp')}>左手抬起</Button>
          <Button size="small" onClick={() => applyIk('rightReach')}>右手前伸</Button>
          <Button size="small" onClick={() => applyIk('leftReach')}>左手前伸</Button>
        </Space>
      )}
      {renderControls(PRIMARY)}
      <Collapse
        size="small"
        items={[{ key: 'more', label: '更多关节', children: renderControls() }]}
      />
      <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
        <Button
          size="small"
          block
          onClick={() => {
            updateObject(object.id, { bonePose: {}, pose: 'stand', animation: 'idle', animationPlaying: true, customAnimationId: null });
          }}
        >
          重置姿势
        </Button>
        <Button
          size="small"
          block
          onClick={() => {
            const name = window.prompt('姿势名称', `${asset.name} 姿势`);
            if (!name) return;
            savePose(asset.id, name, pose);
            message.success('姿势已保存');
          }}
        >
          保存自定义姿势
        </Button>
      </Space>
      {savedPoses.map((p) => (
        <div key={p.id} style={{ display: 'flex', gap: 4, marginTop: 4 }}>
          <Button
            size="small"
            style={{ flex: 1 }}
            onClick={() => updateObject(object.id, { bonePose: p.bones, pose: 'custom', animationPlaying: false, customAnimationId: null })}
          >
            {p.name}
          </Button>
          <Button size="small" danger onClick={() => removePose(p.id)}>删</Button>
        </div>
      ))}
    </div>
  );
}
