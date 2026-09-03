import { useEffect, useState } from 'react';
import { Button, List, Popconfirm, Spin, Tag, Typography, message } from 'antd';
import { RetweetOutlined, SwapOutlined } from '@ant-design/icons';
import { api, RegistryModel } from '../api/client';

const { Text } = Typography;

interface Props {
  currentModelId: string;
  switching: boolean;
  onSwitch: (modelId: string) => void;
}

function stars(score: number): string {
  // 0-10 分映射为 0-5 星
  const n = Math.round(score / 2);
  return '★'.repeat(n) + '☆'.repeat(5 - n);
}

/**
 * 模型切换器:展示 AI 推荐的模型及原因,允许专业用户手动更换模型。
 * 切换后系统将按新模型能力重新编译 Prompt(模型感知)。
 */
export default function ModelSelector({ currentModelId, switching, onSwitch }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<RegistryModel[]>([]);

  useEffect(() => {
    if (!open || models.length > 0) return;
    setLoading(true);
    api.listRegistryModels()
      .then((all) => setModels(all.filter((m) => m.model_type === 'image_to_video' || m.model_type === 'text_to_video')))
      .catch(() => message.error('获取模型列表失败'))
      .finally(() => setLoading(false));
  }, [open, models.length]);

  return (
    <div>
      <Button
        size="small"
        icon={<SwapOutlined />}
        onClick={() => setOpen((v) => !v)}
        loading={switching}
      >
        更换模型
      </Button>

      {open && (
        <div style={{ marginTop: 10, border: '1px solid #f0f0f0', borderRadius: 8, padding: 8, background: '#fafafa' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin size="small" />
            </div>
          ) : models.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前无其他可用模型
            </Text>
          ) : (
            <List
              size="small"
              dataSource={models}
              renderItem={(m) => {
                const isCurrent = m.model_id === currentModelId;
                return (
                  <List.Item
                    style={{ padding: '8px 8px', borderRadius: 6, background: isCurrent ? '#f6f9ff' : undefined }}
                    actions={[
                      isCurrent ? (
                        <Tag color="blue" key="cur">当前</Tag>
                      ) : (
                        <Popconfirm
                          key="switch"
                          title={`切换到 ${m.model_name}?`}
                          description="切换后将按新模型能力重新编译 Prompt"
                          okText="切换"
                          cancelText="取消"
                          onConfirm={() => onSwitch(m.model_id)}
                        >
                          <Button size="small" icon={<RetweetOutlined />} loading={switching}>
                            切换
                          </Button>
                        </Popconfirm>
                      ),
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <span style={{ fontSize: 13 }}>
                          {m.model_name}
                          {m.supports_negative_prompt && (
                            <Tag style={{ marginLeft: 8, fontSize: 11 }}>支持负面提示词</Tag>
                          )}
                        </span>
                      }
                      description={
                        <span style={{ fontSize: 12 }}>
                          质量 {stars(m.quality_score)} · 速度 {stars(m.speed_score)} · 成本 {stars(10 - m.cost_score)}
                          {m.capabilities?.max_duration ? ` · 最长 ${m.capabilities.max_duration}s` : ''}
                        </span>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

