import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Card, Table, Tag, Button, Typography, Space, Input, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import Sidebar from '../components/Sidebar';
import UserMenu from '../components/UserMenu';
import { api, type TaskBrief, type SearchResult } from '../api/client';
import { colors } from '../theme';

const { Title, Text, Paragraph } = Typography;

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'default',
  ANALYZING: 'processing',
  SCRIPTING: 'processing',
  COMPLIANCE_CHECKING: 'processing',
  STORYBOARDING: 'processing',
  GENERATING_ASSETS: 'processing',
  ASSEMBLING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error',
  HUMAN_REVIEW: 'warning',
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskBrief[]>([]);
  const [loading, setLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    api.listTasks()
      .then(setTasks)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const results = await api.searchVideos(q);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const columns = [
    {
      title: '创意',
      dataIndex: 'user_input',
      key: 'user_input',
      ellipsis: true,
      width: '40%',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={STATUS_COLORS[status] || 'default'}>{status}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (ts: number) => new Date(ts * 1000).toLocaleString('zh-CN'),
    },
    {
      title: '模型',
      dataIndex: 'model_used',
      key: 'model_used',
      render: (model: string) => model ? <Tag>{model}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: TaskBrief) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/?task=${record.task_id}`)}
          disabled={record.status === 'PENDING' || record.status === 'FAILED'}
        >
          查看结果
        </Button>
      ),
    },
  ];

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
          <Title level={4} style={{ margin: 0 }}>我的视频历史</Title>
          <UserMenu />
        </Layout.Header>
        <Layout.Content style={{ padding: 24, overflow: 'auto' }}>
          <div style={{ maxWidth: 960, margin: '0 auto' }}>

      <Card style={{ marginBottom: 16 }}>
        <Text type="secondary">语义搜索历史视频</Text>
        <Space.Compact style={{ width: '100%', marginTop: 8 }}>
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="输入关键词搜索,如「搞笑」「古代人」"
            onPressEnter={handleSearch}
            prefix={<SearchOutlined />}
            allowClear
          />
          <Button type="primary" onClick={handleSearch} loading={searching}>
            搜索
          </Button>
        </Space.Compact>

        {searchResults !== null && (
          <div style={{ marginTop: 16 }}>
            {searchResults.length === 0 ? (
              <Empty description="未找到相关视频" />
            ) : (
              <div>
                <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                  找到 {searchResults.length} 个相关视频(按语义相似度排序)
                </Paragraph>
                {searchResults.map((r) => (
                  <Card
                    key={r.video_id}
                    size="small"
                    style={{ marginBottom: 8 }}
                    onClick={() => navigate(`/?task=${r.video_id}`)}
                    hoverable
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Space>
                        <Text strong>{r.metadata.title || r.video_id}</Text>
                        {r.metadata.quality_grade && (
                          <Tag color="gold">质量 {r.metadata.quality_grade}</Tag>
                        )}
                        <Tag color="blue">相似度 {(r.score * 100).toFixed(0)}%</Tag>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {r.semantic_description}
                      </Text>
                      {r.metadata.tags && r.metadata.tags.length > 0 && (
                        <Space size={4} wrap>
                          {r.metadata.tags.map((tag, i) => (
                            <Tag key={i}>{tag}</Tag>
                          ))}
                        </Space>
                      )}
                    </Space>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="task_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无生成记录' }}
        />
      </Card>
          </div>
        </Layout.Content>
      </Layout>
    </div>
  );
}
