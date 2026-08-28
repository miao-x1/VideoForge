import { useCallback, useRef, useState } from 'react';
import { Col, Layout, Row, Typography, message } from 'antd';
import InputPanel, { InputPanelValue } from './components/InputPanel';
import ProgressTimeline from './components/ProgressTimeline';
import VideoResult from './components/VideoResult';
import { api, subscribeTask, type ResultResp, type TaskStatus } from './api/client';

const { Header, Content } = Layout;
const { Title: PageTitle, Paragraph } = Typography;

export default function App() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResultResp | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const handleSubmit = useCallback(async (value: InputPanelValue) => {
    setLoading(true);
    setStatus('PENDING');
    setError(null);
    setResult(null);
    try {
      const brief = await api.createTask(value);
      // 订阅 SSE
      esRef.current?.close();
      esRef.current = subscribeTask(
        brief.task_id,
        async (data) => {
          setStatus(data.status);
          setError(data.error);
          if (data.status === 'COMPLETED') {
            const r = await api.getResult(brief.task_id);
            setResult(r);
            setLoading(false);
          } else if (data.status === 'FAILED') {
            setLoading(false);
            message.error('视频生成失败');
          }
        },
        () => {
          setLoading(false);
          message.error('实时连接中断');
        },
      );
    } catch (e: any) {
      setLoading(false);
      message.error('创建任务失败: ' + (e?.message || ''));
    }
  }, []);

  const showProgress = status !== null;
  const currentStatus: TaskStatus = status || 'PENDING';

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Header style={{ background: '#fff', padding: '0 24px' }}>
        <PageTitle level={3} style={{ margin: '14px 0' }}>
          AI 视频生成 Agent
        </PageTitle>
      </Header>
      <Content style={{ padding: 24 }}>
        <Row gutter={24}>
          <Col xs={24} md={10}>
            <div style={{ background: '#fff', padding: 24, borderRadius: 8 }}>
              <InputPanel loading={loading} onSubmit={handleSubmit} />
            </div>
          </Col>
          <Col xs={24} md={14}>
            <Row gutter={[0, 24]}>
              <Col span={24}>
                <div style={{ background: '#fff', padding: 24, borderRadius: 8, minHeight: 120 }}>
                  <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                    执行过程
                  </Paragraph>
                  {showProgress ? (
                    <ProgressTimeline status={currentStatus} error={error} />
                  ) : (
                    <Paragraph type="secondary">提交创意后将展示 Agent 执行进度</Paragraph>
                  )}
                </div>
              </Col>
              <Col span={24}>
                <VideoResult result={result} />
              </Col>
            </Row>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
}
