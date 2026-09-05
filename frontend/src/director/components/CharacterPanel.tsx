import { Button, Checkbox, Input, InputNumber, Select, Space, Tabs, Typography, message } from 'antd';
import { useDirectorStore } from '../store/useDirectorStore';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { HAIR_STYLE_OPTIONS } from '../characters/templates';
import { clipsForCharacter } from '../characters/animations';
import { posesForCharacter, getPosePreset } from '../characters/poses';
import type { Vec3 } from '../types';
import type { BodyType, CharacterAsset, ClipId } from '../characters/types';
import PoseEditor from './PoseEditor';
import AnimationTimeline from './AnimationTimeline';
import { autoRigFromUrl } from '../characters/rig/autoRig';

const { Text } = Typography;

function VecFields({
  label,
  value,
  step,
  onChange,
}: {
  label: string;
  value: Vec3;
  step: number;
  onChange: (next: Vec3) => void;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
        {(['X', 'Y', 'Z'] as const).map((name, i) => (
          <InputNumber
            key={name}
            size="small"
            addonBefore={name}
            value={Number((value?.[i] ?? 0).toFixed(3))}
            step={step}
            style={{ flex: 1 }}
            onChange={(v) => {
              const next: Vec3 = [...value];
              next[i] = typeof v === 'number' ? v : 0;
              onChange(next);
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function CharacterPanel({ instanceId, characterId }: { instanceId: string; characterId: string }) {
  const object = useDirectorStore((s) => s.objects.find((o) => o.id === instanceId));
  const updateTransform = useDirectorStore((s) => s.updateTransform);
  const updateObject = useDirectorStore((s) => s.updateObject);
  const duplicateInstance = useDirectorStore((s) => s.duplicateInstance);
  const instanceCharacter = useDirectorStore((s) => s.instanceCharacter);
  const asset = useCharacterLibrary((s) => s.characters.find((c) => c.id === characterId));
  const rename = useCharacterLibrary((s) => s.rename);
  const updateAppearance = useCharacterLibrary((s) => s.updateAppearance);
  const setBody = useCharacterLibrary((s) => s.setBody);
  const updateCharacter = useCharacterLibrary((s) => s.updateCharacter);
  const duplicateAsset = useCharacterLibrary((s) => s.duplicate);

  if (!object || !asset) {
    return <Text type="danger">角色资产缺失（{characterId}）</Text>;
  }

  const clips = clipsForCharacter(asset.characterType, asset.animationSetId, asset.skeletonType);
  const poses = posesForCharacter(asset.characterType, asset.skeletonType);
  const hairOptions = HAIR_STYLE_OPTIONS.filter((h) => h.gender === 'any' || h.gender === asset.gender);

  return (
    <div style={{ marginTop: 8 }}>
      <Text strong>角色</Text>
      <div style={{ margin: '6px 0 8px', fontSize: 12, color: '#8c8c8c', wordBreak: 'break-all' }}>
        {asset.id}
      </div>
      <Text type="secondary" style={{ fontSize: 12 }}>角色名称</Text>
      <Input
        size="small"
        value={asset.name}
        style={{ margin: '4px 0 8px' }}
        onChange={(e) => {
          rename(asset.id, e.target.value);
          updateObject(object.id, { name: e.target.value });
        }}
      />
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
        {asset.characterType} · {asset.sourceType} · {asset.rigStatus}/{asset.animationStatus}
      </Text>

      <Tabs
        size="small"
        items={[
          {
            key: 'transform',
            label: '位置',
            children: (
              <>
                <VecFields label="位置" value={object.position} step={0.1} onChange={(position) => updateTransform(object.id, { position })} />
                <VecFields label="旋转" value={object.rotation} step={0.05} onChange={(rotation) => updateTransform(object.id, { rotation })} />
                <VecFields label="缩放" value={object.scale} step={0.05} onChange={(scale) => updateTransform(object.id, { scale })} />
              </>
            ),
          },
          {
            key: 'pose',
            label: '姿势',
            children: (
              <>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                  {poses.filter((pose) => pose.implemented).map((pose) => (
                    <Button
                      key={pose.id}
                      size="small"
                      type={object.pose === pose.id ? 'primary' : 'default'}
                      onClick={() => {
                        const preset = getPosePreset(pose.id);
                        updateObject(object.id, {
                          pose: pose.id,
                          animation: pose.clipId,
                          animationPlaying: pose.playing,
                          bonePose: preset?.bones ?? (pose.id === 'custom' ? object.bonePose : {}),
                          customAnimationId: null,
                        });
                      }}
                    >
                      {pose.label}{pose.implemented ? '' : '（未实现）'}
                    </Button>
                  ))}
                </div>
                <PoseEditor object={object} asset={asset} />
              </>
            ),
          },
          {
            key: 'anim',
            label: '动作',
            children: (
              <>
                <Select
                  size="small"
                  style={{ width: '100%', margin: '0 0 8px' }}
                  value={(object.animation as ClipId | null) ?? 'idle'}
                  options={clips.filter((c) => c.implemented).map((c) => ({
                    value: c.id,
                    label: `${c.label}${c.kind === 'pose' ? '（姿势）' : ''}`,
                  }))}
                  onChange={(animation: ClipId) => {
                    const clip = clips.find((c) => c.id === animation);
                    if (clip?.kind === 'pose' && clip.poseId) {
                      const preset = getPosePreset(clip.poseId);
                      updateObject(object.id, {
                        animation,
                        pose: clip.poseId,
                        animationPlaying: false,
                        bonePose: preset?.bones ?? {},
                        customAnimationId: null,
                      });
                      return;
                    }
                    updateObject(object.id, { animation, pose: animation === 'walk' ? 'walk' : animation === 'run' ? 'run' : 'stand', animationPlaying: true, customAnimationId: null, bonePose: {} });
                  }}
                />
                <Checkbox
                  checked={object.animationPlaying !== false && !object.customAnimationId}
                  onChange={(e) => updateObject(object.id, { animationPlaying: e.target.checked, customAnimationId: e.target.checked ? null : object.customAnimationId })}
                >
                  播放固定动作
                </Checkbox>
                <div style={{ marginTop: 12 }}>
                  <Text strong>创建动作</Text>
                  <AnimationTimeline object={object} asset={asset} />
                </div>
              </>
            ),
          },
          {
            key: 'look',
            label: '外观',
            children: (
              <>
                <Text type="secondary" style={{ fontSize: 12 }}>肤色</Text>
                <Input size="small" type="color" value={asset.appearance.skinColor || '#e0b090'} style={{ width: '100%', margin: '4px 0 8px' }} onChange={(e) => updateAppearance(asset.id, { skinColor: e.target.value })} />
                <Text type="secondary" style={{ fontSize: 12 }}>发色</Text>
                <Input size="small" type="color" value={asset.appearance.hairColor || '#3d2b1f'} style={{ width: '100%', margin: '4px 0 8px' }} onChange={(e) => updateAppearance(asset.id, { hairColor: e.target.value })} />
                <Text type="secondary" style={{ fontSize: 12 }}>服装颜色</Text>
                <Input size="small" type="color" value={asset.appearance.outfitColor || '#4a5568'} style={{ width: '100%', margin: '4px 0 8px' }} onChange={(e) => updateAppearance(asset.id, { outfitColor: e.target.value })} />
                <Text type="secondary" style={{ fontSize: 12 }}>体型</Text>
                <Select
                  size="small"
                  style={{ width: '100%', margin: '4px 0 8px' }}
                  value={asset.bodyType}
                  options={[{ value: 'slim', label: '瘦' }, { value: 'regular', label: '标准' }, { value: 'heavy', label: '壮' }]}
                  onChange={(bodyType: BodyType) => setBody(asset.id, { bodyType })}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>身高 (cm)</Text>
                <InputNumber size="small" min={80} max={220} style={{ width: '100%', margin: '4px 0 8px' }} value={asset.heightCm} onChange={(v) => setBody(asset.id, { heightCm: typeof v === 'number' ? v : asset.heightCm })} />
                {hairOptions.length > 0 && asset.characterType === 'human' && asset.gender === 'female' && (
                  <>
                    <Text type="secondary" style={{ fontSize: 12 }}>发型 / 服装模板</Text>
                    <Select
                      size="small"
                      style={{ width: '100%', margin: '4px 0 8px' }}
                      value={hairOptions.find((h) => h.modelUrl === asset.modelUrl)?.id}
                      options={hairOptions.map((h) => ({ value: h.id, label: h.label }))}
                      onChange={(id) => {
                        const opt = hairOptions.find((h) => h.id === id);
                        if (opt) updateCharacter(asset.id, { modelUrl: opt.modelUrl, skeletonType: 'rpm-feminine', animationSetId: 'rpm-feminine' });
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                      更换发型模板会换整套网格。要固定五官请只改发色。
                    </Text>
                  </>
                )}
                <Checkbox checked={asset.appearance.glassesVisible} onChange={(e) => updateAppearance(asset.id, { glassesVisible: e.target.checked })}>
                  配饰（眼镜，若模型含该网格）
                </Checkbox>
              </>
            ),
          },
          {
            key: 'asset',
            label: '资产',
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  size="small"
                  block
                  onClick={() => {
                    updateCharacter(asset.id, { defaultPose: (object.pose as CharacterAsset['defaultPose']) ?? 'stand', defaultBonePose: object.bonePose ?? null });
                    message.success(`已保存 ${asset.name}（${asset.id}）`);
                  }}
                >
                  保存角色
                </Button>
                <Button
                  size="small"
                  block
                  onClick={() => {
                    duplicateInstance(object.id);
                    message.success('已复制实例，仍引用同一 Character ID');
                  }}
                >
                  复制实例（同一角色）
                </Button>
                <Button
                  size="small"
                  block
                  onClick={() => {
                    const copy = duplicateAsset(asset.id);
                    if (copy) {
                      instanceCharacter(copy.id);
                      message.success(`已克隆为 ${copy.id}`);
                    }
                  }}
                >
                  复制角色（新 Character ID）
                </Button>
                <Button
                  size="small"
                  block
                  onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.glb,.gltf';
                    input.onchange = async () => {
                      const file = input.files?.[0];
                      if (!file) return;
                      const url = await new Promise<string>((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(String(reader.result));
                        reader.onerror = () => reject(new Error('读取失败'));
                        reader.readAsDataURL(file);
                      });
                      const result = await autoRigFromUrl(url);
                      if (!result.ok) {
                        message.error(result.error ?? '无法绑定');
                        return;
                      }
                      updateCharacter(asset.id, {
                        modelUrl: url,
                        skeletonType: result.skeletonType,
                        animationSetId: result.animationSetId,
                        rigStatus: result.rigStatus,
                        animationStatus: result.animationStatus,
                        sourceType: 'uploaded_3d',
                      });
                      message.success('已替换模型并重新绑定');
                    };
                    input.click();
                  }}
                >
                  替换模型 / 重新导入
                </Button>
                <Button
                  size="small"
                  block
                  onClick={async () => {
                    const result = await autoRigFromUrl(asset.modelUrl);
                    if (!result.ok) {
                      message.error(result.error ?? '重新绑定失败');
                      return;
                    }
                    updateCharacter(asset.id, {
                      skeletonType: result.skeletonType,
                      animationSetId: result.animationSetId,
                      rigStatus: result.rigStatus,
                      animationStatus: result.animationStatus,
                    });
                    message.success(result.inspection.message);
                  }}
                >
                  重新绑定
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </div>
  );
}
