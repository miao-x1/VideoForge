import { useEffect, useState } from 'react';
import { Button, Dropdown, Input, Modal, Typography, message } from 'antd';
import { DownOutlined, FolderOpenOutlined, PlusOutlined } from '@ant-design/icons';
import { api, type ProjectInfo } from '../../api/client';
import { getDirectorProjectId, setDirectorProjectId } from '../scope';
import { applyScopedLocalCaches, hydrateDirectorFromBackend } from '../sync';
import { useDirectorStore } from '../store/useDirectorStore';
import { directorDark } from '../../theme';

const { Text } = Typography;

export default function ProjectSwitcher({
  projectId,
  onChanged,
}: {
  projectId: string;
  onChanged: (id: string, title: string) => void;
}) {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [title, setTitle] = useState('导演台');
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const persistNow = useDirectorStore((s) => s.persistNow);

  const load = async (id: string) => {
    try {
      const list = await api.listProjects();
      setProjects(list);
      const current = list.find((p) => p.id === id);
      setTitle(current?.title || '导演台');
      if (current) onChanged(current.id, current.title);
    } catch {
      setTitle('导演台');
    }
  };

  useEffect(() => {
    if (projectId) void load(projectId);
  }, [projectId]);

  const switchTo = async (id: string) => {
    if (id === getDirectorProjectId()) return;
    persistNow();
    setDirectorProjectId(id);
    applyScopedLocalCaches();
    await hydrateDirectorFromBackend();
    const next = projects.find((p) => p.id === id);
    setTitle(next?.title || '导演台');
    onChanged(id, next?.title || '导演台');
    message.success(`已切换到「${next?.title || '项目'}」`);
  };

  const create = async () => {
    const next = name.trim();
    if (!next) return;
    try {
      persistNow();
      const created = await api.createProject({ title: next });
      setDirectorProjectId(created.id);
      applyScopedLocalCaches();
      await hydrateDirectorFromBackend();
      setCreating(false);
      setName('');
      await load(created.id);
      message.success('项目已创建');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '创建项目失败');
    }
  };

  return (
    <>
      <Dropdown
        trigger={['click']}
        menu={{
          items: [
            ...projects.slice(0, 8).map((p) => ({
              key: p.id,
              icon: <FolderOpenOutlined />,
              label: p.title,
              onClick: () => void switchTo(p.id),
            })),
            { type: 'divider' as const },
            {
              key: 'new',
              icon: <PlusOutlined />,
              label: '新建项目',
              onClick: () => setCreating(true),
            },
          ],
        }}
      >
        <Button type="text" style={{ color: directorDark.text, maxWidth: 220 }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {title}
          </span>
          <DownOutlined style={{ fontSize: 10, marginLeft: 6, color: directorDark.muted }} />
        </Button>
      </Dropdown>
      <Modal
        title="新建项目"
        open={creating}
        onCancel={() => setCreating(false)}
        onOk={() => void create()}
        okText="创建"
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          项目用于隔离角色、场景和生成记录。
        </Text>
        <Input
          autoFocus
          value={name}
          placeholder="项目名称"
          onChange={(e) => setName(e.target.value)}
          onPressEnter={() => void create()}
        />
      </Modal>
    </>
  );
}
