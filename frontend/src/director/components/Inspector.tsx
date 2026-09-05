import { Checkbox, Input, InputNumber, Select, Typography } from 'antd';
import { catalogShapeOptions } from '../catalog';
import { useDirectorStore } from '../store/useDirectorStore';
import { mediaUrl } from '../../api/client';
import { colors } from '../../theme';
import type { ShapeKind, Vec3 } from '../types';
import CharacterPanel from './CharacterPanel';
import ShotInspector from './ShotInspector';

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
  const axes: Array<[string, number]> = [
    ['X', 0],
    ['Y', 1],
    ['Z', 2],
  ];
  return (
    <div style={{ marginBottom: 10 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
        {axes.map(([name, i]) => (
          <InputNumber
            key={name}
            size="small"
            addonBefore={name}
            value={Number(value[i].toFixed(3))}
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

export default function Inspector({ embedded = false, dark = false }: { embedded?: boolean; dark?: boolean }) {
  const selectedId = useDirectorStore((s) => s.selectedId);
  const objects = useDirectorStore((s) => s.objects);
  const cameras = useDirectorStore((s) => s.cameras);
  const environment = useDirectorStore((s) => s.environment);
  const updateObject = useDirectorStore((s) => s.updateObject);
  const updateTransform = useDirectorStore((s) => s.updateTransform);
  const updateCamera = useDirectorStore((s) => s.updateCamera);
  const setEnvironment = useDirectorStore((s) => s.setEnvironment);
  const compositionUrl = useDirectorStore((s) => s.compositionUrl);
  const imageUrl = useDirectorStore((s) => s.imageUrl);

  const object = objects.find((o) => o.id === selectedId);
  const camera = cameras.find((c) => c.id === selectedId);

  return (
    <div
      className={dark ? 'director-dark-panel' : undefined}
      style={{
        width: embedded ? '100%' : 340,
        flexShrink: 0,
        background: dark ? 'transparent' : colors.surface,
        borderLeft: embedded ? 'none' : `1px solid ${colors.border}`,
        overflow: 'auto',
        padding: 12,
        color: dark ? '#f0f0f0' : undefined,
      }}
    >
      <Text strong style={dark ? { color: '#f0f0f0' } : undefined}>
        {object?.characterId ? '角色' : camera ? '摄像机' : object ? '元素' : '场景 / 镜头'}
      </Text>

      {!object && !camera && (
        <div style={{ marginTop: 12 }}>
          {(compositionUrl || imageUrl) && (
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>构图 / 画面</Text>
              <img
                src={mediaUrl(imageUrl || compositionUrl || '')}
                alt=""
                style={{ width: '100%', borderRadius: 8, marginTop: 6, display: 'block' }}
              />
            </div>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>场景环境</Text>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>天空颜色</Text>
            <Input
              size="small"
              type="color"
              value={environment.sky}
              style={{ width: '100%', margin: '4px 0 10px' }}
              onChange={(e) => setEnvironment({ sky: e.target.value })}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>环境光强度</Text>
            <InputNumber
              size="small"
              min={0}
              max={3}
              step={0.05}
              value={environment.ambientIntensity}
              style={{ width: '100%', margin: '4px 0 10px' }}
              onChange={(v) => setEnvironment({ ambientIntensity: typeof v === 'number' ? v : 0.55 })}
            />
            <Checkbox
              checked={environment.showGrid}
              onChange={(e) => setEnvironment({ showGrid: e.target.checked })}
            >
              显示网格
            </Checkbox>
          </div>
          <div style={{ marginTop: 16 }}>
            <ShotInspector />
          </div>
        </div>
      )}

      {object?.characterId && (
        <CharacterPanel instanceId={object.id} characterId={object.characterId} />
      )}

      {object && !object.characterId && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>名称</Text>
          <Input
            size="small"
            value={object.name}
            style={{ margin: '4px 0 10px' }}
            onChange={(e) => updateObject(object.id, { name: e.target.value })}
          />
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            {object.type}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>形状</Text>
          <Select
            size="small"
            showSearch
            optionFilterProp="label"
            style={{ width: '100%', margin: '4px 0 10px' }}
            value={object.primitive}
            options={catalogShapeOptions()}
            onChange={(primitive: ShapeKind) => updateObject(object.id, { primitive })}
          />
          <VecFields
            label="Position"
            value={object.position}
            step={0.1}
            onChange={(position) => updateTransform(object.id, { position })}
          />
          <VecFields
            label="Rotation (rad)"
            value={object.rotation}
            step={0.05}
            onChange={(rotation) => updateTransform(object.id, { rotation })}
          />
          <VecFields
            label="Scale"
            value={object.scale}
            step={0.05}
            onChange={(scale) => updateTransform(object.id, { scale })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>颜色</Text>
          <Input
            size="small"
            type="color"
            value={object.color}
            style={{ width: '100%', margin: '4px 0 10px' }}
            onChange={(e) => updateObject(object.id, { color: e.target.value })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>金属度</Text>
          <InputNumber
            size="small"
            min={0}
            max={1}
            step={0.05}
            value={object.metalness}
            style={{ width: '100%', margin: '4px 0 10px' }}
            onChange={(v) => updateObject(object.id, { metalness: typeof v === 'number' ? v : 0 })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>粗糙度</Text>
          <InputNumber
            size="small"
            min={0}
            max={1}
            step={0.05}
            value={object.roughness}
            style={{ width: '100%', margin: '4px 0 10px' }}
            onChange={(v) => updateObject(object.id, { roughness: typeof v === 'number' ? v : 0.65 })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>透明度</Text>
          <InputNumber
            size="small"
            min={0.05}
            max={1}
            step={0.05}
            value={object.opacity}
            style={{ width: '100%', margin: '4px 0 10px' }}
            onChange={(v) => updateObject(object.id, { opacity: typeof v === 'number' ? v : 1 })}
          />
          {object.type === 'light' && (
            <>
              <Text type="secondary" style={{ fontSize: 12 }}>灯光强度</Text>
              <InputNumber
                size="small"
                min={0}
                max={40}
                step={0.2}
                value={object.lightIntensity ?? 8}
                style={{ width: '100%', margin: '4px 0 10px' }}
                onChange={(v) => updateObject(object.id, { lightIntensity: typeof v === 'number' ? v : 8 })}
              />
            </>
          )}
          <Checkbox
            checked={object.visible}
            onChange={(e) => updateObject(object.id, { visible: e.target.checked })}
          >
            显示
          </Checkbox>
          <Checkbox
            checked={object.locked}
            style={{ marginLeft: 12 }}
            onChange={(e) => updateObject(object.id, { locked: e.target.checked })}
          >
            锁定
          </Checkbox>
          {object.animations.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Animation</Text>
              <Select
                size="small"
                allowClear
                style={{ width: '100%', marginTop: 4 }}
                value={object.animation ?? undefined}
                options={object.animations.map((n) => ({ value: n, label: n }))}
                onChange={(animation) => updateObject(object.id, { animation: animation ?? null })}
              />
            </div>
          )}
        </div>
      )}

      {camera && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>机位名称</Text>
          <Input
            size="small"
            value={camera.name}
            style={{ margin: '4px 0 10px' }}
            onChange={(e) => updateCamera(camera.id, { name: e.target.value })}
          />
          <VecFields
            label="Camera Position"
            value={camera.position}
            step={0.1}
            onChange={(position) => updateCamera(camera.id, { position })}
          />
          <VecFields
            label="Camera Rotation (rad)"
            value={camera.rotation}
            step={0.05}
            onChange={(rotation) => updateCamera(camera.id, { rotation })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>FOV</Text>
          <InputNumber
            size="small"
            min={10}
            max={120}
            value={camera.fov}
            style={{ width: '100%', marginTop: 4 }}
            onChange={(fov) => updateCamera(camera.id, { fov: typeof fov === 'number' ? fov : 45 })}
          />
          <div style={{ marginTop: 16 }}>
            <ShotInspector />
          </div>
        </div>
      )}
    </div>
  );
}
