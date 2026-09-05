import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Card, Empty, Input, Layout, Modal, Popconfirm, Select, Space, Tag, Typography, message,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, PlayCircleOutlined, PlusOutlined, SearchOutlined,
} from '@ant-design/icons';
import Sidebar from '../components/Sidebar';
import UserMenu from '../components/UserMenu';
import { mediaUrl } from '../api/client';
import {
  deleteWork, fetchUserWorks, updateWorkTitle, type GenerationVersion,
} from '../director/generationApi';
import { colors } from '../theme';

const { Title, Text, Paragraph } = Typography;

function formatTime(ts?: number): string {
  if (!ts) return '';
  const ms = ts < 1e12 ? ts * 1000 : ts;
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function statusTag(status: string) {
  if (status === 'completed') return <Tag color="success">已完成</Tag>;
  if (status === 'running' || status === 'pending') return <Tag color="processing">生成中</Tag>;
  if (status === 'failed') return <Tag color="error">失败</Tag>;
  return <Tag>{status}</Tag>;
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<GenerationVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [kind, setKind] = useState<'all' | 'video' | 'image'>('all');
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [playing, setPlaying] = useState<GenerationVersion | null>(null);
  const [renaming, setRenaming] = useState<GenerationVersion | null>(null);
  const [titleDraft, setTitleDraft] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await fetchUserWorks(kind === 'all' ? '' : kind, appliedQuery.trim() || undefined);
      setItems(rows);
    } catch {
      message.error('加载历史作品失败');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [kind, appliedQuery]);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => items, [items]);

  const startRename = (row: GenerationVersion) => {
    setRenaming(row);
    setTitleDraft(row.title || row.prompt || '');
  };

  const saveRename = async () => {
    if (!renaming) return;
    const title = titleDraft.trim();
    if (!title) {
      message.warning('请填写作品名称');
      return;
    }
    try {
      const updated = await updateWorkTitle(renaming.generation_id, title);
      setItems((prev) => prev.map((row) => (row.generation_id === updated.generation_id ? { ...row, ...updated } : row)));
      setRenaming(null);
      message.success('已改名');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '改名失败');
    }
  };

  const remove = async (row: GenerationVersion) => {
    try {
      await deleteWork(row.generation_id);
      setItems((prev) => prev.filter((item) => item.generation_id !== row.generation_id));
      if (playing?.generation_id === row.generation_id) setPlaying(null);
      message.success('已删除');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '删除失败');
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: colors.bg }}>
      <Sidebar />
      <Layout style={{ flex: 1, minHeight: 0, background: colors.bg }}>
        <Layout.Header
          style={{
            background: colors.surface,
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            height: 56,
            lineHeight: '56px',
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <Title level={4} style={{ margin: 0, fontWeight: 500, letterSpacing: '0.06em' }}>历史作品</Title>
          <UserMenu />
        </Layout.Header>
        <Layout.Content style={{ padding: 24, overflow: 'auto' }}>
          <div style={{ maxWidth: 1080, margin: '0 auto' }}>
            <Card style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <Input
                  allowClear
                  prefix={<SearchOutlined />}
                  placeholder="搜索作品名或提示词"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onPressEnter={() => setAppliedQuery(query)}
                  style={{ maxWidth: 320 }}
                />
                <Select
                  value={kind}
                  style={{ width: 120 }}
                  onChange={(v) => setKind(v)}
                  options={[
                    { value: 'all', label: '全部' },
                    { value: 'video', label: '视频' },
                    { value: 'image', label: '图片' },
                  ]}
                />
                <Button onClick={() => { setAppliedQuery(query); if (query === appliedQuery) void load(); }} loading={loading}>刷新</Button>
                <div style={{ flex: 1 }} />
                <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/director')}>
                  去导演台生成
                </Button>
              </div>
              <Paragraph type="secondary" style={{ margin: '12px 0 0' }}>
                这里是当前账号已经生成的成片。生成过程中也可以打开、改名或删除。
              </Paragraph>
            </Card>

            {visible.length === 0 && !loading ? (
              <Empty
                description="还没有成片，去导演台生成。"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" onClick={() => navigate('/director')}>进入导演台</Button>
              </Empty>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                {visible.map((row) => {
                  const preview = row.url ? mediaUrl(row.url) : '';
                  return (
                    <Card
                      key={row.generation_id}
                      hoverable
                      styles={{ body: { padding: 12 } }}
                      cover={
                        preview && row.kind === 'video' ? (
                          <video
                            src={preview}
                            muted
                            playsInline
                            preload="metadata"
                            style={{ width: '100%', height: 168, objectFit: 'cover', background: '#111', display: 'block' }}
                          />
                        ) : preview && row.kind === 'image' ? (
                          <img
                            src={preview}
                            alt={row.title || '作品'}
                            style={{ width: '100%', height: 168, objectFit: 'cover', display: 'block' }}
                          />
                        ) : (
                          <div style={{ height: 168, background: '#ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted }}>
                            {row.status === 'running' || row.status === 'pending' ? '生成中…' : '暂无预览'}
                          </div>
                        )
                      }
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <Text strong ellipsis style={{ flex: 1 }}>
                          {row.title || row.prompt || '未命名作品'}
                        </Text>
                        {statusTag(row.status)}
                      </div>
                      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 10 }}>
                        {row.kind === 'video' ? '视频' : '图片'}
                        {row.aspect_ratio ? ` · ${row.aspect_ratio}` : ''}
                        {row.duration ? ` · ${row.duration}s` : ''}
                        {row.created_at ? ` · ${formatTime(row.created_at)}` : ''}
                      </Text>
                      <Space size={6} wrap>
                        <Button size="small" icon={<PlayCircleOutlined />} disabled={!preview} onClick={() => setPlaying(row)}>
                          查看
                        </Button>
                        <Button size="small" icon={<EditOutlined />} onClick={() => startRename(row)}>
                          改名
                        </Button>
                        <Popconfirm title="删除这件作品？" description="删除后无法从历史里找回。" onConfirm={() => void remove(row)}>
                          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                        </Popconfirm>
                      </Space>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </Layout.Content>
      </Layout>

      <Modal
        title={playing?.title || '作品预览'}
        open={!!playing}
        onCancel={() => setPlaying(null)}
        footer={null}
        width={720}
        destroyOnClose
      >
        {playing?.url && playing.kind === 'video' && (
          <video src={mediaUrl(playing.url)} controls autoPlay style={{ width: '100%', borderRadius: 8 }} />
        )}
        {playing?.url && playing.kind === 'image' && (
          <img src={mediaUrl(playing.url)} alt={playing.title || ''} style={{ width: '100%', borderRadius: 8 }} />
        )}
        {playing?.prompt && (
          <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>{playing.prompt}</Paragraph>
        )}
      </Modal>

      <Modal
        title="修改作品名称"
        open={!!renaming}
        onCancel={() => setRenaming(null)}
        onOk={() => void saveRename()}
        okText="保存"
      >
        <Input
          value={titleDraft}
          maxLength={128}
          onChange={(e) => setTitleDraft(e.target.value)}
          onPressEnter={() => void saveRename()}
          placeholder="作品名称"
        />
      </Modal>
    </div>
  );
}
