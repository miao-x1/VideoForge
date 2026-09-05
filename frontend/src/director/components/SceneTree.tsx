import { Button, List, Typography } from 'antd';
import { DeleteOutlined, EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import { useDirectorStore } from '../store/useDirectorStore';
import { colors, directorDark, radius } from '../../theme';

const { Text } = Typography;

export default function SceneTree({ embedded = false }: { embedded?: boolean }) {
  const objects = useDirectorStore((s) => s.objects);
  const cameras = useDirectorStore((s) => s.cameras);
  const selectedId = useDirectorStore((s) => s.selectedId);
  const activeCamera = useDirectorStore((s) => s.activeCamera);
  const selectObject = useDirectorStore((s) => s.selectObject);
  const selectCamera = useDirectorStore((s) => s.selectCamera);
  const removeObject = useDirectorStore((s) => s.removeObject);
  const updateObject = useDirectorStore((s) => s.updateObject);

  const body = (
    <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>对象</Text>
      <List
        size="small"
        dataSource={objects}
        locale={{ emptyText: '暂无对象' }}
        renderItem={(item) => {
          const active = selectedId === item.id;
          return (
            <List.Item
              onClick={() => selectObject(item.id)}
              style={{
                cursor: 'pointer',
                padding: '6px 8px',
                borderRadius: radius.item,
                background: active ? 'rgba(102,126,234,0.15)' : 'transparent',
                opacity: item.visible ? 1 : 0.45,
              }}
              actions={[
                <Button
                  key="vis"
                  type="text"
                  size="small"
                  icon={item.visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    updateObject(item.id, { visible: !item.visible });
                  }}
                />,
                <Button
                  key="del"
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeObject(item.id);
                  }}
                />,
              ]}
            >
              <Text ellipsis style={{ maxWidth: 120, color: directorDark.text }}>
                {item.name}
              </Text>
            </List.Item>
          );
        }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>机位</Text>
      <List
        size="small"
        dataSource={cameras}
        renderItem={(cam) => {
          const active = selectedId === cam.id || activeCamera === cam.id;
          return (
            <List.Item
              onClick={() => selectCamera(cam.id)}
              style={{
                cursor: 'pointer',
                padding: '6px 8px',
                borderRadius: radius.item,
                background: active ? 'rgba(54,207,201,0.16)' : 'transparent',
              }}
            >
              <Text ellipsis style={{ color: directorDark.text }}>{cam.name}</Text>
            </List.Item>
          );
        }}
      />
    </div>
  );

  if (embedded) return body;

  return (
    <div
      style={{
        width: 240,
        flexShrink: 0,
        background: colors.surface,
        borderRight: `1px solid ${colors.border}`,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.border}` }}>
        <Text strong>Scene Tree</Text>
      </div>
      {body}
    </div>
  );
}
