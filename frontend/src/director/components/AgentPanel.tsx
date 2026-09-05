import { useEffect, useRef, useState } from 'react';
import { Button, Input, Space, Typography } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { colors } from '../../theme';
import { useAgentStore } from '../agent/useAgentStore';
import { useDirectorStore } from '../store/useDirectorStore';

const { Text } = Typography;

const SHORTCUTS: Array<{ label: string; text: string }> = [
  { label: '创建角色', text: '创建一个女主角。' },
  { label: '创建场景', text: '布置一个客厅房间。' },
  { label: '创建镜头', text: '创建一个 5 秒镜头。' },
  { label: '添加动作', text: '让当前角色走路。' },
  { label: '调整镜头', text: '镜头慢慢推进。' },
  { label: '自动分镜', text: '根据当前场景自动生成一个分镜。' },
  { label: '生成提示词', text: '生成这个镜头的视频提示词。' },
  { label: '生成画面', text: '生成这个镜头的画面。' },
  { label: '生成视频', text: '把这个画面做成 5 秒视频。' },
];

export default function AgentPanel() {
  const messages = useAgentStore((s) => s.messages);
  const running = useAgentStore((s) => s.running);
  const pendingConfirm = useAgentStore((s) => s.pendingConfirm);
  const send = useAgentStore((s) => s.send);
  const confirmPending = useAgentStore((s) => s.confirmPending);
  const sceneName = useDirectorStore((s) => s.sceneName);
  const objects = useDirectorStore((s) => s.objects);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, running]);

  useEffect(() => {
    let prev = useDirectorStore.getState().selectedId;
    return useDirectorStore.subscribe((state) => {
      if (state.selectedId === prev || !state.selectedId) return;
      prev = state.selectedId;
      const obj = state.objects.find((o) => o.id === state.selectedId);
      if (obj?.characterId) {
        useAgentStore.getState().setFocus({ character_id: obj.characterId, object_id: obj.id });
      }
    });
  }, []);

  const submit = () => {
    const next = text.trim();
    if (!next) return;
    setText('');
    void send(next);
  };

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: colors.surface,
      }}
    >
      <div style={{ padding: '8px 12px', borderBottom: `1px solid ${colors.border}` }}>
        <Text strong>AI 导演</Text>
        <div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {sceneName} · {objects.filter((o) => o.characterId).length} 角色 · {objects.length} 物件
          </Text>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.length === 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            在导演台直接下指令，例如：「让女主角走到桌子旁边，然后坐下，镜头从中景慢慢推进到近景。」
          </Text>
        )}
        {messages.map((msg) => (
          <div key={msg.id} style={{ marginBottom: 12 }}>
            <Text strong style={{ fontSize: 12 }}>{msg.role === 'user' ? '你' : 'AI 导演'}</Text>
            {msg.text && (
              <div
                style={{
                  marginTop: 4,
                  padding: '6px 8px',
                  borderRadius: 8,
                  background: msg.role === 'user' ? '#f0f5ff' : '#fafafa',
                  fontSize: 13,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {msg.text}
              </div>
            )}
            {msg.steps.map((step) => (
              <div
                key={step.id}
                style={{
                  marginTop: 6,
                  fontSize: 12,
                  color: step.status === 'error' ? '#cf1322' : step.status === 'running' ? '#1677ff' : '#434343',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {step.kind === 'thinking' ? `· ${step.text}` : step.text}
                {step.prompt && (
                  <pre
                    style={{
                      marginTop: 6,
                      padding: 8,
                      background: '#111',
                      color: '#d9d9d9',
                      borderRadius: 6,
                      fontSize: 11,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {step.prompt}
                  </pre>
                )}
              </div>
            ))}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {pendingConfirm && (
        <div style={{ padding: 10, borderTop: `1px solid ${colors.border}`, background: '#fff7e6' }}>
          <Text style={{ fontSize: 12 }}>AI 导演准备：{pendingConfirm.note || pendingConfirm.name}</Text>
          <Space style={{ marginTop: 8 }}>
            <Button size="small" onClick={() => void confirmPending(false)}>取消</Button>
            <Button size="small" type="primary" danger onClick={() => void confirmPending(true)}>确认执行</Button>
          </Space>
        </div>
      )}

      <div style={{ padding: '8px 10px', borderTop: `1px solid ${colors.border}` }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
          {SHORTCUTS.map((item) => (
            <Button
              key={item.label}
              size="small"
              disabled={running}
              onClick={() => void send(item.text)}
            >
              {item.label}
            </Button>
          ))}
        </div>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={text}
            disabled={running}
            placeholder="告诉 Agent 要拍什么…"
            onChange={(e) => setText(e.target.value)}
            onPressEnter={submit}
          />
          <Button type="primary" icon={<SendOutlined />} loading={running} onClick={submit} />
        </Space.Compact>
      </div>
    </div>
  );
}
