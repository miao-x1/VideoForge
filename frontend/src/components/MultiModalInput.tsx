import { useState } from 'react';
import { Upload, Input, Button, Tag, Space, Tabs, message, Typography, Select } from 'antd';
import { UploadOutlined, LinkOutlined, PictureOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { api, type InputSourceItem } from '../api/client';

const { Text } = Typography;

interface Props {
  sources: InputSourceItem[];
  onChange: (sources: InputSourceItem[]) => void;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  image: { label: '图片', color: 'blue' },
  video: { label: '视频', color: 'purple' },
  url: { label: 'URL', color: 'orange' },
};

// 参考素材用途:AI 自动判断为默认值
const PURPOSE_OPTIONS = [
  { label: 'AI 自动判断', value: 'overall' },
  { label: '主体参考', value: 'subject' },
  { label: '场景参考', value: 'scene' },
  { label: '风格参考', value: 'style' },
  { label: '镜头参考', value: 'camera' },
  { label: '动作参考', value: 'action' },
];

export default function MultiModalInput({ sources, onChange }: Props) {
  const [urlInput, setUrlInput] = useState('');
  const [uploading, setUploading] = useState(false);

  const addSource = (item: InputSourceItem) => {
    onChange([...sources, item]);
  };

  const removeSource = (index: number) => {
    onChange(sources.filter((_, i) => i !== index));
  };

  const setPurpose = (index: number, purpose: string) => {
    onChange(sources.map((s, i) => (i === index ? { ...s, purpose } : s)));
  };

  const handleImageUpload = async (file: File) => {
    setUploading(true);
    try {
      const resp = await api.uploadImage(file);
      addSource({ type: 'image', content: resp.file_path, purpose: 'overall' });
      message.success(`图片已上传: ${resp.file_name}`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '图片上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleVideoUpload = async (file: File) => {
    setUploading(true);
    try {
      const resp = await api.uploadVideo(file);
      addSource({ type: 'video', content: resp.file_path, purpose: 'overall' });
      message.success(`视频已上传: ${resp.file_name}`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '视频上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleUrlAdd = () => {
    const url = urlInput.trim();
    if (!url) return;
    if (!/^https?:\/\//.test(url)) {
      message.warning('请输入完整 URL (以 http:// 或 https:// 开头)');
      return;
    }
    addSource({ type: 'url', content: url, purpose: 'overall' });
    setUrlInput('');
  };

  const tabItems = [
    {
      key: 'image',
      label: <span><PictureOutlined /> 图片</span>,
      children: (
        <Upload
          accept=".png,.jpg,.jpeg,.webp,.gif"
          showUploadList={false}
          beforeUpload={handleImageUpload}
        >
          <Button icon={<UploadOutlined />} loading={uploading}>
            上传图片
          </Button>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            PNG/JPG/WebP/GIF, 最大 20MB
          </Text>
        </Upload>
      ),
    },
    {
      key: 'video',
      label: <span><VideoCameraOutlined /> 视频</span>,
      children: (
        <Upload
          accept=".mp4,.mov,.avi,.mkv,.webm"
          showUploadList={false}
          beforeUpload={handleVideoUpload}
        >
          <Button icon={<UploadOutlined />} loading={uploading}>
            上传视频
          </Button>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            MP4/MOV/AVI/MKV/WebM, 最大 20MB
          </Text>
        </Upload>
      ),
    },
    {
      key: 'url',
      label: <span><LinkOutlined /> 链接</span>,
      children: (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/article"
            onPressEnter={handleUrlAdd}
          />
          <Button type="primary" onClick={handleUrlAdd}>
            添加
          </Button>
        </Space.Compact>
      ),
    },
  ];

  return (
    <div>
      <Tabs items={tabItems} size="small" />
      {sources.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {sources.map((src, i) => {
            const meta = TYPE_LABELS[src.type] || { label: src.type, color: 'default' };
            const display = src.type === 'url' ? src.content : `[${meta.label}] ${src.content.split(/[/\\]/).pop()}`;
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  background: '#fafafa',
                  border: '1px solid #f0f0f0',
                  borderRadius: 6,
                  padding: '4px 8px',
                }}
              >
                <Tag color={meta.color} style={{ margin: 0, flexShrink: 0 }}>
                  {display.length > 40 ? `${display.slice(0, 40)}…` : display}
                </Tag>
                <Select
                  size="small"
                  value={src.purpose || 'overall'}
                  onChange={(v) => setPurpose(i, v)}
                  options={PURPOSE_OPTIONS}
                  style={{ width: 130, flexShrink: 0 }}
                />
                <Button
                  type="text"
                  size="small"
                  danger
                  onClick={() => removeSource(i)}
                  style={{ marginLeft: 'auto', flexShrink: 0 }}
                >
                  移除
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
