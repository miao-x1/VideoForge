import { useState } from 'react';
import { Button, Input, Modal, Typography } from 'antd';
import { RedoOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

interface Props {
  /** 按钮文案 */
  label?: string;
  /** 仅图标模式(紧凑场景如镜头行内操作) */
  iconOnly?: boolean;
  /** 反馈提示标题 */
  title?: string;
  /** 示例提示(展示给用户的"哪里不满意"样例) */
  placeholder?: string;
  /** 提交重生成(feedback 可为空=直接重生成) */
  onRegenerate: (feedback: string | undefined) => void | Promise<void>;
  disabled?: boolean;
  loading?: boolean;
  size?: 'small' | 'middle';
}

/**
 * Decision Loop 反馈重生成:点击"重新生成"先让用户表达"哪里不满意"(可留空)。
 * 反馈会注入 LLM 重生成上下文,实现定向修改而非盲目重抽卡。
 */
export default function RegenerateWithFeedback({
  label = '重新生成',
  iconOnly = false,
  title,
  placeholder = '例如:节奏太慢,中间增加一个转折',
  onRegenerate,
  disabled,
  loading,
  size = 'middle',
}: Props) {
  const [open, setOpen] = useState(false);
  const [feedback, setFeedback] = useState('');

  const submit = (withFeedback: boolean) => {
    setOpen(false);
    const fb = withFeedback ? feedback.trim() || undefined : undefined;
    setFeedback('');
    void onRegenerate(fb);
  };

  return (
    <>
      <Button
        icon={<RedoOutlined />}
        disabled={disabled}
        loading={loading}
        size={size}
        onClick={() => setOpen(true)}
        title={iconOnly ? label : undefined}
      >
        {iconOnly ? null : label}
      </Button>
      <Modal
        open={open}
        title={title || '告诉 AI 哪里不满意'}
        onCancel={() => setOpen(false)}
        okText="带反馈重新生成"
        onOk={() => submit(true)}
        okButtonProps={{ disabled: loading }}
        cancelButtonProps={{ disabled: loading }}
        destroyOnClose
        width={480}
      >
        <Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 13 }}>
          描述你的修改期望,AI 会据此定向重生成,而不是盲目重抽卡。留空则直接重新生成。
        </Paragraph>
        <Input.TextArea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder={placeholder}
          rows={3}
          maxLength={300}
          showCount
          autoFocus
        />
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Text
            type="secondary"
            style={{ fontSize: 12, cursor: 'pointer' }}
            onClick={() => submit(false)}
          >
            跳过反馈,直接重新生成
          </Text>
        </div>
      </Modal>
    </>
  );
}
