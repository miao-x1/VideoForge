import { create } from 'zustand';
import { useDirectorStore } from '../store/useDirectorStore';
import { buildDirectorContext, type AgentFocus } from './context';
import { logAgentExecution, runAgentChat, type AgentChatResponse } from './sse';
import type { SceneBook } from '../persist';

export type StepStatus = 'running' | 'ok' | 'error' | 'confirm';

export interface AgentStep {
  id: string;
  kind: 'thinking' | 'tool' | 'result' | 'error';
  text: string;
  tool?: string;
  status?: StepStatus;
  prompt?: string;
}

export interface AgentMessage {
  id: string;
  role: 'user' | 'agent';
  text: string;
  steps: AgentStep[];
  createdAt: number;
  attachments?: string[];
}

export interface AgentSendExtras {
  attachments?: string[];
  duration?: number;
  aspectRatio?: string;
}

interface AgentOp {
  before: SceneBook;
  after: SceneBook;
}

interface AgentStore {
  conversationId: string;
  messages: AgentMessage[];
  running: boolean;
  focus: AgentFocus;
  lastCreatedCharacterId: string | null;
  pendingConfirm: { name: string; arguments: Record<string, unknown>; note?: string; rest: Array<{ name: string; arguments: Record<string, unknown>; note?: string; confirm?: boolean }> } | null;
  opsPast: AgentOp[];
  opsFuture: AgentOp[];
  send: (text: string, confirm?: boolean, extras?: AgentSendExtras) => Promise<void>;
  confirmPending: (yes: boolean) => Promise<void>;
  setFocus: (patch: Partial<AgentFocus>) => void;
}

