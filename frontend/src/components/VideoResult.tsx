import { useState } from 'react';
import {
  Card,
  Collapse,
  Descriptions,
  Empty,
  List,
  Select,
  Tag,
  Typography,
  Image as AntImage,
} from 'antd';
import {
  CheckCircleFilled,
  WarningFilled,
  CloseCircleFilled,
} from '@ant-design/icons';
import type { ResultResp } from '../api/client';

const { Title, Text } = Typography;

const complianceStatusColor: Record<string, string> = {
  pass: 'green',
  review: 'orange',
  reject: 'red',
};

const gradeColor: Record<string, string> = {
  A: 'green',
  B: 'blue',
  C: 'orange',
  D: 'red',
};

interface Props {
  result: ResultResp | null;
}

export default function VideoResult({ result }: Props) {
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
  if (!result) {
    return <Empty description="视频尚未生成" />;
  }

  const time = new Date(result.created_at * 1000).toLocaleString('zh-CN');
  const script = result.script;
  const storyboard = result.storyboard;
  const compliance = result.compliance_report;
  const guard = result.content_guard_report;
  const quality = result.quality_report;
  const versions = result.video_versions ?? [];
  const currentUrl = selectedUrl || result.video_url;

  return (
    <Card>
      {currentUrl ? (
        <video
          src={currentUrl}
          controls
          key={currentUrl}
          style={{ width: '100%', borderRadius: 8, background: '#000' }}
        />
      ) : (
        <Empty description="视频生成中或未生成" />
      )}

      {versions.length > 1 && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>历史版本</Text>
          <Select
            size="small"
            value={currentUrl ?? undefined}
            onChange={setSelectedUrl}
            style={{ minWidth: 220 }}
            options={versions.map((v) => ({
              value: v.url,
              label: `v${v.version}${v.current ? '(当前)' : ''} · ${v.reason || '成片'} · ${new Date(v.ts * 1000).toLocaleString('zh-CN', { hour12: false })}`,
            }))}
          />
          {selectedUrl && selectedUrl !== result.video_url && (
            <Tag color="orange">正在查看历史版本</Tag>
          )}
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <Title level={4} style={{ marginBottom: 4 }}>
          {result.title || 'AI 生成的视频'}
        </Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            生成时间：{time}
          </Text>
          {result.model_used && (
            <Tag color="blue">{result.model_used}</Tag>
          )}
        </div>
      </div>

      <Collapse style={{ marginTop: 16 }} accordion>
        {script && (
          <Collapse.Panel header="脚本" key="script">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="标题">{script.title}</Descriptions.Item>
              {script.hook && (
                <Descriptions.Item label="Hook">{script.hook}</Descriptions.Item>
              )}
              {script.narration && (
                <Descriptions.Item label="旁白">{script.narration}</Descriptions.Item>
              )}
              {script.ending && (
                <Descriptions.Item label="结尾">{script.ending}</Descriptions.Item>
              )}
            </Descriptions>
            {Array.isArray(script.scenes) && script.scenes.length > 0 && (
              <List
                size="small"
                header={<Text strong>场景</Text>}
                dataSource={script.scenes}
                renderItem={(s: any, i: number) => (
                  <List.Item>
                    {i + 1}. {s.description || s.scene || JSON.stringify(s)}
                  </List.Item>
                )}
              />
            )}
          </Collapse.Panel>
        )}

        {storyboard?.shots && (
          <Collapse.Panel
            header={`分镜 (${storyboard.shots.length} 个镜头)`}
            key="storyboard"
          >
            <List
              size="small"
              dataSource={storyboard.shots}
              renderItem={(shot: any, i: number) => (
                <List.Item>
                  <Descriptions
                    column={2}
                    size="small"
                    title={`镜头 ${shot.shot_id ?? i + 1}`}
                  >
                    <Descriptions.Item label="时长">
                      {shot.duration}s
                    </Descriptions.Item>
                    <Descriptions.Item label="场景">
                      {shot.scene || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="角色">
                      {shot.character || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="运镜">
                      {shot.camera_movement || shot.camera || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="画面" span={2}>
                      {shot.visual_description || shot.image_prompt || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="旁白" span={2}>
                      {shot.voiceover || shot.narration || '-'}
                    </Descriptions.Item>
                    {shot.subtitle && (
                      <Descriptions.Item label="字幕" span={2}>
                        {shot.subtitle}
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </List.Item>
              )}
            />
          </Collapse.Panel>
        )}

        {storyboard?.shots && storyboard.shots.some((s: any) => s.image_path || s.audio_path) && (
          <Collapse.Panel
            header={`中间产物 (${storyboard.shots.length} 组图片+音频)`}
            key="assets"
          >
            <List
              size="small"
              dataSource={storyboard.shots}
              renderItem={(shot: any, i: number) => {
                const imgFile = shot.image_path?.split(/[\\/]/).pop();
                const audioFile = shot.audio_path?.split(/[\\/]/).pop();
                const imgUrl = imgFile ? `/storage/images/${imgFile}` : null;
                const audioUrl = audioFile ? `/storage/audio/${audioFile}` : null;
                return (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <Text strong>镜头 {shot.shot_id ?? i + 1}</Text>
                      <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
                        {imgUrl ? (
                          <div>
                            <Text type="secondary" style={{ fontSize: 12 }}>关键帧</Text>
                            <AntImage
                              src={imgUrl}
                              width={120}
                              style={{ borderRadius: 6, display: 'block', marginTop: 4 }}
                              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                            />
                          </div>
                        ) : null}
                        {audioUrl ? (
                          <div>
                            <Text type="secondary" style={{ fontSize: 12 }}>TTS 旁白</Text>
                            <audio
                              src={audioUrl}
                              controls
                              style={{ display: 'block', marginTop: 4, height: 32 }}
                            />
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </List.Item>
                );
              }}
            />
          </Collapse.Panel>
        )}

        {compliance && (
          <Collapse.Panel
            header={
              <span>
                合规报告{' '}
                <Tag color={complianceStatusColor[compliance.status] || 'default'}>
                  {compliance.status}
                </Tag>
                {typeof compliance.overall_score === 'number' && (
                  <Tag>Score {compliance.overall_score}</Tag>
                )}
                {result.revision_count > 0 && (
                  <Tag color="orange">修订 {result.revision_count} 次</Tag>
                )}
                {result.human_review_required && (
                  <Tag color="orange">需人工审核</Tag>
                )}
              </span>
            }
            key="compliance"
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="状态">{compliance.status}</Descriptions.Item>
              <Descriptions.Item label="风险等级">
                {compliance.risk_level || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="综合评分">
                {compliance.overall_score ?? '-'}
              </Descriptions.Item>
              {compliance.review_reason && (
                <Descriptions.Item label="审核原因">
                  {compliance.review_reason}
                </Descriptions.Item>
              )}
            </Descriptions>
            {Array.isArray(compliance.violations) &&
              compliance.violations.length > 0 && (
                <List
                  size="small"
                  header={<Text type="danger" strong>违规项</Text>}
                  dataSource={compliance.violations}
                  renderItem={(v: any) => (
                    <List.Item>
                      <Text type="danger">
                        {typeof v === 'string' ? v : v.message || JSON.stringify(v)}
                      </Text>
                    </List.Item>
                  )}
                />
              )}
            {Array.isArray(compliance.warnings) &&
              compliance.warnings.length > 0 && (
                <List
                  size="small"
                  header={<Text type="warning" strong>警告项</Text>}
                  dataSource={compliance.warnings}
                  renderItem={(w: any) => (
                    <List.Item>
                      <Text type="warning">
                        {typeof w === 'string' ? w : w.message || JSON.stringify(w)}
                      </Text>
                    </List.Item>
                  )}
                />
              )}
          </Collapse.Panel>
        )}

        {guard && (
          <Collapse.Panel
            header={
              <span>
                内容风控{' '}
                <Tag
                  color={
                    guard.safe === false
                      ? 'red'
                      : guard.overall_risk === 'high'
                      ? 'orange'
                      : 'green'
                  }
                >
                  {guard.overall_risk || '-'}
                </Tag>
              </span>
            }
            key="guard"
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="安全风险">
                {guard.safety_risk || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="平台风险">
                {guard.platform_risk || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="文化风险">
                {guard.cultural_risk || '-'}
              </Descriptions.Item>
            </Descriptions>
            {Array.isArray(guard.warnings) && guard.warnings.length > 0 && (
              <List
                size="small"
                dataSource={guard.warnings}
                renderItem={(w: string) => (
                  <List.Item>
                    <Text type="warning">{w}</Text>
                  </List.Item>
                )}
              />
            )}
          </Collapse.Panel>
        )}

        {quality && (
          <Collapse.Panel
            header={
              <span>
                质量报告{' '}
                <Tag color={gradeColor[quality.grade] || 'default'}>
                  Grade {quality.grade}
                </Tag>
              </span>
            }
            key="quality"
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="时长">
                {typeof quality.duration === 'number'
                  ? quality.duration.toFixed(2)
                  : '-'}{' '}
                s
              </Descriptions.Item>
              <Descriptions.Item label="分辨率">
                {quality.width}x{quality.height}
              </Descriptions.Item>
              <Descriptions.Item label="FPS">
                {typeof quality.fps === 'number' ? quality.fps.toFixed(1) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="比例">
                {quality.aspect_ratio || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="音轨">
                {quality.has_audio ? '有' : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="分镜数">
                {quality.scenes ?? '-'}
              </Descriptions.Item>
            </Descriptions>
            {Array.isArray(quality.checks) && quality.checks.length > 0 && (
              <List
                size="small"
                header={<Text strong>检查项</Text>}
                dataSource={quality.checks}
                renderItem={(c: string) => (
                  <List.Item>
                    <CheckCircleFilled style={{ color: '#52c41a', marginRight: 8 }} />
                    {c}
                  </List.Item>
                )}
              />
            )}
            {Array.isArray(quality.warnings) && quality.warnings.length > 0 && (
              <List
                size="small"
                header={<Text type="warning" strong>警告</Text>}
                dataSource={quality.warnings}
                renderItem={(w: string) => (
                  <List.Item>
                    <WarningFilled style={{ color: '#faad14', marginRight: 8 }} />
                    {w}
                  </List.Item>
                )}
              />
            )}
            {Array.isArray(quality.errors) && quality.errors.length > 0 && (
              <List
                size="small"
                header={<Text type="danger" strong>错误</Text>}
                dataSource={quality.errors}
                renderItem={(e: string) => (
                  <List.Item>
                    <CloseCircleFilled style={{ color: '#ff4d4f', marginRight: 8 }} />
                    {e}
                  </List.Item>
                )}
              />
            )}
          </Collapse.Panel>
        )}
      </Collapse>
    </Card>
  );
}
