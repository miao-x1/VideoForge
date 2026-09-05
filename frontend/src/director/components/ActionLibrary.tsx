import { message } from 'antd';
import { cinema } from '../../theme';
import { ACTION_GROUPS, DIRECTOR_ACTIONS } from '../directing/actions';
import { useDirectorStore } from '../store/useDirectorStore';

export default function ActionLibrary() {
  const applyAction = useDirectorStore((s) => s.applyAction);
  const selectedId = useDirectorStore((s) => s.selectedId);
  const objects = useDirectorStore((s) => s.objects);
  const selected = objects.find((o) => o.id === selectedId && o.characterId);

  return (
    <div style={{ padding: 10 }}>
      <div style={{ color: cinema.muted, fontSize: 12, marginBottom: 10 }}>
        {selected ? `应用到 ${selected.name}` : '先点选角色，再点动作。未选中时应用到第一个角色。'}
      </div>
      {ACTION_GROUPS.map((group) => (
        <div key={group.key} style={{ marginBottom: 14 }}>
          <div style={{ color: cinema.gold, fontSize: 11, letterSpacing: 1, marginBottom: 6 }}>{group.label}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {DIRECTOR_ACTIONS.filter((a) => a.group === group.key).map((action) => (
              <button
                key={action.id}
                type="button"
                onClick={() => {
                  applyAction(action.id, selected?.id);
                  message.success(`已应用「${action.label}」`);
                }}
                style={{
                  textAlign: 'left',
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: `1px solid ${cinema.line}`,
                  background: cinema.raised,
                  color: cinema.text,
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600 }}>{action.label}</div>
                {action.note && <div style={{ fontSize: 10, color: cinema.muted, marginTop: 2 }}>{action.note}</div>}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
