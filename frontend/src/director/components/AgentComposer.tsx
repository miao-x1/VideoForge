import { useState } from 'react';
import { Button, Input, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useAgentStore } from '../agent/useAgentStore';

const SKILLS: Array<{ label: string; text?: string; action?: 'stage' | 'compose' }> = [
  { label: '打开导演台', action: 'stage' },
  { label: '发送构图', action: 'compose' },
  { label: '拆分镜', text: '一个女生晚上回到家，把包放下然后坐在沙发上，显得很疲惫。' },
  { label: '生成画面', text: '生成这个镜头的画面。' },
  { label: '生成视频', text: '把这个画面做成 5 秒视频。' },
  { label: '改成特写', text: '最后一个镜头改成脸部特写。' },
];

function lastStatus(
  messages: ReturnType<typeof useAgentStore.getState>['messages'],
  running: boolean,
): string | null {
  const agent = [...messages].reverse().find((m) => m.role === 'agent');
  if (!agent) return running ? '正在理解你的意图…' : null;
  const step = [...agent.steps].reverse().find((s) => s.text);
  if (step?.text) return step.text.split('\n')[0];
  if (agent.text) return agent.text.split('\n')[0];
  return running ? '正在理解你的意图…' : null;
}

export default function AgentComposer({
  onOpenStage,
  onSendComposition,
}: {
  onOpenStage: () => void;
  onSendComposition: () => void;
}) {
  const running = useAgentStore((s) => s.running);
  const send = useAgentStore((s) => s.send);
  const messages = useAgentStore((s) => s.messages);
  const pendingConfirm = useAgentStore((s) => s.pendingConfirm);
  const confirmPending = useAgentStore((s) => s.confirmPending);
  const status = lastStatus(messages, running);
  const [text, setText] = useState('');

  const submit = () => {
    const next = text.trim();
    if (!next) return;
    setText('');
    void send(next);
  };

  return (
    <div
      style={{
        flexShrink: 0,
        background: '#11111a',
        borderTop: '1px solid #2a2a3a',
        padding: '10px 16px 12px',
      }}
    >
      {status && (
        <div
          style={{
            marginBottom: 8,
            color: '#bfbfbf',
            fontSize: 12,
            maxHeight: 40,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
          }}
        >
          Agent：{status}
        </div>
      )}
      {pendingConfirm && (
        <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#faad14', fontSize: 12 }}>
            {pendingConfirm.note || `确认执行 ${pendingConfirm.name}？`}
          </span>
          <Button size="small" onClick={() => void confirmPending(false)}>取消</Button>
          <Button size="small" type="primary" onClick={() => void confirmPending(true)}>确认执行</Button>
        </div>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        {SKILLS.map((skill) => (
          <Button
            key={skill.label}
            size="small"
            disabled={running && skill.action !== 'stage'}
            onClick={() => {
              if (skill.action === 'stage') onOpenStage();
              else if (skill.action === 'compose') onSendComposition();
              else if (skill.text) void send(skill.text);
            }}
          >
            {skill.label}
          </Button>
        ))}
      </div>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          size="large"
          value={text}
          disabled={running}
          placeholder="说出你的创意，或者从一个 skill 开始创作"
          onChange={(e) => setText(e.target.value)}
          onPressEnter={submit}
        />
        <Button type="primary" size="large" icon={<SendOutlined />} loading={running} onClick={submit} />
      </Space.Compact>
    </div>
  );
}
