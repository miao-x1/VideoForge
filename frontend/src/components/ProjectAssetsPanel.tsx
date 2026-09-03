import { useCallback, useEffect, useState } from 'react';
import { Button, Empty, message, Popconfirm, Select, Spin, Tag, Typography } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { api } from '../api/client';
import type { AssetInfo } from '../api/client';
import { colors } from '../theme';

const { Text, Paragraph } = Typography;

/** 资产类型 → 中文 */
const TYPE_LABELS: Record<string, string> = {
  image: '图片', video: '视频', audio: '音频',
  person: '角色参考', scene: '场景参考', object: '道具',
  style: '风格参考', reference: '参考', voice: '语音', music: '音乐',
};

const FILTER_OPTIONS = [
  { label: '全部类型', value: '' },
  ...Object.entries(TYPE_LABELS).map(([value, label]) => ({ label, value })),
];

/** 判断资产文件是否可直接预览 */
function previewKind(asset: AssetInfo): 'image' | 'video' | 'audio' | null {
  const path = asset.file_path || '';
  const mime = asset.media_type || '';
  if (mime.startsWith('image') || /\.(png|jpe?g|webp|gif)$/i.test(path)) return 'image';
  if (mime.startsWith('video') || /\.(mp4|mov|webm)$/i.test(path)) return 'video';
  if (mime.startsWith('audio') || /\.(mp3|wav|m4a|aac)$/i.test(path)) return 'audio';
  return null;
}

interface Props {
  projectId: string;
  /** 资产变化回调(删除后通知父级刷新计数) */
  onChanged?: () => void;
}

/**
 * 项目素材库面板:真实读取 /api/assets(生成完成时后端自动登记的成片/镜头图 + 手动添加的参考素材)。
 */
export default function ProjectAssetsPanel({ projectId, onChanged }: Props) {
  const [loading, setLoading] = useState(true);
  const [assets, setAssets] = useState<AssetInfo[]>([]);
  const [filter, setFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listAssets(filter ? { project_id: projectId, asset_type: filter } : { project_id: projectId });
      setAssets(list);
    } catch {
      message.error('加载项目素材失败');
    } finally {
      setLoading(false);
    }
  }, [projectId, filter]);

  useEffect(() => { load(); }, [load]);

  const remove = useCallback(async (assetId: string) => {
    try {
      await api.deleteAsset(assetId);
      message.success('素材已删除');
      setAssets((prev) => prev.filter((a) => a.id !== assetId));
      onChanged?.();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除素材失败');
    }
  }, [onChanged]);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Text strong>项目素材({assets.length})</Text>
        <Select
          size="small" style={{ width: 140 }} value={filter}
          options={FILTER_OPTIONS} onChange={setFilter}
        />
      </div>
      {assets.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无项目素材。任务完成生成的成片与镜头图会自动登记到这里"
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
          {assets.map((a) => {
            const kind = previewKind(a);
            const typeLabel = TYPE_LABELS[a.asset_type] || a.asset_type;
            return (
              <div key={a.id} style={{ border: `1px solid ${colors.border}`, borderRadius: 10, overflow: 'hidden', background: colors.surface }}>
                {kind === 'image' && (
                  <img src={a.file_path!} alt={a.name} style={{ width: '100%', height: 120, objectFit: 'cover', display: 'block' }} />
                )}
                {kind === 'video' && (
                  <video src={a.file_path!} controls style={{ width: '100%', height: 120, objectFit: 'contain', display: 'block', background: '#000' }} />
                )}
                {kind === 'audio' && (
                  <div style={{ padding: '42px 12px' }}><audio src={a.file_path!} controls style={{ width: '100%' }} /></div>
                )}
                {!kind && (
                  <div style={{ padding: '42px 12px', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 22 }}>📄</div>
                )}
                <div style={{ padding: '8px 10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    <Text ellipsis style={{ flex: 1, fontSize: 13 }}>{a.name}</Text>
                    <Popconfirm title="删除该素材?" onConfirm={() => remove(a.id)}>
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                  <Tag style={{ marginRight: 0, fontSize: 11 }}>{typeLabel}</Tag>
                  {a.description && (
                    <Paragraph type="secondary" style={{ fontSize: 11, marginBottom: 0, marginTop: 4 }} ellipsis={{ rows: 2 }}>
                      {a.description}
                    </Paragraph>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
