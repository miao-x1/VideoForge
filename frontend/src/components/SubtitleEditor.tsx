import { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Card,
  InputNumber,
  List,
  message,
  Popconfirm,
  Space,
  Switch,
  Tag,
  Typography,
} from 'antd';
import { DownloadOutlined, SaveOutlined } from '@ant-design/icons';
import type { SubtitleItem } from '../api/client';
import { api } from '../api/client';

const { Text } = Typography;

interface Props {
  taskId: string;
  onUpdated: () => void; // 字幕更新触发重合成后回调(SSE 会推送新版本)
}

function fmtTime(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function SubtitleEditor({ taskId, onUpdated }: Props) {
  const [items, setItems] = useState<SubtitleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.getSubtitles(taskId);
      setItems(resp.items);
    } catch {
      // 任务可能尚无分镜
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    load();
  }, [load]);

  const updateItem = (idx: number, patch: Partial<SubtitleItem>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.updateSubtitles(taskId, items);
      message.success('字幕已保存,正在重新合成新版本');
      onUpdated();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (!loading && items.length === 0) return null;

  return (
    <Card
      size="small"
      title="字幕编辑"
      extra={
        <Space>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={async () => {
              try {
                const { default: axios } = await import('axios');
                const resp = await axios.get(
                  `/api/video/tasks/${taskId}/subtitles/export`,
                  { responseType: 'blob' },
                );
                const url = URL.createObjectURL(resp.data);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${taskId}.srt`;
                a.click();
                URL.revokeObjectURL(url);
              } catch {
                message.error('SRT 导出失败');
              }
            }}
          >
            导出 SRT
          </Button>
          <Popconfirm title="保存后将重新合成新版本视频,确认?" onConfirm={save}>
            <Button size="small" type="primary" icon={<SaveOutlined />} loading={saving}>
              保存并重新合成
            </Button>
          </Popconfirm>
        </Space>
      }
    >
      <List
        size="small"
        dataSource={items}
        renderItem={(item, idx) => (
          <List.Item>
            <Space direction="vertical" style={{ width: '100%' }} size={4}>
              <Space size={8} wrap>
                <Tag color="blue">镜头 {item.shot_index + 1}</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {fmtTime(item.start)} → {fmtTime(item.end)}({(item.end - item.start).toFixed(1)}s)
                </Text>
                <Space size={4}>
                  <Text type="secondary" style={{ fontSize: 12 }}>烧录</Text>
                  <Switch
                    size="small"
                    checked={item.enabled}
                    onChange={(v) => updateItem(idx, { enabled: v })}
                  />
                </Space>
                <Space size={4}>
                  <Text type="secondary" style={{ fontSize: 12 }}>字号</Text>
                  <InputNumber
                    size="small"
                    min={0}
                    max={96}
                    value={item.font_size || undefined}
                    placeholder="默认"
                    style={{ width: 72 }}
                    onChange={(v) => updateItem(idx, { font_size: v ?? 0 })}
                  />
                </Space>
              </Space>
              <Typography.Paragraph style={{ marginBottom: 0 }}>
                <Typography.Text
                  editable={{
                    onChange: (v) => updateItem(idx, { text: v }),
                    text: item.text,
                    tooltip: '点击编辑字幕文本',
                  }}
                >
                  {item.text || '(空)'}
                </Typography.Text>
              </Typography.Paragraph>
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
}
