export const SCENE_PRESETS: Array<{
  id: string;
  name: string;
  items: Array<{ id: string; position: [number, number, number] }>;
}> = [
  {
    id: 'room',
    name: '房间',
    items: [
      { id: 'floor', position: [0, 0, 0] },
      { id: 'wall', position: [0, 0, -1.52] },
      { id: 'door', position: [-1.05, 0, -1.48] },
      { id: 'window', position: [1.05, 0, -1.48] },
      { id: 'table', position: [0, 0, 0.15] },
      { id: 'chair', position: [0, 0, 0.85] },
    ],
  },
  {
    id: 'office',
    name: '办公室',
    items: [
      { id: 'floor', position: [0, 0, 0] },
      { id: 'desk', position: [0, 0, 0.1] },
      { id: 'chair', position: [0, 0, 0.95] },
      { id: 'bookshelf', position: [-1.25, 0, -1.2] },
      { id: 'lamp', position: [1.15, 0, 0.55] },
    ],
  },
  {
    id: 'street',
    name: '街道',
    items: [
      { id: 'road', position: [0, 0, 0] },
      { id: 'streetlamp', position: [-1.6, 0, 0.2] },
      { id: 'fence', position: [1.6, 0, 0] },
    ],
  },
  {
    id: 'forest',
    name: '森林',
    items: [
      { id: 'tree', position: [-1.2, 0, -0.6] },
      { id: 'pine', position: [1.1, 0, -0.8] },
      { id: 'bush', position: [0.2, 0, 0.7] },
      { id: 'rock', position: [-0.6, 0, 0.9] },
      { id: 'grass', position: [0.8, 0, 0.4] },
    ],
  },
  {
    id: 'stage',
    name: '舞台',
    items: [
      { id: 'stage', position: [0, 0, 0] },
      { id: 'platform', position: [0, 0, 1.1] },
      { id: 'column', position: [-1.4, 0, -0.4] },
    ],
  },
];
