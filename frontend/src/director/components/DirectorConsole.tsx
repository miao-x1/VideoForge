import { Button, InputNumber, Select, Typography } from 'antd';
import { cinema } from '../../theme';
import { useDirectorStore } from '../store/useDirectorStore';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import CharacterPanel from './CharacterPanel';
import ShotInspector from './ShotInspector';
import { analyzeScene } from '../directing/advice';
import { ANGLE_LABEL, ATMOSPHERE_LABEL, SHOT_SIZE_LABEL, WEATHER_LABEL } from '../directing/look';
import type { Atmosphere, CameraAngle, CharacterRelationKind, ShotSize, Weather } from '../types';
import { useMemo } from 'react';

const { Text } = Typography;

const RELATIONS: Array<{ value: CharacterRelationKind; label: string }> = [
  { value: 'hostile', label: '敌对' },
  { value: 'romantic', label: '爱慕' },
  { value: 'ally', label: '同盟' },
  { value: 'family', label: '家人' },
  { value: 'stranger', label: '陌生' },
];

export default function DirectorConsole({ onOpenStage }: { onOpenStage: () => void }) {
  const selectedId = useDirectorStore((s) => s.selectedId);
  const objects = useDirectorStore((s) => s.objects) ?? [];
  const cameras = useDirectorStore((s) => s.cameras) ?? [];
  const environment = useDirectorStore((s) => s.environment);
  const relations = useDirectorStore((s) => s.relations) ?? [];
  const sceneId = useDirectorStore((s) => s.sceneId);
  const timeOfDay = useDirectorStore((s) => s.timeOfDay);
  const shotType = useDirectorStore((s) => s.shotType);
  const applyAdvice = useDirectorStore((s) => s.applyAdvice);
  const applyEnvironmentLook = useDirectorStore((s) => s.applyEnvironmentLook);
  const applyShotFraming = useDirectorStore((s) => s.applyShotFraming);
  const applyCameraTemplate = useDirectorStore((s) => s.applyCameraTemplate);
  const applyBlocking = useDirectorStore((s) => s.applyBlocking);
  const setRelation = useDirectorStore((s) => s.setRelation);
  const updateCamera = useDirectorStore((s) => s.updateCamera);
  const addCamera = useDirectorStore((s) => s.addCamera);
  const selectCamera = useDirectorStore((s) => s.selectCamera);
  const activeCamera = useDirectorStore((s) => s.activeCamera);

  const object = objects.find((o) => o.id === selectedId);
  const camera = cameras.find((c) => c.id === selectedId) ?? cameras.find((c) => c.id === activeCamera);
  const chars = objects.filter((o) => o.characterId);
  const other = chars.find((c) => c.id !== object?.id);
  const relation = relations.find((r) => r.fromId === object?.id || r.toId === object?.id);
  const asset = useCharacterLibrary((s) => s.characters.find((c) => c.id === object?.characterId));
  const tips = useMemo(
    () =>
      analyzeScene({
        sceneId,
        objects,
        cameras,
        environment: environment ?? { ambientIntensity: 0.55, weather: 'clear', timeOfDay: '' },
        relations,
        timeOfDay,
        shotType,
        activeCamera,
      } as Parameters<typeof analyzeScene>[0]),
    [sceneId, objects, cameras, environment, relations, timeOfDay, shotType, activeCamera],
  );

  return (
    <div
      style={{
        width: 276,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: cinema.panel,
        borderLeft: `1px solid ${cinema.line}`,
      }}
    >
      <div style={{ padding: '12px 14px', borderBottom: `1px solid ${cinema.line}` }}>
        <div style={{ fontSize: 11, letterSpacing: 1.4, color: cinema.gold }}>导演控制台</div>
        <div style={{ color: cinema.text, fontWeight: 600, marginTop: 2 }}>
          {object?.characterId ? object.name : camera && selectedId === camera.id ? camera.name : '当前场景'}
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 12 }}>
        {object?.characterId && (
          <div style={{ marginBottom: 14 }}>
            <Fact label="角色" value={object.name} />
            <Fact label="类型" value={asset ? `${asset.gender === 'female' ? '女' : asset.ageGroup === 'child' ? '小孩' : asset.ageGroup === 'elder' ? '老人' : '男'} · ${asset.characterType}` : '角色'} />
            <Fact label="当前动作" value={object.animation || object.pose || '站立'} />
            {other && (
              <>
                <Fact label="与角色" value={other.name} />
                <div style={{ marginBottom: 10 }}>
                  <Text style={{ fontSize: 12, color: cinema.muted }}>关系</Text>
                  <Select
                    size="small"
                    style={{ width: '100%', marginTop: 4 }}
                    value={relation?.kind ?? 'stranger'}
                    options={RELATIONS}
                    onChange={(kind) => setRelation(object.id, other.id, kind)}
                  />
                </div>
              </>
            )}
            <CharacterPanel instanceId={object.id} characterId={object.characterId} />
          </div>
        )}

        {(!object || !object.characterId) && selectedId && camera && selectedId === camera.id && (
          <div style={{ marginBottom: 14 }}>
            <Fact label="机位" value={camera.name} />
            <div style={{ marginBottom: 8 }}>
              <Text style={{ fontSize: 12, color: cinema.muted }}>景别</Text>
              <Select
                size="small"
                style={{ width: '100%', marginTop: 4 }}
                value={camera.shotSize ?? 'medium'}
                options={Object.entries(SHOT_SIZE_LABEL).map(([value, label]) => ({ value, label }))}
                onChange={(size: ShotSize) => applyShotFraming(size, camera.angle)}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text style={{ fontSize: 12, color: cinema.muted }}>角度</Text>
              <Select
                size="small"
                style={{ width: '100%', marginTop: 4 }}
                value={camera.angle ?? 'eye'}
                options={Object.entries(ANGLE_LABEL).map(([value, label]) => ({ value, label }))}
                onChange={(angle: CameraAngle) => applyShotFraming(camera.shotSize ?? 'medium', angle)}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text style={{ fontSize: 12, color: cinema.muted }}>FOV / 焦距</Text>
              <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                <InputNumber size="small" min={10} max={120} value={camera.fov} onChange={(fov) => updateCamera(camera.id, { fov: typeof fov === 'number' ? fov : 45 })} />
                <InputNumber size="small" min={14} max={135} value={camera.focalLength ?? 35} onChange={(focalLength) => updateCamera(camera.id, { focalLength: typeof focalLength === 'number' ? focalLength : 35 })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
              <Button size="small" onClick={() => applyCameraTemplate('romance')}>爱情镜头</Button>
              <Button size="small" onClick={() => applyCameraTemplate('battle')}>战斗镜头</Button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {cameras.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => selectCamera(c.id)}
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    borderRadius: 8,
                    border: `1px solid ${c.id === activeCamera ? cinema.gold : cinema.line}`,
                    background: cinema.raised,
                    color: cinema.text,
                    cursor: 'pointer',
                  }}
                >
                  {c.name} · {SHOT_SIZE_LABEL[c.shotSize ?? 'medium']}
                </button>
              ))}
              <Button size="small" onClick={() => addCamera()}>创建 Camera</Button>
            </div>
          </div>
        )}

        {(!object || !object.characterId) && !(camera && selectedId === camera.id) && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ color: cinema.gold, fontSize: 11, letterSpacing: 1, marginBottom: 8 }}>环境参数</div>
            <Select
              size="small"
              style={{ width: '100%', marginBottom: 8 }}
              value={environment.timeOfDay || 'day'}
              options={[
                { value: 'dawn', label: '清晨' },
                { value: 'day', label: '白天' },
                { value: 'dusk', label: '黄昏' },
                { value: 'night', label: '夜晚' },
              ]}
              onChange={(v) => applyEnvironmentLook(undefined, v, undefined)}
            />
            <Select
              size="small"
              style={{ width: '100%', marginBottom: 8 }}
              value={environment.weather || 'clear'}
              options={Object.entries(WEATHER_LABEL).map(([value, label]) => ({ value, label }))}
              onChange={(v: Weather) => applyEnvironmentLook(v, undefined, undefined)}
            />
            <Select
              size="small"
              style={{ width: '100%', marginBottom: 10 }}
              value={environment.atmosphere || 'neutral'}
              options={Object.entries(ATMOSPHERE_LABEL).map(([value, label]) => ({ value, label }))}
              onChange={(v: Atmosphere) => applyEnvironmentLook(undefined, undefined, v)}
            />
            <ShotInspector />
          </div>
        )}

        <div style={{ borderTop: `1px solid ${cinema.line}`, paddingTop: 12, marginTop: 8 }}>
          <div style={{ color: cinema.gold, fontSize: 11, letterSpacing: 1, marginBottom: 8 }}>AI 导演建议</div>
          {tips.map((tip) => (
            <div
              key={tip.id}
              style={{
                padding: 10,
                borderRadius: 8,
                background: cinema.raised,
                border: `1px solid ${cinema.line}`,
                marginBottom: 8,
              }}
            >
              <div style={{ color: cinema.text, fontWeight: 600, fontSize: 13 }}>{tip.title}</div>
              <div style={{ color: cinema.muted, fontSize: 12, marginTop: 4 }}>{tip.detail}</div>
              {tip.apply && (
                <Button size="small" style={{ marginTop: 8 }} onClick={() => applyAdvice(tip.apply!)}>
                  应用建议
                </Button>
              )}
            </div>
          ))}
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <Button size="small" onClick={() => applyBlocking('dialogue')}>对话站位</Button>
            <Button size="small" onClick={() => applyBlocking('conflict')}>冲突站位</Button>
            <Button size="small" onClick={onOpenStage}>自动布置</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
      <span style={{ color: cinema.muted, fontSize: 12 }}>{label}</span>
      <span style={{ color: cinema.text, fontSize: 12, fontWeight: 600 }}>{value}</span>
    </div>
  );
}
