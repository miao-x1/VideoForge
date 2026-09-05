import { Button, Modal, Typography } from 'antd';
import { directorDark } from '../../theme';

const { Title, Paragraph, Text } = Typography;

const STEPS = [
  { n: '第一步', t: '创建你的第一个角色', d: '从官方模板开始，或上传已绑定骨骼的 GLB 模型。' },
  { n: '第二步', t: '创建场景', d: '用场景预设或道具布置空间，把角色放到镜头里。' },
  { n: '第三步', t: '制作第一个镜头', d: '调整摄像机和景别，然后生成图片或视频。' },
];

export default function OnboardingModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          开始创作
        </Button>
      }
      width={520}
      destroyOnClose
    >
      <Title level={4} style={{ color: directorDark.text, marginTop: 8 }}>
        欢迎来到 AI 导演台
      </Title>
      <Paragraph style={{ color: directorDark.muted }}>
        这是 AI 影视创作导演工作台：资产入棚、布置场景、设计镜头，再生成画面和视频。不是 3D 建模软件。
      </Paragraph>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
        {STEPS.map((step) => (
          <div
            key={step.n}
            style={{
              padding: 12,
              borderRadius: 8,
              background: '#121222',
              border: `1px solid ${directorDark.border}`,
            }}
          >
            <Text style={{ color: directorDark.accent, fontSize: 12 }}>{step.n}</Text>
            <div style={{ color: directorDark.text, fontWeight: 600, marginTop: 4 }}>{step.t}</div>
            <div style={{ color: directorDark.muted, fontSize: 12, marginTop: 4 }}>{step.d}</div>
          </div>
        ))}
      </div>
    </Modal>
  );
}

export function onboardingKey(userId: string): string {
  return `vf_director_onboarded:${userId || 'anon'}`;
}

export function hasFinishedOnboarding(userId: string): boolean {
  if (!userId) return true;
  if (localStorage.getItem(onboardingKey(userId))) return true;
  if (localStorage.getItem('vf_director_onboarded')) return true;
  if (localStorage.getItem(onboardingKey('')) || localStorage.getItem(onboardingKey('anon'))) {
    localStorage.setItem(onboardingKey(userId), '1');
    return true;
  }
  return false;
}

export function markOnboardingDone(userId: string): void {
  if (userId) localStorage.setItem(onboardingKey(userId), '1');
  localStorage.setItem('vf_director_onboarded', '1');
}
