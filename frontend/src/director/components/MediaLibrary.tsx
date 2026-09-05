import { useEffect, useState } from 'react';
import { Button, Typography, Upload, message } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { directorDark } from '../../theme';
import { deleteDirectorAsset, listDirectorAssets, uploadDirectorAsset, type DirectorAsset } from '../assetApi';
import { mediaUrl } from '../../api/client';
import { applySceneCanvas } from '../sceneCanvas';

const { Text } = Typography;

export default function MediaLibrary() {
  const [items, setItems] = useState<DirectorAsset[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      setItems(await listDirectorAssets());
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div style={{ padding: 8 }}>
      <Upload
        accept="image/*,video/*,.glb,.gltf"
        showUploadList={false}
        beforeUpload={async (file) => {
          try {
            const type = file.type.startsWith('video/') ? 'video' : file.name.match(/\.glb|\.gltf/i) ? 'model' : 'image';
            await uploadDirectorAsset(file, type);
            message.success('已上传到素材库');
            await refresh();
          } catch (e: unknown) {
            message.error(e instanceof Error ? e.message : '上传失败');
          }
          return false;
        }}
      >
        <Button size="small" type="primary" block loading={loading} style={{ marginBottom: 10 }}>
          上传素材
        </Button>
      </Upload>
      {items.length === 0 && (
        <Text style={{ color: directorDark.muted, fontSize: 12 }}>还没有素材。上传图片可作为构图参考。</Text>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((item) => (
          <div
            key={item.id}
            style={{
              border: `1px solid ${directorDark.border}`,
              borderRadius: 8,
              padding: 8,
              background: directorDark.panel,
            }}
          >
            <div style={{ color: directorDark.text, fontSize: 12, fontWeight: 600 }}>{item.name}</div>
            <div style={{ color: directorDark.muted, fontSize: 11, margin: '4px 0 8px' }}>
              {item.asset_type || item.mime_type || 'file'}
            </div>
            {item.url && item.mime_type?.startsWith('image/') && (
              <img src={mediaUrl(item.url)} alt="" style={{ width: '100%', borderRadius: 6, marginBottom: 8 }} />
            )}
            <div style={{ display: 'flex', gap: 6 }}>
              {item.url && item.mime_type?.startsWith('image/') && (
                <Button
                  size="small"
                  onClick={() => {
                    applySceneCanvas(mediaUrl(item.url || ''));
                    message.success('已贴到 3D 画布');
                  }}
                >
                  贴到画布
                </Button>
              )}
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={async () => {
                  await deleteDirectorAsset(item.id);
                  await refresh();
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
