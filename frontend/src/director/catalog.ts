import type { SceneObjectType, ShapeKind, Vec3 } from './types';

export interface CatalogItem {
  id: string;
  category: SceneObjectType;
  name: string;
  shape: ShapeKind;
  color: string;
  scale?: Vec3;
  lightIntensity?: number;
}

export const CATALOG_GROUPS: Array<{ key: SceneObjectType; label: string }> = [
  { key: 'shape', label: '几何体' },
  { key: 'furniture', label: '家具' },
  { key: 'architecture', label: '建筑场景' },
  { key: 'nature', label: '自然' },
  { key: 'vehicle', label: '载具' },
  { key: 'prop', label: '道具' },
  { key: 'light', label: '灯光' },
  { key: 'effect', label: '标记 / 特效' },
];

export const CATALOG: CatalogItem[] = [
  { id: 'box', category: 'shape', name: '立方体', shape: 'box', color: '#69c0ff' },
  { id: 'roundedBox', category: 'shape', name: '圆角方块', shape: 'roundedBox', color: '#85a5ff' },
  { id: 'sphere', category: 'shape', name: '球体', shape: 'sphere', color: '#95de64' },
  { id: 'hemisphere', category: 'shape', name: '半球', shape: 'hemisphere', color: '#b7eb8f' },
  { id: 'cylinder', category: 'shape', name: '圆柱', shape: 'cylinder', color: '#ffc53d' },
  { id: 'cone', category: 'shape', name: '圆锥', shape: 'cone', color: '#ff7a45' },
  { id: 'capsule', category: 'shape', name: '胶囊', shape: 'capsule', color: '#b37feb' },
  { id: 'plane', category: 'shape', name: '平面', shape: 'plane', color: '#adc6ff' },
  { id: 'torus', category: 'shape', name: '圆环', shape: 'torus', color: '#ff85c0' },
  { id: 'tube', category: 'shape', name: '管道', shape: 'tube', color: '#ffadd2' },
  { id: 'pyramid', category: 'shape', name: '金字塔', shape: 'pyramid', color: '#ffc069' },
  { id: 'ring', category: 'shape', name: '圆盘', shape: 'ring', color: '#87e8de' },
  { id: 'star', category: 'shape', name: '星形', shape: 'star', color: '#ffec3d' },
  { id: 'arrow', category: 'shape', name: '箭头', shape: 'arrow', color: '#36cfc9' },
  { id: 'tetrahedron', category: 'shape', name: '四面体', shape: 'tetrahedron', color: '#ff9c6e' },
  { id: 'octahedron', category: 'shape', name: '八面体', shape: 'octahedron', color: '#85a5ff' },
  { id: 'dodecahedron', category: 'shape', name: '十二面体', shape: 'dodecahedron', color: '#b37feb' },
  { id: 'icosahedron', category: 'shape', name: '二十面体', shape: 'icosahedron', color: '#5cdbd3' },
  { id: 'torusKnot', category: 'shape', name: '纽结', shape: 'torusKnot', color: '#ff4d4f' },

  { id: 'table', category: 'furniture', name: '桌子', shape: 'table', color: '#a8071a' },
  { id: 'desk', category: 'furniture', name: '书桌', shape: 'desk', color: '#873800' },
  { id: 'chair', category: 'furniture', name: '椅子', shape: 'chair', color: '#ad4e00' },
  { id: 'stool', category: 'furniture', name: '凳子', shape: 'stool', color: '#d48806' },
  { id: 'bench', category: 'furniture', name: '长椅', shape: 'bench', color: '#614700' },
  { id: 'sofa', category: 'furniture', name: '沙发', shape: 'sofa', color: '#1d39c4' },
  { id: 'bed', category: 'furniture', name: '床', shape: 'bed', color: '#d6e4ff' },
  { id: 'bookshelf', category: 'furniture', name: '书架', shape: 'bookshelf', color: '#874d00' },
  { id: 'cabinet', category: 'furniture', name: '柜子', shape: 'cabinet', color: '#ad8b00' },
  { id: 'fridge', category: 'furniture', name: '冰箱', shape: 'fridge', color: '#f0f5ff' },
  { id: 'tvstand', category: 'furniture', name: '电视柜', shape: 'tvstand', color: '#262626' },
  { id: 'lamp', category: 'furniture', name: '落地灯', shape: 'lamp', color: '#fff1b8' },
  { id: 'plantpot', category: 'furniture', name: '盆栽', shape: 'plantpot', color: '#389e0d' },
  { id: 'mirror', category: 'furniture', name: '镜子', shape: 'mirror', color: '#91d5ff' },

  { id: 'wall', category: 'architecture', name: '墙', shape: 'wall', color: '#d9d9d9' },
  { id: 'floor', category: 'architecture', name: '地板', shape: 'floor', color: '#bfbfbf' },
  { id: 'roof', category: 'architecture', name: '屋顶', shape: 'roof', color: '#cf1322' },
  { id: 'door', category: 'architecture', name: '门', shape: 'door', color: '#874d00' },
  { id: 'window', category: 'architecture', name: '窗', shape: 'window', color: '#91d5ff' },
  { id: 'column', category: 'architecture', name: '柱子', shape: 'column', color: '#bfbfbf' },
  { id: 'arch', category: 'architecture', name: '拱门', shape: 'arch', color: '#8c8c8c' },
  { id: 'stairs', category: 'architecture', name: '楼梯', shape: 'stairs', color: '#8c8c8c' },
  { id: 'fence', category: 'architecture', name: '围栏', shape: 'fence', color: '#614700' },
  { id: 'house', category: 'architecture', name: '小屋', shape: 'house', color: '#faad14' },
  { id: 'road', category: 'architecture', name: '路面', shape: 'road', color: '#434343' },
  { id: 'streetlamp', category: 'architecture', name: '路灯', shape: 'streetlamp', color: '#fff1b8' },
  { id: 'stage', category: 'architecture', name: '舞台', shape: 'stage', color: '#722ed1' },
  { id: 'platform', category: 'architecture', name: '平台', shape: 'platform', color: '#8c8c8c' },
  { id: 'tent', category: 'architecture', name: '帐篷', shape: 'tent', color: '#13c2c2' },

  { id: 'tree', category: 'nature', name: '阔叶树', shape: 'tree', color: '#237804' },
  { id: 'pine', category: 'nature', name: '松树', shape: 'pine', color: '#135200' },
  { id: 'palm', category: 'nature', name: '棕榈', shape: 'palm', color: '#389e0d' },
  { id: 'cactus', category: 'nature', name: '仙人掌', shape: 'cactus', color: '#52c41a' },
  { id: 'bush', category: 'nature', name: '灌木', shape: 'bush', color: '#389e0d' },
  { id: 'grass', category: 'nature', name: '草丛', shape: 'grass', color: '#73d13d' },
  { id: 'rock', category: 'nature', name: '石头', shape: 'rock', color: '#8c8c8c' },
  { id: 'mountain', category: 'nature', name: '山体', shape: 'mountain', color: '#595959' },
  { id: 'water', category: 'nature', name: '水面', shape: 'water', color: '#1890ff' },
  { id: 'cloud', category: 'nature', name: '云', shape: 'cloud', color: '#f5f5f5' },
  { id: 'flower', category: 'nature', name: '花', shape: 'flower', color: '#eb2f96' },
  { id: 'mushroom', category: 'nature', name: '蘑菇', shape: 'mushroom', color: '#cf1322' },

  { id: 'car', category: 'vehicle', name: '汽车', shape: 'car', color: '#cf1322' },
  { id: 'truck', category: 'vehicle', name: '卡车', shape: 'truck', color: '#fa8c16' },
  { id: 'bus', category: 'vehicle', name: '巴士', shape: 'bus', color: '#1677ff' },
  { id: 'motorcycle', category: 'vehicle', name: '摩托', shape: 'motorcycle', color: '#262626' },
  { id: 'bike', category: 'vehicle', name: '自行车', shape: 'bike', color: '#096dd9' },
  { id: 'boat', category: 'vehicle', name: '小船', shape: 'boat', color: '#13c2c2' },
  { id: 'airplane', category: 'vehicle', name: '飞机', shape: 'airplane', color: '#d9d9d9' },

  { id: 'crate', category: 'prop', name: '木箱', shape: 'crate', color: '#ad6800' },
  { id: 'barrel', category: 'prop', name: '木桶', shape: 'barrel', color: '#874d00' },
  { id: 'bottle', category: 'prop', name: '瓶子', shape: 'bottle', color: '#36cfc9' },
  { id: 'book', category: 'prop', name: '书', shape: 'book', color: '#1d39c4' },
  { id: 'cup', category: 'prop', name: '杯子', shape: 'cup', color: '#fff2e8' },
  { id: 'plate', category: 'prop', name: '盘子', shape: 'plate', color: '#fff1f0' },
  { id: 'vase', category: 'prop', name: '花瓶', shape: 'vase', color: '#9254de' },
  { id: 'phone', category: 'prop', name: '手机', shape: 'phone', color: '#111111' },
  { id: 'laptop', category: 'prop', name: '笔记本', shape: 'laptop', color: '#434343' },
  { id: 'bag', category: 'prop', name: '背包', shape: 'bag', color: '#ad4e00' },
  { id: 'suitcase', category: 'prop', name: '行李箱', shape: 'suitcase', color: '#1d39c4' },
  { id: 'trash', category: 'prop', name: '垃圾桶', shape: 'trash', color: '#52c41a' },
  { id: 'sign', category: 'prop', name: '指示牌', shape: 'sign', color: '#fadb14' },
  { id: 'ball', category: 'prop', name: '球', shape: 'ball', color: '#ff4d4f' },
  { id: 'camera_prop', category: 'prop', name: '摄影机', shape: 'camera_prop', color: '#262626' },
  { id: 'umbrella', category: 'prop', name: '伞', shape: 'umbrella', color: '#eb2f96' },

  { id: 'light_point', category: 'light', name: '点光', shape: 'light_point', color: '#fff566', lightIntensity: 8 },
  { id: 'light_spot', category: 'light', name: '聚光', shape: 'light_spot', color: '#ffe58f', lightIntensity: 12 },
  { id: 'light_directional', category: 'light', name: '平行光', shape: 'light_directional', color: '#fffbe6', lightIntensity: 1.4 },
  { id: 'light_area', category: 'light', name: '面光', shape: 'light_area', color: '#fff1b8', lightIntensity: 6 },

  { id: 'marker', category: 'effect', name: '站位标记', shape: 'marker', color: '#ff4d4f' },
  { id: 'screen', category: 'effect', name: '屏幕 / 监视器', shape: 'screen', color: '#111111' },
  { id: 'flag', category: 'effect', name: '旗帜', shape: 'flag', color: '#cf1322' },
  { id: 'fire', category: 'effect', name: '火焰', shape: 'fire', color: '#fa541c' },
  { id: 'smoke', category: 'effect', name: '烟雾', shape: 'smoke', color: '#bfbfbf' },
  { id: 'hologram', category: 'effect', name: '全息', shape: 'hologram', color: '#13c2c2' },
];

export function getCatalogItem(id: string): CatalogItem | undefined {
  return CATALOG.find((item) => item.id === id);
}

export function catalogShapeOptions(): Array<{ value: ShapeKind; label: string }> {
  return CATALOG.map((item) => ({ value: item.shape, label: item.name }));
}