function newId() {
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

async function applyAgentResponse(
  messageId: string,
  userText: string,
  data: AgentChatResponse,
  get: () => AgentStore,
  set: (patch: Partial<AgentStore>) => void,
  appendStep: (messageId: string, step: AgentStep) => void,
) {
  if (data.conversation_id) {
    set({ conversationId: data.conversation_id });
  }
  for (const line of data.thinking || []) {
    appendStep(messageId, { id: newId(), kind: 'thinking', status: 'ok', text: `✓ ${line}` });
  }
  for (const action of data.actions || []) {
    const result = (data.tool_results || []).find((r) => r.name === action.tool);
    const running = !result && !data.requires_confirmation;
    appendStep(messageId, {
      id: newId(),
      kind: 'tool',
      tool: action.tool,
      status: result?.success === false ? 'error' : running ? 'running' : 'ok',
      text: result?.success === false
        ? `执行失败：${result.message || action.note || action.tool}`
        : `${result ? '✓' : '⏳'} ${result?.message || action.note || action.tool}`,
    });
  }
  if (data.generation_id) {
    appendStep(messageId, {
      id: newId(),
      kind: 'result',
      status: 'ok',
      text: `✓ 生成 ${data.generation_id}`,
    });
  }
  if (data.requires_confirmation) {
    const first = (data.actions || []).find((a) => a.tool) || { tool: 'confirm', arguments: {}, note: data.message };
    set({
      pendingConfirm: {
        name: String(first.tool || 'confirm'),
        arguments: first.arguments || {},
        note: data.message,
        rest: [],
      },
      running: false,
    });
    appendStep(messageId, {
      id: newId(),
      kind: 'error',
      status: 'confirm',
      text: data.message || '该操作需要确认后才能执行。',
      tool: first.tool,
    });
    return;
  }
  if (data.message) {
    appendStep(messageId, {
      id: newId(),
      kind: data.error_code ? 'error' : 'result',
      status: data.error_code ? 'error' : 'ok',
      text: data.error_code ? data.message : `✓ ${data.message}`,
    });
  }
  try {
    const { fetchRemoteSceneBook } = await import('../sync');
    const book = await fetchRemoteSceneBook();
    if (book?.scenes.length) {
      useDirectorStore.getState().loadBook(book, { record: false });
    }
  } catch {
    /* 刷新失败不影响对话 */
  }
  await logAgentExecution({
    conversation_id: data.conversation_id || get().conversationId,
    message_id: data.message_id || messageId,
    agent_run_id: data.agent_run_id || newId(),
    user_input: userText,
    tool_name: 'plan',
    tool_result: { generation_id: data.generation_id, success: data.success },
    execution_status: data.success ? 'ok' : 'error',
    error: data.error_code || null,
  });
  set({ running: false, pendingConfirm: null });
}

export const useAgentStore = create<AgentStore>((set, get) => {
  const appendStep = (messageId: string, step: AgentStep) => {
    set((s) => ({
      messages: s.messages.map((m) => (m.id === messageId ? { ...m, steps: [...m.steps, step] } : m)),
    }));
  };

  return {
    conversationId: `conv_${newId()}`,
    messages: [],
    running: false,
    focus: { character_id: null, object_id: null, camera_id: null, shot_id: null },
    lastCreatedCharacterId: null,
    pendingConfirm: null,
    opsPast: [],
    opsFuture: [],

    setFocus: (patch) => set((s) => ({ focus: { ...s.focus, ...patch } })),

    send: async (text, confirm = false, extras) => {
      const trimmed = text.trim();
      if (!trimmed || (get().running && !confirm)) return;
      try {
        const { flushSceneBookNow } = await import('../syncSchedule');
        await flushSceneBookNow();
      } catch {
        /* 后端仍会用本次 context 兜底建分镜 */
      }
      if (extras?.duration || extras?.aspectRatio) {
        useDirectorStore.getState().updateShotMeta({
          shotDuration: extras.duration ?? useDirectorStore.getState().shotDuration,
        });
        if (extras.aspectRatio) {
          useDirectorStore.getState().setAspectRatio(extras.aspectRatio as '9:16' | '16:9' | '1:1');
        }
      }
      const userId = newId();
      const agentId = newId();
      if (!confirm) {
        set((s) => ({
          running: true,
          pendingConfirm: null,
          messages: [
            ...s.messages,
            { id: userId, role: 'user', text: trimmed, steps: [], createdAt: Date.now(), attachments: extras?.attachments },
            { id: agentId, role: 'agent', text: '', steps: [], createdAt: Date.now() },
          ],
        }));
      } else {
        const agent = [...get().messages].reverse().find((m) => m.role === 'agent');
        set({ running: true, pendingConfirm: null });
        if (agent) {
          appendStep(agent.id, { id: newId(), kind: 'thinking', text: '已确认，开始执行' });
        }
      }

      const targetId = confirm
        ? ([...get().messages].reverse().find((m) => m.role === 'agent')?.id || agentId)
        : agentId;
      const ctx = {
        ...buildDirectorContext(get().focus),
        attachment_urls: extras?.attachments || [],
        gen_duration: extras?.duration ?? useDirectorStore.getState().shotDuration,
        aspect_ratio: extras?.aspectRatio || useDirectorStore.getState().aspectRatio,
        user_message: trimmed,
      };

      try {
        const data = await runAgentChat({
          message: trimmed,
          conversation_id: get().conversationId,
          context: ctx,
          confirm,
        });
        await applyAgentResponse(targetId, trimmed, data, get, set, appendStep);
      } catch (err) {
        const payload = (err as Error & { payload?: AgentChatResponse }).payload;
        appendStep(targetId, {
          id: newId(),
          kind: 'error',
          status: 'error',
          text: payload?.message || (err instanceof Error ? err.message : String(err)),
        });
        set({ running: false });
      }
    },

    confirmPending: async (yes) => {
      const pending = get().pendingConfirm;
      if (!pending) return;
      const agent = [...get().messages].reverse().find((m) => m.role === 'agent');
      const user = [...get().messages].reverse().find((m) => m.role === 'user');
      if (!yes) {
        if (agent) {
          appendStep(agent.id, { id: newId(), kind: 'result', text: '已取消高风险操作' });
        }
        set({ pendingConfirm: null, running: false });
        return;
      }
      await get().send(user?.text || pending.note || '', true);
    },
  };
});
