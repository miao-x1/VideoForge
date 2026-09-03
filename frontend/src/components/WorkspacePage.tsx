import { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Empty, List, message, Popconfirm, Spin, Tag, Typography,
} from 'antd';
import {
  PlusOutlined, PlayCircleOutlined, FolderOpenOutlined, DeleteOutlined,
  ReloadOutlined, VideoCameraOutlined,
} from '@ant-design/icons';
import { api } from '../api/client';
import type { ProjectDetail, ProjectInfo, ProjectTaskBrief, TaskBrief, TaskStatus } from '../api/client';
import { cardStyle, colors } from '../theme';

const { Title, Paragraph, Text } = Typography;

/** 任务状态 → 中文标签与颜色 */
const STATUS_META: Record<TaskStatus, { label: string; color: string }> = {
  PENDING: { label: '排队中', color: 'default' },
  ANALYZING: { label: '分析创意', color: 'processing' },
  SCRIPTING: { label: '生成脚本', color: 'processing' },
  COMPLIANCE_CHECKING: { label: '合规预审', color: 'processing' },
  SCRIPT_REVIEW: { label: '待确认脚本', color: 'warning' },
  STORYBOARDING: { label: '生成分镜', color: 'processing' },
  STORYBOARD_REVIEW: { label: '待确认分镜', color: 'warning' },
  GENERATING_ASSETS: { label: '生成素材', color: 'processing' },
  PROMPT_REVIEW: { label: '待确认Prompt', color: 'warning' },
  ASSEMBLING: { label: '合成成片', color: 'processing' },
  COMPLETED: { label: '已完成', color: 'success' },
  FAILED: { label: '失败', color: 'error' },
  HUMAN_REVIEW: { label: '待人工审核', color: 'warning' },
};

const TERMINAL: TaskStatus[] = ['COMPLETED', 'FAILED'];

export function statusMeta(status: TaskStatus) {
  return STATUS_META[status] ?? { label: status, color: 'default' };
}

