import { Button, Input, InputNumber, Select, Typography } from 'antd';
import { useDirectorStore } from '../store/useDirectorStore';
import { directorDark } from '../../theme';
import type { CameraMotion } from '../types';

const { Text } = Typography;

const SHOT_TYPES = [
  { value: 'close-up', label: '特写' },
  { value: 'medium shot', label: '中景' },
  { value: 'wide shot', label: '远景' },
  { value: 'over-shoulder', label: '过肩' },
];

const MOTIONS: Array<{ value: CameraMotion | 'static'; label: string }> = [
  { value: 'static', label: '静止' },
  { value: 'push_in', label: '推进' },
  { value: 'pull_out', label: '拉远' },
  { value: 'pan', label: '横摇' },
  { value: 'tilt', label: '俯仰' },
  { value: 'orbit', label: '环绕' },
  { value: 'tracking', label: '跟随' },
];

const TIMES = [
  { value: '', label: '未设置' },
  { value: 'dawn', label: '清晨' },
  { value: 'day', label: '白天' },
  { value: 'dusk', label: '黄昏' },
  { value: 'night', label: '夜晚' },
];

export default function ShotInspector() {
  const sceneName = useDirectorStore((s) => s.sceneName);
  const shotDuration = useDirectorStore((s) => s.shotDuration ?? 4);
  const shotDescription = useDirectorStore((s) => s.shotDescription ?? '');
  const shotType = useDirectorStore((s) => s.shotType ?? 'medium shot');
  const cameraMovement = useDirectorStore((s) => s.cameraMovement ?? 'static');
  const emotion = useDirectorStore((s) => s.emotion ?? '');
  const timeOfDay = useDirectorStore((s) => s.timeOfDay ?? '');
  const objects = useDirectorStore((s) => s.objects);
  const activeCamera = useDirectorStore((s) => s.activeCamera);
  const updateShotMeta = useDirectorStore((s) => s.updateShotMeta);
  const lookAt = useDirectorStore((s) => s.lookAt);
  const addCamera = useDirectorStore((s) => s.addCamera);

  const lead = objects.find((o) => o.characterId);

  return (
    <div>
      <Text strong style={{ color: directorDark.text }}>镜头</Text>
      <div style={{ marginTop: 10 }}>
        <Field label="镜头名称">
          <Input
            size="small"
            value={sceneName}
            onChange={(e) => updateShotMeta({ sceneName: e.target.value })}
          />
        </Field>
        <Field label="时长（秒）">
          <InputNumber
            size="small"
            min={1}
            max={20}
            value={shotDuration}
            style={{ width: '100%' }}
            onChange={(v) => updateShotMeta({ shotDuration: typeof v === 'number' ? v : 4 })}
          />
        </Field>
        <Field label="角色">
          <div style={{ color: directorDark.text, fontSize: 12 }}>
            {lead ? lead.name : '还没有角色，请从左侧创建并加入镜头'}
          </div>
        </Field>
        <Field label="动作">
          <div style={{ color: directorDark.muted, fontSize: 12 }}>
            {lead?.animation || lead?.pose || '未设置'}
          </div>
        </Field>
        <Field label="景别">
          <Select
            size="small"
            style={{ width: '100%' }}
            value={shotType}
            options={SHOT_TYPES}
            onChange={(v) => updateShotMeta({ shotType: v })}
          />
        </Field>
        <Field label="镜头运动">
          <Select
            size="small"
            style={{ width: '100%' }}
            value={cameraMovement}
            options={MOTIONS}
            onChange={(v) => updateShotMeta({ cameraMovement: v })}
          />
        </Field>
        <Field label="时间">
          <Select
            size="small"
            style={{ width: '100%' }}
            value={timeOfDay}
            options={TIMES}
            onChange={(v) => updateShotMeta({ timeOfDay: v })}
          />
        </Field>
        <Field label="情绪 / 描述">
          <Input.TextArea
            rows={3}
            value={shotDescription || emotion}
            placeholder="女主走进咖啡厅，中景，略显疲惫"
            onChange={(e) => updateShotMeta({ shotDescription: e.target.value, emotion: e.target.value })}
          />
        </Field>
        <Button
          size="small"
          block
          style={{ marginBottom: 8 }}
          disabled={!lead}
          onClick={() => {
            if (!lead) return;
            lookAt(activeCamera, [lead.position[0], lead.position[1] + 1.45, lead.position[2]]);
          }}
        >
          摄像机对准角色
        </Button>
        <Button size="small" block onClick={() => addCamera()}>
          添加机位
        </Button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <Text style={{ fontSize: 12, color: directorDark.muted }}>{label}</Text>
      <div style={{ marginTop: 4 }}>{children}</div>
    </div>
  );
}
