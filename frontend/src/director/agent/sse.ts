export interface AgentChatResponse {
  success: boolean;
  plan: Record<string, unknown> | null;
  actions: Array<{ type?: string; tool?: string; note?: string; arguments?: Record<string, unknown> }>;
  tool_results: Array<{ name?: string; success?: boolean; message?: string; generation_id?: string }>;
  generation_id: string | null;
  message: string;
  requires_confirmation?: boolean;
  thinking?: string[];
  error_code?: string | null;
  conversation_id?: string;
  message_id?: string;
  agent_run_id?: string;
}

export async function runAgentChat(payload: {
  message: string;
  conversation_id: string;
  context: unknown;
  confirm?: boolean;
  project_id?: string;
}): Promise<AgentChatResponse> {
  const token = localStorage.getItem('vf_token');
  const { withDirectorProject, getDirectorProjectId } = await import('../scope');
  const res = await fetch(withDirectorProject('/api/agent/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      ...payload,
      project_id: payload.project_id || getDirectorProjectId(),
      stream: false,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = typeof data?.message === 'string' ? data.message : `Agent API ${res.status}`;
    const error = new Error(err) as Error & { payload?: AgentChatResponse };
    error.payload = data;
    throw error;
  }
  return data as AgentChatResponse;
}

export type AgentSseEvent =
  | { event: 'run'; data: { conversation_id: string; message_id: string; agent_run_id: string } }
  | { event: 'thinking'; data: { text: string } }
  | { event: 'tool_call'; data: { name: string; arguments: Record<string, unknown>; note?: string; confirm?: boolean } }
  | { event: 'error'; data: { message: string; suggestion?: string } }
  | { event: 'complete'; data: { ok: boolean; planned?: number } };

export async function streamAgentChat(
  payload: { message: string; conversation_id: string; context: unknown; confirm?: boolean },
  onEvent: (ev: AgentSseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('vf_token');
  const { withDirectorProject } = await import('../scope');
  const res = await fetch(withDirectorProject('/api/agent/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Agent API ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split('\n\n');
    buf = chunks.pop() ?? '';
    for (const chunk of chunks) {
      const ev = parseSse(chunk);
      if (ev) onEvent(ev);
    }
  }
  if (buf.trim()) {
    const ev = parseSse(buf);
    if (ev) onEvent(ev);
  }
}

function parseSse(chunk: string): AgentSseEvent | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of chunk.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) } as AgentSseEvent;
  } catch {
    return null;
  }
}

export async function logAgentExecution(body: {
  conversation_id: string;
  message_id: string;
  agent_run_id: string;
  user_input: string;
  context?: unknown;
  tool_name: string;
  tool_arguments?: Record<string, unknown>;
  tool_result?: Record<string, unknown>;
  execution_status: string;
  error?: string | null;
}): Promise<void> {
  try {
    const token = localStorage.getItem('vf_token');
    const { withDirectorProject } = await import('../scope');
    await fetch(withDirectorProject('/api/agent/log'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch {
    /* 日志失败不影响导演台 */
  }
}
