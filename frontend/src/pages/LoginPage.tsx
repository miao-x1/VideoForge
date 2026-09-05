import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Checkbox, Form, Input, Modal, Tabs, Typography, message,
} from 'antd';
import {
  LockOutlined, MailOutlined, MobileOutlined, SafetyOutlined, UserOutlined,
} from '@ant-design/icons';
import { authApi } from '../api/client';
import { useAuth } from '../hooks/useAuth';

const { Title, Paragraph, Link } = Typography;

type View = 'login' | 'register' | 'forgot';
type LoginMode = 'password' | 'sms';

function authErrorMessage(e: any, fallback: string): string {
  if (!e?.response) return '后端未连接，请先启动 backend（端口 8000）后再试';
  const detail = e.response.data?.detail;
  if (e.response.status === 409) {
    return typeof detail === 'string' ? `${detail}` : '该账号已注册，请直接登录或找回密码';
  }
  return typeof detail === 'string' ? detail : fallback;
}

function CaptchaRow({
  image,
  onRefresh,
}: {
  image: string;
  onRefresh: () => void;
}) {
  return (
    <div
      onClick={onRefresh}
      title="点击刷新"
      className="auth-captcha"
    >
      {image ? (
        <img src={image} alt="图形验证码" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : (
        <div style={{ textAlign: 'center', lineHeight: '40px', color: '#999', fontSize: 12 }}>加载中</div>
      )}
    </div>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { applyAuth } = useAuth();
  const [view, setView] = useState<View>('login');
  const [loginMode, setLoginMode] = useState<LoginMode>('password');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [captchaId, setCaptchaId] = useState('');
  const [captchaImage, setCaptchaImage] = useState('');
  const [termsOpen, setTermsOpen] = useState(false);
  const [codeChannel, setCodeChannel] = useState(false);
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();
  const [forgotForm] = Form.useForm();

  const refreshCaptcha = useCallback(async () => {
    try {
      const data = await authApi.captcha();
      setCaptchaId(data.captcha_id);
      setCaptchaImage(data.image);
    } catch {
      message.error('图形验证码加载失败，请确认后端已启动');
    }
  }, []);

  useEffect(() => {
    refreshCaptcha();
  }, [refreshCaptcha, view, loginMode]);

  useEffect(() => {
    authApi.status()
      .then((s) => setCodeChannel(s.sms_configured || s.email_configured))
      .catch(() => setCodeChannel(false));
  }, []);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = window.setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => window.clearTimeout(t);
  }, [countdown]);

  const sendCode = async (form: ReturnType<typeof Form.useForm>[0], purpose: 'register' | 'login' | 'reset') => {
    try {
      const account = form.getFieldValue('account');
      const captcha_code = form.getFieldValue('captcha_code');
      if (!account) {
        message.warning('请先填写手机号或邮箱');
        return;
      }
      if (!captcha_code) {
        message.warning('请先填写图形验证码');
        return;
      }
      setSending(true);
      const resp = await authApi.sendCode({
        account,
        purpose,
        captcha_id: captchaId,
        captcha_code,
      });
      message.success(resp.message);
      if (resp.dev_code) {
        form.setFieldValue('verify_code', resp.dev_code);
      }
      setCountdown(resp.cooldown || 60);
      await refreshCaptcha();
      form.setFieldValue('captcha_code', '');
    } catch (e: any) {
      message.error(authErrorMessage(e, '验证码发送失败'));
      await refreshCaptcha();
    } finally {
      setSending(false);
    }
  };

  const onPasswordLogin = async (values: any) => {
    setLoading(true);
    try {
      const resp = await authApi.login({
        account: values.account,
        password: values.password,
        captcha_id: captchaId,
        captcha_code: values.captcha_code,
        remember: !!values.remember,
      });
      applyAuth(resp);
      message.success('登录成功');
      navigate('/director');
    } catch (e: any) {
      message.error(authErrorMessage(e, '登录失败'));
      await refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const onSmsLogin = async (values: any) => {
    setLoading(true);
    try {
      const resp = await authApi.loginSms({
        account: values.account,
        verify_code: values.verify_code,
        captcha_id: captchaId,
        captcha_code: values.captcha_code,
        remember: !!values.remember,
      });
      applyAuth(resp);
      message.success('登录成功');
      navigate('/director');
    } catch (e: any) {
      message.error(authErrorMessage(e, '登录失败'));
      await refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const onRegister = async (values: any) => {
    setLoading(true);
    try {
      const resp = await authApi.register({
        account: values.account,
        password: values.password,
        display_name: values.display_name || '',
        captcha_id: captchaId,
        captcha_code: values.captcha_code,
        verify_code: values.verify_code || '',
        agree: !!values.agree,
      });
      applyAuth(resp);
      message.success('注册成功');
      navigate('/director');
    } catch (e: any) {
      message.error(authErrorMessage(e, '注册失败'));
      await refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const onReset = async (values: any) => {
    setLoading(true);
    try {
      const resp = await authApi.resetPassword({
        account: values.account,
        verify_code: values.verify_code,
        password: values.password,
      });
      message.success(resp.message);
      setView('login');
      setLoginMode('password');
    } catch (e: any) {
      message.error(authErrorMessage(e, '重置失败'));
      await refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const accountRules = [
    { required: true, message: '请输入手机号或邮箱' },
    {
      validator: (_: unknown, value: string) => {
        const v = (value || '').trim();
        if (!v) return Promise.resolve();
        const phone = /^1[3-9]\d{9}$/.test(v);
        const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
        return phone || email ? Promise.resolve() : Promise.reject(new Error('请输入有效手机号或邮箱'));
      },
    },
  ];

  const codeButton = (form: ReturnType<typeof Form.useForm>[0], purpose: 'register' | 'login' | 'reset') => (
    <Button disabled={countdown > 0} loading={sending} onClick={() => sendCode(form, purpose)}>
      {countdown > 0 ? `${countdown}s` : '获取验证码'}
    </Button>
  );

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-mark">
          <div className="word">VIDEOFORGE</div>
          <div className="line" />
          <div className="sub">AI 影视创作工作台</div>
        </div>

        {view !== 'forgot' && (
          <Tabs
            centered
            activeKey={view}
            onChange={(k) => setView(k as View)}
            items={[
              { key: 'login', label: '登录' },
              { key: 'register', label: '注册' },
            ]}
          />
        )}

        {view === 'login' && (
          <>
            {codeChannel && (
            <Tabs
              size="small"
              activeKey={loginMode}
              onChange={(k) => setLoginMode(k as LoginMode)}
              items={[
                { key: 'password', label: '密码登录' },
                { key: 'sms', label: '验证码登录' },
              ]}
            />
            )}
            {loginMode === 'password' || !codeChannel ? (
              <Form form={loginForm} onFinish={onPasswordLogin} layout="vertical">
                <Form.Item name="account" rules={accountRules}>
                  <Input prefix={<UserOutlined />} placeholder="手机号或邮箱" size="large" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
                </Form.Item>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Form.Item name="captcha_code" rules={[{ required: true, message: '请输入图形验证码' }]} style={{ flex: 1, marginBottom: 24 }}>
                    <Input prefix={<SafetyOutlined />} placeholder="图形验证码" size="large" />
                  </Form.Item>
                  <CaptchaRow image={captchaImage} onRefresh={refreshCaptcha} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                  <Form.Item name="remember" valuePropName="checked" noStyle>
                    <Checkbox>记住登录</Checkbox>
                  </Form.Item>
                  <Button type="link" style={{ padding: 0, height: 'auto' }} onClick={() => setView('forgot')}>忘记密码？</Button>
                </div>
                <Button type="primary" htmlType="submit" loading={loading} block size="large">登录</Button>
              </Form>
            ) : (
              <Form form={loginForm} onFinish={onSmsLogin} layout="vertical">
                <Form.Item name="account" rules={accountRules}>
                  <Input prefix={<MobileOutlined />} placeholder="手机号或邮箱" size="large" />
                </Form.Item>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Form.Item name="captcha_code" rules={[{ required: true, message: '请输入图形验证码' }]} style={{ flex: 1, marginBottom: 24 }}>
                    <Input prefix={<SafetyOutlined />} placeholder="图形验证码" size="large" />
                  </Form.Item>
                  <CaptchaRow image={captchaImage} onRefresh={refreshCaptcha} />
                </div>
                <Form.Item name="verify_code" rules={[{ required: true, message: '请输入短信/邮箱验证码' }, { len: 6, message: '验证码为 6 位' }]}>
                  <Input
                    prefix={<MailOutlined />}
                    placeholder="6 位验证码"
                    size="large"
                    suffix={codeButton(loginForm, 'login')}
                  />
                </Form.Item>
                <Form.Item name="remember" valuePropName="checked">
                  <Checkbox>记住登录</Checkbox>
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block size="large">登录</Button>
              </Form>
            )}
          </>
        )}

        {view === 'register' && (
          <Form form={registerForm} onFinish={onRegister} layout="vertical">
            <Form.Item name="account" rules={accountRules}>
              <Input prefix={<UserOutlined />} placeholder="手机号或邮箱" size="large" />
            </Form.Item>
            <Form.Item name="display_name">
              <Input prefix={<UserOutlined />} placeholder="昵称（可选）" size="large" />
            </Form.Item>
            <div style={{ display: 'flex', gap: 8 }}>
              <Form.Item name="captcha_code" rules={[{ required: true, message: '请输入图形验证码' }]} style={{ flex: 1, marginBottom: 24 }}>
                <Input prefix={<SafetyOutlined />} placeholder="图形验证码" size="large" />
              </Form.Item>
              <CaptchaRow image={captchaImage} onRefresh={refreshCaptcha} />
            </div>
            {codeChannel && (
            <Form.Item name="verify_code" rules={[{ required: true, message: '请输入验证码' }, { len: 6, message: '验证码为 6 位' }]}>
              <Input
                prefix={<MailOutlined />}
                placeholder="短信 / 邮箱验证码"
                size="large"
                suffix={codeButton(registerForm, 'register')}
              />
            </Form.Item>
            )}
            <Form.Item name="password" rules={[{ required: true, message: '请设置密码' }, { min: 8, message: '密码至少 8 位' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="设置密码（至少 8 位）" size="large" />
            </Form.Item>
            <Form.Item
              name="confirm"
              dependencies={['password']}
              rules={[
                { required: true, message: '请再次输入密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) return Promise.resolve();
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="确认密码" size="large" />
            </Form.Item>
            <Form.Item
              name="agree"
              valuePropName="checked"
              rules={[{ validator: (_, v) => (v ? Promise.resolve() : Promise.reject(new Error('请先同意用户协议'))) }]}
            >
              <Checkbox>
                我已阅读并同意
                <Link onClick={(e) => { e.preventDefault(); setTermsOpen(true); }}>《用户协议》</Link>
                和
                <Link onClick={(e) => { e.preventDefault(); setTermsOpen(true); }}>《隐私政策》</Link>
              </Checkbox>
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">注册</Button>
          </Form>
        )}

        {view === 'forgot' && (
          <>
            <Title level={4} style={{ marginTop: 0 }}>找回密码</Title>
            <Paragraph type="secondary">用注册时的手机号或邮箱接收验证码，然后设置新密码。</Paragraph>
            <Form form={forgotForm} onFinish={onReset} layout="vertical">
              <Form.Item name="account" rules={accountRules}>
                <Input prefix={<UserOutlined />} placeholder="手机号或邮箱" size="large" />
              </Form.Item>
              <div style={{ display: 'flex', gap: 8 }}>
                <Form.Item name="captcha_code" rules={[{ required: true, message: '请输入图形验证码' }]} style={{ flex: 1, marginBottom: 24 }}>
                  <Input prefix={<SafetyOutlined />} placeholder="图形验证码" size="large" />
                </Form.Item>
                <CaptchaRow image={captchaImage} onRefresh={refreshCaptcha} />
              </div>
              <Form.Item name="verify_code" rules={[{ required: true, message: '请输入验证码' }, { len: 6, message: '验证码为 6 位' }]}>
                <Input
                  prefix={<MailOutlined />}
                  placeholder="6 位验证码"
                  size="large"
                  suffix={codeButton(forgotForm, 'reset')}
                />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请设置新密码' }, { min: 8, message: '新密码至少 8 位' }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="新密码（至少 8 位）" size="large" />
              </Form.Item>
              <Form.Item
                name="confirm"
                dependencies={['password']}
                rules={[
                  { required: true, message: '请再次输入新密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('password') === value) return Promise.resolve();
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="确认新密码" size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">重置密码</Button>
              <Button type="link" block style={{ marginTop: 8 }} onClick={() => setView('login')}>返回登录</Button>
            </Form>
          </>
        )}

        <span className="auth-foot">
          {codeChannel
            ? '点击图形验证码可刷新'
            : '当前未配置短信/邮箱，用密码注册和登录即可，账号会保存在本地数据库'}
        </span>
      </div>

      <Modal title="用户协议与隐私政策" open={termsOpen} onCancel={() => setTermsOpen(false)} footer={null}>
        <Paragraph>使用 VideoForge 即表示你同意：账号仅供本人使用，生成内容需遵守法律法规与平台规范，不上传违法或侵权素材。</Paragraph>
        <Paragraph>我们仅用账号信息完成登录、创作记录与作品存储。密码经哈希保存。短信/邮箱通道的密钥只存放在后端环境变量中。</Paragraph>
      </Modal>
    </div>
  );
}
