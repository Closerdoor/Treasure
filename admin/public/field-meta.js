export const WORK_FIELD_META = {
  module: {
    label: '模块',
    front: '前台频道归属',
    note: '决定作品进入影视、书籍等一级入口。'
  },
  submodule: {
    label: '子模块',
    front: '前台详情路由',
    note: '电影当前使用 movie，会导出到 /video/movie/{id}。'
  },
  schema_type: {
    label: '内容类型',
    front: '详情页结构类型',
    note: '用于区分真人电影、动画、剧集等不同展示结构。'
  },
  title: {
    label: '中文标题',
    front: '详情页主标题',
    note: '前台卡片、列表、详情页首屏都会优先展示。'
  },
  title_original: {
    label: '原始标题',
    front: '副标题 / 原名',
    note: '展示原语言片名或官方外文名。'
  },
  year: {
    label: '年份',
    front: '作品年代',
    note: '用于列表筛选、卡片信息和详情基础信息。'
  },
  country: {
    label: '国家 / 地区',
    front: '产地信息',
    note: '前台用于基础信息和列表摘要。'
  },
  language: {
    label: '语言',
    front: '对白语言',
    note: '详情页基础信息字段。'
  },
  total_time: {
    label: '片长',
    front: '运行时间',
    note: '电影详情页会以分钟展示。'
  },
  studio: {
    label: '制片方',
    front: '出品 / 制作信息',
    note: '对应 generated 中的 publishCompany。'
  },
  status: {
    label: '状态',
    front: '发布状态',
    note: 'published 会进入当前前台导出范围。'
  },
  introduction: {
    label: '短简介',
    front: '列表摘要 / 详情简介',
    note: '用于首页、列表卡片和详情顶部简介。'
  },
  story: {
    label: '剧情长文',
    front: '详情介绍',
    note: '用于详情页更完整的剧情或作品介绍区域。'
  },
  scores: {
    label: '评分',
    front: '评分区 / 综合评分',
    note: '保存豆瓣、IMDb、TMDB、烂番茄等评分来源。'
  },
  images: {
    label: '图片资源',
    front: '海报 / 剧照 / 壁纸',
    note: '主海报、图库和详情页视觉资源都来自这里。'
  },
  external_source: {
    label: '外部来源',
    front: '外部链接 / 平台 ID',
    note: '用于保存豆瓣、IMDb、TMDB 等来源 ID 和链接。'
  },
  release_dates: {
    label: '上映日期',
    front: '上映信息',
    note: '详情页基础信息字段，可保留多地区日期。'
  },
  videos: {
    label: '视频',
    front: '预告片 / 视频区',
    note: '保存视频名称、封面、链接和时长。'
  },
  comments: {
    label: '评论影评',
    front: '精选评论 / 影评区',
    note: '保存短评、影评和来源排序信息。'
  },
  related: {
    label: '关联作品',
    front: '系列 / 相似推荐',
    note: '保存系列作品、相似作品或推荐作品。'
  },
  quotes: {
    label: '台词名言',
    front: '名言区',
    note: '详情页可展示精选台词或摘录。'
  },
  other_titles: {
    label: '其他译名',
    front: '别名',
    note: '用于详情页展示 AKA 信息。'
  },
  soundtrack: {
    label: '原声',
    front: '音乐区',
    note: '保存原声带或相关音乐信息。'
  },
  characters: {
    label: '角色信息',
    front: '角色区',
    note: '保存角色补充资料，后续可与演职员关系联动。'
  }
};
