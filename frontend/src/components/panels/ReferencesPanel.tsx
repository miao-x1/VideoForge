import { useState } from 'react';
import { Button, Select, Input, Typography, Empty, Spin, Tag, Space } from 'antd';
import { DeleteOutlined, InboxOutlined } from '@ant-design/icons';
import { useCreativeStore } from '../../store/useCreativeStore';
import { api, type ReferenceAsset } from '../../api/client';

const { Text } = Typography;

const PURPOSES = [
  { label: '主体参考', value: 'subject' },
  { label: '场景参考', value: 'scene' },
  { label: '风格参考', value: 'style' },
  { label: '构图参考', value: 'composition' },
  { label: '配色参考', value: 'color' },
  { label: '动作参考', value: 'action' },
  { label: '镜头参考', value: 'camera' },
  { label: '运动参考', value: 'movement' },
  { label: '节奏参考', value: 'rhythm' },
  { label: '整体参考', value: 'overall' },
];

export default function ReferencesPanel() {
  const references = useCreativeStore((s) => s.spec.references ?? []);
  const updateSpec = useCreativeStore((s) => s.updateSpec);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = async (file: File) => {
    setUploading(true);
    try {
      const isImage = /\.(png|jpe?g|webp|gif)$/i.test(file.name);
      const resp = isImage
        ? await api.uploadImage(file)
        : await api.uploadVideo(file);
      const newRef: ReferenceAsset = {
        type: isImage ? 'image' : 'video',
        source: resp.file_path,
        purpose: 'overall',
        description: '',
      };
      updateSpec({ references: [...references, newRef] });
    } catch {
      // 上传失败静默处理
    } finally {
      setUploading(false);
    }
  };

  const update = (index: number, patch: Partial<ReferenceAsset>) => {
    const next = [...references];
    next[index] = { ...next[index], ...patch };
    updateSpec({ references: next });
  };

  const remove = (index: number) => {
    updateSpec({ references: references.filter((_, i) => i !== index) });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Text type="secondary">上传参考素材（图片/视频），按用途分类</Text>
      </div>

      {/* 上传区域 */}
      <label
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          border: '2px dashed #d9d9d9',
          borderRadius: 8,
          padding: '20px 12px',
          cursor: 'pointer',
          transition: 'border-color 0.2s',
          marginBottom: 16,
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files[0];
          if (file) handleFileSelect(file);
        }}
      >
        {uploading ? (
          <Spin size="small" />
        ) : (
          <>
            <InboxOutlined style={{ fontSize: 24, color: '#999', marginBottom: 4 }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              点击或拖拽文件上传
            </Text>
            <input
              type="file"
              accept="image/*,video/*"
              style={{ display: 'none' }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
                e.target.value = '';
              }}
            />
          </>
        )}
      </label>

      {/* 参考列表 */}
      {references.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无参考素材" />
      ) : (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {references.map((ref, i) => (
            <div
              key={i}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: 8,
                padding: 10,
              }}
            >
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                <Tag color={ref.type === 'image' ? 'blue' : 'purple'}>
                  {ref.type === 'image' ? '图片' : '视频'}
                </Tag>
                <Select
                  value={ref.purpose}
                  onChange={(v) => update(i, { purpose: v })}
                  size="small"
                  style={{ flex: 1 }}
                  options={PURPOSES}
                />
                <Button
                  danger
                  ghost
                  icon={<DeleteOutlined />}
                  size="small"
                  onClick={() => remove(i)}
                />
              </div>
              <Input
                value={ref.description ?? ''}
                onChange={(e) => update(i, { description: e.target.value })}
                placeholder="描述该参考的用途，如「主角外观参考」"
                size="small"
              />
              {ref.source && (
                <Text
                  type="secondary"
                  style={{ fontSize: 11, display: 'block', marginTop: 4, wordBreak: 'break-all' }}
                >
                  {ref.source.split(/[/\\]/).pop()}
                </Text>
              )}
            </div>
          ))}
        </Space>
      )}
    </div>
  );
}
