import { useState } from 'react';
import { Input, Modal, message } from 'antd';
import { useDirectorStore } from '../store/useDirectorStore';
import { planAutoStage } from '../directing/autoStage';

export default function AutoStageModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [text, setText] = useState('两个人在雨夜街头争吵');
  const applyAutoStage = useDirectorStore((s) => s.applyAutoStage);
  const preview = planAutoStage(text);

  return (
    <Modal
      title="AI 自动布景"
      open={open}
      onCancel={onClose}
      okText="布置到摄影棚"
      cancelText="继续手改"
      onOk={() => {
        const summary = applyAutoStage(text);
        message.success(summary);
        onClose();
      }}
    >
      <div style={{ color: '#9a9286', fontSize: 12, marginBottom: 8 }}>
        根据文字生成场景、站位、灯光和机位。不会锁死，布置后仍可在 3D 里改。
      </div>
      <Input.TextArea
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="两个人在雨夜街头争吵"
      />
      <div style={{ marginTop: 12, padding: 10, background: '#16141c', borderRadius: 8, color: '#f4efe6', fontSize: 12 }}>
        {preview.summary}
      </div>
    </Modal>
  );
}
