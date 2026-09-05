import { Radio } from 'antd';
import { useDirectorStore } from '../store/useDirectorStore';
import type { TransformMode } from '../types';

export default function ViewportToolbar() {
  const transformMode = useDirectorStore((s) => s.transformMode);
  const setTransformMode = useDirectorStore((s) => s.setTransformMode);

  return (
    <div
      style={{
        position: 'absolute',
        left: 12,
        bottom: 12,
        zIndex: 3,
        display: 'flex',
        gap: 8,
      }}
    >
      <Radio.Group
        size="small"
        value={transformMode}
        onChange={(e) => setTransformMode(e.target.value as TransformMode)}
      >
        <Radio.Button value="translate">移动</Radio.Button>
        <Radio.Button value="rotate">旋转</Radio.Button>
        <Radio.Button value="scale">缩放</Radio.Button>
      </Radio.Group>
    </div>
  );
}
