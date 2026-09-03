import { Collapse, Tag, Typography } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { accents, calloutStyle } from '../theme';

const { Text, Paragraph } = Typography;

interface ScriptScene {
  scene_id: number;
  duration: number;
  location: string;
  characters: string[];
  visual: string;
  dialogue: string;
  voiceover: string;
}

interface ScriptData {
  title: string;
  hook: string;
  scenes: ScriptScene[];
  ending: string;
}

interface Props {
  script: ScriptData | null;
}

export default function ScriptViewer({ script }: Props) {
  if (!script) return null;

  const totalDuration = script.scenes?.reduce((s, sc) => s + (sc.duration || 0), 0) || 0;

  return (
    <Collapse
      size="small"
      style={{ marginTop: 12 }}
      defaultActiveKey={['script']}
      items={[{
        key: 'script',
        label: (
          <span>
            <EditOutlined style={{ marginRight: 6 }} />
            脚本 · {script.scenes?.length || 0} 场景 · {totalDuration}秒
          </span>
        ),
        children: (
          <div>
            {script.title && (
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ fontSize: 14 }}>{script.title}</Text>
              </div>
            )}
            {script.hook && (
              <div style={{ marginBottom: 8, ...calloutStyle(accents.warning) }}>
                <Text type="secondary" style={{ fontSize: 12 }}>Hook: </Text>
                <Text style={{ fontSize: 13 }}>{script.hook}</Text>
              </div>
            )}
            {script.scenes?.map((scene, i) => (
              <div
                key={i}
                style={{
                  marginBottom: 8,
                  padding: '8px 10px',
                  background: accents.neutral.bg,
                  border: `1px solid ${accents.neutral.border}`,
                  borderRadius: 4,
                }}
              >
                <div style={{ display: 'flex', gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
                  <Tag color="blue">场景 {scene.scene_id}</Tag>
                  <Tag>{scene.duration}秒</Tag>
                  {scene.location && <Tag color="cyan">{scene.location}</Tag>}
                  {scene.characters?.map((c, ci) => (
                    <Tag key={ci} color="purple">{c}</Tag>
                  ))}
                </div>
                {scene.visual && (
                  <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                    <Text type="secondary">画面: </Text>{scene.visual}
                  </Paragraph>
                )}
                {scene.dialogue && (
                  <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                    <Text type="secondary">对白: </Text>{scene.dialogue}
                  </Paragraph>
                )}
                {scene.voiceover && (
                  <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                    <Text type="secondary">旁白: </Text>{scene.voiceover}
                  </Paragraph>
                )}
              </div>
            ))}
            {script.ending && (
              <div style={calloutStyle(accents.success)}>
                <Text type="secondary" style={{ fontSize: 12 }}>结尾: </Text>
                <Text style={{ fontSize: 13 }}>{script.ending}</Text>
              </div>
            )}
          </div>
        ),
      }]}
    />
  );
}
