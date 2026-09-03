import { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Empty, List, Modal, Popconfirm, Spin, Tag, Timeline, Typography, message,
} from 'antd';
import { HistoryOutlined, RestOutlined } from '@ant-design/icons';
import { api } from '../api/client';
import type { TaskVersionEntry, TaskVersionNodeInfo } from '../api/client';

const { Text } = Typography;

interface Props {
  taskId: string;
  /** 版本历史变化时外部触发刷新(如局部重生成完成) */
  refreshKey?: number;
  /** 恢复版本后通知外部刷新任务状态 */
  onRestored?: (nodeType: string) => void;
}

const REASON_COLORS: Record<string, string> = {
  初始生成: 'blue',
  初始编译: 'blue',
  用户编辑: 'orange',
  重新生成: 'purple',
  局部修改: 'cyan',
};

function reasonColor(reason: string): string {
  if (reason.startsWith('回退')) return 'red';
  return REASON_COLORS[reason] || 'default';
}

/**
 * 版本历史面板:展示任务内关键节点(创作方案/脚本/分镜/Prompt)的版本历史,
 * 支持查看各版本并恢复到任意历史版本。恢复后可基于该版本继续重新生成。
 */
export default function VersionHistoryPanel({ taskId, refreshKey, onRestored }: Props) {
  const [nodes, setNodes] = useState<TaskVersionNodeInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [versions, setVersions] = useState<TaskVersionEntry[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [restoring, setRestoring] = useState<number | null>(null);

  const loadNodes = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.listTaskVersions(taskId);
      setNodes(resp.nodes);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '版本列表加载失败');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    loadNodes();
  }, [loadNodes, refreshKey]);

  const openHistory = async (nodeType: string) => {
    setActiveNode(nodeType);
    setVersionsLoading(true);
    try {
      const resp = await api.getTaskVersionHistory(taskId, nodeType);
      setVersions(resp.versions);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '版本历史加载失败');
    } finally {
      setVersionsLoading(false);
    }
  };

  const restore = async (nodeType: string, version: number) => {
    setRestoring(version);
    try {
      const resp = await api.restoreTaskVersion(taskId, nodeType, version);
      message.success(resp.message || `已恢复 v${version}`);
      setActiveNode(null);
      await loadNodes();
      onRestored?.(nodeType);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '版本恢复失败');
    } finally {
      setRestoring(null);
    }
  };

  return (
    <Card size="small" style={{ marginTop: 16 }} title={<Text strong><HistoryOutlined /> 版本历史</Text>}>
      <Spin spinning={loading}>
        {nodes.length === 0 ? (
          <Empty description="暂无版本记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            size="small"
            dataSource={nodes}
            renderItem={(node) => (
              <List.Item
                actions={[
                  <Button
                    key="view"
                    type="link"
                    size="small"
                    onClick={() => openHistory(node.node_type)}
                  >
                    查看历史
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <span>
                      {node.label}
                      <Tag style={{ marginLeft: 8 }}>v{node.latest_version}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>共 {node.version_count} 个版本</Text>
                    </span>
                  }
                  description={node.latest_reason}
                />
              </List.Item>
            )}
          />
        )}
      </Spin>

      <Modal
        open={activeNode !== null}
        title={`版本历史 - ${nodes.find((n) => n.node_type === activeNode)?.label ?? activeNode}`}
        onCancel={() => setActiveNode(null)}
        footer={null}
        width={560}
      >
        <Spin spinning={versionsLoading}>
          {versions.length === 0 ? (
            <Empty description="无版本" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Timeline
              items={versions.map((v) => ({
                color: v.reason.startsWith('回退') ? 'red' : 'blue',
                children: (
                  <div>
                    <div>
                      <Text strong>v{v.version}</Text>
                      <Tag style={{ marginLeft: 8 }} color={reasonColor(v.reason)}>{v.reason}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(v.ts * 1000).toLocaleString('zh-CN')}
                      </Text>
                    </div>
                    {v.label && <Text type="secondary" style={{ fontSize: 12 }}>{v.label}</Text>}
                    <div style={{ marginTop: 4 }}>
                      <Popconfirm
                        title={`恢复到 ${nodes.find((n) => n.node_type === activeNode)?.label ?? ''} v${v.version}?`}
                        description="恢复后可基于该版本继续重新生成"
                        onConfirm={() => activeNode && restore(activeNode, v.version)}
                      >
                        <Button
                          size="small"
                          icon={<RestOutlined />}
                          loading={restoring === v.version}
                          disabled={restoring !== null && restoring !== v.version}
                        >
                          恢复此版本
                        </Button>
                      </Popconfirm>
                    </div>
                  </div>
                ),
              }))}
            />
          )}
        </Spin>
      </Modal>
    </Card>
  );
}