function formatTime(ts: number): string {
  const ms = ts < 1e12 ? ts * 1000 : ts;
  const d = new Date(ms);
  const now = Date.now();
  const diff = (now - ms) / 1000;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, '0')}`;
}

interface Props {
  onNewCreation: () => void;
  onOpenTask: (taskId: string) => void;
}

/**
 * 项目工作台首页:
 * - 新建作品入口
 * - 进行中任务(可恢复,含刷新后失忆修复)
 * - 最近作品(项目卡片,展开查看集内任务)
 * - 最近任务
 */
export default function WorkspacePage({ onNewCreation, onOpenTask }: Props) {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<TaskBrief[]>([]);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  // 展开的项目详情(点击项目卡片加载)
  const [expandedId, setExpandedId] = useState<string>('');
  const [expandedDetail, setExpandedDetail] = useState<ProjectDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [taskList, projectList] = await Promise.all([
        api.listTasks().catch(() => [] as TaskBrief[]),
        api.listProjects().catch(() => [] as ProjectInfo[]),
      ]);
      setTasks(taskList);
      setProjects(projectList);
    } catch {
      if (!silent) message.error('加载工作台数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runningTasks = tasks.filter((t) => !TERMINAL.includes(t.status));
  const recentTasks = tasks.slice(0, 10);

  const openProject = useCallback(async (projectId: string) => {
    if (expandedId === projectId) {
      setExpandedId('');
      setExpandedDetail(null);
      return;
    }
    setExpandedId(projectId);
    setExpandedDetail(null);
    setDetailLoading(true);
    try {
      const detail = await api.getProject(projectId);
      setExpandedDetail(detail);
    } catch {
      message.error('加载作品详情失败');
      setExpandedId('');
    } finally {
      setDetailLoading(false);
    }
  }, [expandedId]);

  const deleteProject = useCallback(async (projectId: string) => {
    try {
      await api.deleteProject(projectId);
      message.success('作品已删除');
      if (expandedId === projectId) {
        setExpandedId('');
        setExpandedDetail(null);
      }
      load(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除作品失败');
    }
  }, [expandedId, load]);

  const renderTaskItem = (t: { task_id: string; user_input: string; status: TaskStatus; model_used: string; created_at: number }, extra?: React.ReactNode) => {
    const meta = statusMeta(t.status);
    return (
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
          borderRadius: 8, cursor: 'pointer', border: `1px solid ${colors.border}`,
          background: colors.surface, marginBottom: 8,
        }}
        onClick={() => onOpenTask(t.task_id)}
      >
        <VideoCameraOutlined style={{ fontSize: 16, color: '#8b5cf6', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text ellipsis style={{ flex: 1, fontSize: 13 }}>
              {t.user_input || '未命名创作'}
            </Text>
            <Tag color={meta.color} style={{ marginRight: 0 }}>{meta.label}</Tag>
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatTime(t.created_at)}{t.model_used ? ` · ${t.model_used}` : ''}
          </Text>
        </div>
        {extra}
        <Button type="primary" size="small" ghost icon={<PlayCircleOutlined />}>
          {TERMINAL.includes(t.status) ? '查看' : '继续'}
        </Button>
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', width: '100%' }}>
      {/* 新建作品 */}
      <Card style={{ ...cardStyle, marginBottom: 16, textAlign: 'center', padding: 8 }}>
        <Title level={3} style={{ marginBottom: 4 }}>开始一个新的作品</Title>
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          输入你的创意,AI 将生成创作方案、作品设定、剧本与分镜,逐步确认后产出成片
        </Paragraph>
        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          onClick={onNewCreation}
        >
          新建作品
        </Button>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* 进行中任务 */}
          {runningTasks.length > 0 && (
            <Card
              style={{ ...cardStyle, marginBottom: 16 }}
              title={`进行中的创作(${runningTasks.length})`}
              extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>}
            >
              {runningTasks.map((t) => renderTaskItem(t))}
              <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
                刷新页面或换设备后,这里都可以继续未完成的创作
              </Paragraph>
            </Card>
          )}

          {/* 最近作品 */}
          <Card
            style={{ ...cardStyle, marginBottom: 16 }}
            title={<span><FolderOpenOutlined style={{ marginRight: 8 }} />我的作品</span>}
            extra={
              <Button size="small" icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>
            }
          >
            {projects.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="还没有作品,从上面的「新建作品」开始"
              />
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
                {projects.map((p) => (
                  <div key={p.id}>
                    <div
                      onClick={() => openProject(p.id)}
                      style={{
                        padding: '14px 16px', borderRadius: 10,
                        border: `1px solid ${expandedId === p.id ? '#8b5cf6' : colors.border}`,
                        background: colors.surface, cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <Text strong style={{ flex: 1 }} ellipsis>{p.title}</Text>
                        {p.is_series && <Tag color="purple" style={{ marginRight: 0 }}>系列</Tag>}
                        <Popconfirm
                          title="删除作品"
                          description="删除作品不删除其任务记录,确定删除?"
                          onConfirm={(e) => { e?.stopPropagation(); deleteProject(p.id); }}
                          onCancel={(e) => e?.stopPropagation()}
                        >
                          <Button
                            size="small" type="text" danger icon={<DeleteOutlined />}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </Popconfirm>
                      </div>
                      {p.description && (
                        <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 6 }} ellipsis={{ rows: 1 }}>
                          {p.description}
                        </Paragraph>
                      )}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {p.task_count} 次创作 · {p.asset_count} 个素材 · {formatTime(p.updated_at)}
                      </Text>
                    </div>
                    {/* 展开作品内任务 */}
                    {expandedId === p.id && (
                      <div style={{ padding: '10px 4px 2px' }}>
                        {detailLoading ? (
                          <div style={{ textAlign: 'center', padding: 16 }}><Spin /></div>
                        ) : expandedDetail ? (
                          expandedDetail.tasks.length === 0 ? (
                            <Text type="secondary" style={{ fontSize: 12 }}>该作品还没有创作记录</Text>
                          ) : (
                            expandedDetail.tasks.map((t: ProjectTaskBrief) => renderTaskItem(t))
                          )
                        ) : null}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* 最近任务 */}
          <Card style={cardStyle} title={`最近创作(${recentTasks.length})`}>
            {recentTasks.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有创作记录" />
            ) : (
              <List
                dataSource={recentTasks}
                renderItem={(t) => renderTaskItem(t)}
              />
            )}
          </Card>
        </>
      )}
    </div>
  );
}
