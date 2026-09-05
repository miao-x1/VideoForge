import { useEffect, useState } from 'react';
import { Alert, Button, Checkbox, Divider, Drawer, Input, Radio, Select, Upload, message } from 'antd';
import { FolderOpenOutlined } from '@ant-design/icons';
import { cinema } from '../../theme';
import { billingApi, type BillingStatus } from '../../api/client';
import { useDirectorStore } from '../store/useDirectorStore';
import { loadScene } from '../sceneApi';
import type { AspectRatio } from '../types';

function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('读取失败'));
    reader.readAsText(file);
  });
}

function billingError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (err instanceof Error) return err.message;
  return '操作失败';
}

export default function SettingsDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const setAspectRatio = useDirectorStore((s) => s.setAspectRatio);
  const environment = useDirectorStore((s) => s.environment);
  const setEnvironment = useDirectorStore((s) => s.setEnvironment);
  const resetScene = useDirectorStore((s) => s.resetScene);

  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.minimax.cn');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (!localStorage.getItem('vf_token')) {
      setBilling(null);
      return;
    }
    billingApi.status().then((data) => {
      setBilling(data);
      const savedUrl = data.credentials.find((c) => c.provider === data.video_provider)?.base_url;
      if (savedUrl) setBaseUrl(savedUrl);
    }).catch(() => setBilling(null));
  }, [open]);

  const saved = billing?.credentials.find((c) => c.provider === (billing.video_provider || 'minimax'));

  const applyPrefs = async (patch: { video_source?: 'platform' | 'own'; video_provider?: string }) => {
    setBusy(true);
    try {
      setBilling(await billingApi.updatePrefs(patch));
    } catch (err) {
      message.error(billingError(err));
    } finally {
      setBusy(false);
    }
  };

  const saveKey = async () => {
    if (!billing) return;
    if (apiKey.trim().length < 8) {
      message.error('请粘贴完整 API Key');
      return;
    }
    setBusy(true);
    try {
      await billingApi.saveCredential({
        provider: billing.video_provider || 'minimax',
        api_key: apiKey.trim(),
        base_url: billing.video_provider === 'qwen' ? '' : baseUrl,
      });
      setApiKey('');
      setBilling(await billingApi.status());
      message.success('已保存，出片将走你自己的账户');
    } catch (err) {
      message.error(billingError(err));
    } finally {
      setBusy(false);
    }
  };

  const recharge = async (packageId: string) => {
    setBusy(true);
    try {
      setBilling(await billingApi.recharge({ package_id: packageId }));
      message.success('已写入本站测试账本，不会转到 MiniMax');
    } catch (err) {
      message.error(billingError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer title="摄影棚设置" open={open} onClose={onClose} width={400}>
      <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 8 }}>画幅</div>
      <Select
        style={{ width: '100%', marginBottom: 16 }}
        value={aspectRatio}
        options={[
          { value: '9:16', label: '9:16 竖屏短剧' },
          { value: '16:9', label: '16:9 横屏' },
          { value: '1:1', label: '1:1' },
        ]}
        onChange={(v) => setAspectRatio(v as AspectRatio)}
      />
      <Checkbox
        checked={environment.showGrid}
        onChange={(e) => setEnvironment({ showGrid: e.target.checked })}
      >
        显示地面网格
      </Checkbox>
      <div style={{ marginTop: 20 }}>
        <Upload
          accept="application/json"
          showUploadList={false}
          beforeUpload={async (file) => {
            try {
              loadScene(await readAsText(file));
              message.success('场景已加载');
            } catch (err: unknown) {
              message.error(err instanceof Error ? err.message : '加载失败');
            }
            return false;
          }}
        >
          <Button icon={<FolderOpenOutlined />}>加载场景 JSON</Button>
        </Upload>
      </div>
      <Button
        danger
        style={{ marginTop: 16 }}
        onClick={() => {
          resetScene();
          message.success('已清空当前镜头（角色资产仍保留）');
        }}
      >
        清空当前镜头
      </Button>

      <Divider style={{ borderColor: cinema.line, margin: '28px 0 16px' }} />
      <div style={{ color: cinema.text, fontSize: 14, marginBottom: 8 }}>模型与计费</div>
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 12 }}
        message="余额只记在 VideoForge 本站账本，不会打到 MiniMax。"
        description="没填自己的 Key 时，出片用的是服务器 .env 里运营方的 MINIMAX_API_KEY。本站先扣你的测试额度，再拿运营方 Key 去调 MiniMax。"
      />

      {billing ? (
        <>
          <Radio.Group
            value={billing.video_source}
            disabled={busy}
            onChange={(e) => applyPrefs({ video_source: e.target.value })}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}
          >
            <Radio value="platform">平台代付（用运营方 Key，扣本站余额）</Radio>
            <Radio value="own">自己的 API Key（走 MiniMax 账户，本站不扣费）</Radio>
          </Radio.Group>

          <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 8 }}>供应商</div>
          <Select
            style={{ width: '100%', marginBottom: 16 }}
            value={billing.video_provider}
            disabled={busy}
            options={billing.catalog.map((item) => ({
              value: item.provider,
              label: `${item.label}${item.available || billing.video_source === 'own' ? '' : '（平台未配置）'}`,
            }))}
            onChange={(v) => applyPrefs({ video_provider: v })}
          />

          {billing.video_source === 'platform' ? (
            <>
              <div style={{ color: cinema.text, fontSize: 22, marginBottom: 4 }}>
                ¥{billing.wallet.balance_yuan}
              </div>
              <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 12, lineHeight: 1.6 }}>
                本站账本 · 约 {billing.price_fen_per_sec / 100} 元/秒
                {billing.platform_ready ? ' · 运营方 MiniMax 已配置' : ' · 运营方 MiniMax Key 未配置，平台模式无法出片'}
              </div>
              {billing.dev_recharge ? (
                <>
                  <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 8 }}>
                    开发环境可领取测试额度，只写入本地 user_wallets，不是微信支付，也不会充进 MiniMax。
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                    {billing.packages.map((pack) => (
                      <Button key={pack.id} size="small" loading={busy} onClick={() => recharge(pack.id)}>
                        领取 {pack.label} 测试额度
                      </Button>
                    ))}
                  </div>
                </>
              ) : (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 8 }}
                  message="正式收款还没接。生产环境请用自己的 MiniMax Key，或等微信支付接入后再走平台代付。"
                />
              )}
            </>
          ) : (
            <>
              {billing.video_provider === 'minimax' && (
                <>
                  <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 8 }}>MiniMax 站点</div>
                  <Select
                    style={{ width: '100%', marginBottom: 12 }}
                    value={baseUrl}
                    options={[
                      { value: 'https://api.minimax.cn', label: '国内站 api.minimax.cn' },
                      { value: 'https://api.minimax.io', label: '国际站 api.minimax.io' },
                    ]}
                    onChange={setBaseUrl}
                  />
                </>
              )}
              <Input.Password
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={saved ? `已保存，尾号 ${saved.last4}，可覆盖` : '粘贴 API Key，只保存在你的账户'}
                style={{ marginBottom: 8 }}
              />
              <Button type="primary" loading={busy} onClick={saveKey} block>
                保存 Key
              </Button>
              {!saved && (
                <div style={{ color: cinema.muted, fontSize: 12, marginTop: 8 }}>
                  未保存 Key 时无法出片。
                </div>
              )}
              {saved && (
                <Button
                  type="link"
                  danger
                  style={{ paddingLeft: 0, marginTop: 4 }}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await billingApi.deleteCredential(billing.video_provider);
                      setBilling(await billingApi.status());
                      message.success('已删除');
                    } catch (err) {
                      message.error(billingError(err));
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  删除已保存的 Key
                </Button>
              )}
            </>
          )}
        </>
      ) : (
        <div style={{ color: cinema.muted, fontSize: 12 }}>登录后可设置出片通道</div>
      )}
    </Drawer>
  );
}
