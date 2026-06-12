import fs from "node:fs";
import path from "node:path";

const root = path.resolve("F:/MyProject/Treasure/temp-script/book-ingest");
const dataDir = path.join(root, "data");
const stagingDir = path.join(dataDir, "staging");
const rawDir = path.join(dataDir, "raw");
const manifestDir = path.join(dataDir, "batch-manifests");

const runId = "2026-06-11-web-novel-blocked-manual-fallback";

const records = [
  {
    id: "0200000041",
    title: "雪中悍刀行",
    author: "烽火戏诸侯",
    year: 2011,
    wordCount: 4600000,
    tags: ["武侠", "玄幻", "江湖"],
    genres: ["网络小说", "武侠幻想"],
    summary: "一部兼具庙堂权谋与江湖气象的长篇网络小说。故事以北凉世子徐凤年为中心，展开关于家国、江湖、亲情、师友与个人成长的群像叙事。",
    story: "徐凤年从纨绔世子逐步走向承担北凉命运的位置，在游历江湖、卷入朝堂纷争和面对天下格局变化的过程中，完成从个人逍遥到家国担当的转变。",
    sources: [
      ["QQ阅读", "QQ阅读", "https://ubook.reader.qq.com/book-detail/172865"],
      ["中国作家网", "中国作家网", "https://www.chinawriter.com.cn/n1/2022/0125/c404027-32339304.html"]
    ]
  },
  {
    id: "0200000042",
    title: "新宋",
    author: "阿越",
    year: 2004,
    tags: ["历史", "架空历史", "穿越"],
    genres: ["网络小说", "历史小说"],
    summary: "架空历史小说。现代人石越来到北宋神宗年间，以知识、制度与政治经验介入王安石变法前后的时代浪潮，重新想象宋代政治、经济与社会演变。",
    story: "主人公石越进入北宋政治场域后，在理想、现实、派系和制度之间周旋，试图推动一个不同于真实历史走向的新宋，同时也不断面对个人能力与时代惯性的边界。",
    sources: [
      ["维基百科", "Wikipedia", "https://zh.wikipedia.org/wiki/%E6%96%B0%E5%AE%8B"],
      ["微信读书", "微信读书", "https://weread.qq.com/web/search/books?author=%E9%98%BF%E8%B6%8A"]
    ]
  },
  {
    id: "0200000043",
    title: "风姿物语",
    author: "罗森",
    year: 1997,
    tags: ["奇幻", "玄幻", "冒险"],
    genres: ["网络小说", "奇幻小说"],
    summary: "早期中文网络奇幻小说代表作之一。作品以庞大的异世界设定和多线人物关系展开，融合冒险、战争、政治、魔法与成长叙事。",
    story: "故事围绕兰斯洛等角色在风之大陆上的冒险和纷争展开，多方势力、历史谜团与人物命运相互牵连，逐步形成横跨大陆格局的史诗叙事。",
    sources: [
      ["维基百科", "Wikipedia", "https://zh.wikipedia.org/zh-hans/%E9%A2%A8%E5%A7%BF%E7%89%A9%E8%AA%9E"],
      ["豆瓣作者作品", "豆瓣", "https://book.douban.com/author/4513708/books?format=pic&sortby=time"]
    ]
  },
  {
    id: "0200000044",
    title: "陈二狗的妖孽人生",
    author: "烽火戏诸侯",
    tags: ["都市", "成长", "现实"],
    genres: ["网络小说", "都市小说"],
    summary: "都市题材网络小说。作品以出身底层的陈二狗为主角，描写他从东北乡村走入城市，在现实、欲望、人情和阶层流动中寻找出路。",
    story: "陈二狗离开熟悉的乡土环境后，进入更复杂的城市社会。他在不同人物与势力的牵引中成长，也不断面对身份、野心、情义和现实规则的考验。",
    sources: [
      ["起点中文网", "起点中文网", "https://www.qidian.com/book/1204224/"],
      ["中国作家网", "中国作家网", "https://www.chinawriter.com.cn/n1/2020/0331/c404027-31655577.html"]
    ]
  },
  {
    id: "0200000045",
    title: "佣兵天下",
    author: "说不得大师",
    tags: ["奇幻", "战争", "冒险"],
    genres: ["网络小说", "奇幻小说"],
    summary: "奇幻战争题材网络小说。作品围绕佣兵团、国家战争、种族冲突和英雄成长展开，以宏大的世界观和群像冒险构成主要叙事。",
    story: "以艾米等年轻佣兵的成长为主线，故事从佣兵任务逐渐扩展到大陆战争与历史命运。个人友情、团队责任和时代巨变交织，推动角色走向更大的战场。",
    sources: [
      ["起点中文网", "起点中文网", "https://www.qidian.com/book/1026121482/"],
      ["微信读书", "微信读书", "https://weread.qq.com/web/search/books?author=%E8%AF%B4%E4%B8%8D%E5%BE%97%E5%A4%A7%E5%B8%88"]
    ]
  },
  {
    id: "0200000046",
    title: "天行健",
    author: "燕垒生",
    tags: ["武侠", "幻想", "战争"],
    genres: ["网络小说", "武侠幻想"],
    summary: "幻想武侠长篇小说。作品以战争、权力、个人信念和时代秩序为核心，塑造了兼具传统武侠气质和架空史诗格局的世界。",
    story: "主人公在战乱和权谋中不断选择自己的道路，个人武勇与国家机器、理想主义与现实规则发生冲突，形成关于秩序、牺牲和命运的长篇叙事。",
    sources: [
      ["微信读书", "微信读书", "https://weread.qq.com/web/bookDetail/fec32090811e1a5d6g019018"],
      ["豆瓣", "豆瓣", "https://book.douban.com/subject/1437858//"]
    ]
  },
  {
    id: "0200000047",
    title: "鬼吹灯",
    author: "天下霸唱",
    year: 2006,
    tags: ["悬疑", "探险", "盗墓"],
    genres: ["网络小说", "悬疑灵异"],
    summary: "悬疑探险类网络小说代表作。作品以胡八一、王胖子、Shirley杨等人的探险经历为主线，融合民俗传说、地理秘境和古墓机关。",
    story: "主角一行在不同地域和古墓遗迹中寻找线索，面对机关、传说和未知危险。系列通过多卷探险串联人物身世、历史谜团和民间志怪想象。",
    sources: [
      ["维基百科", "Wikipedia", "https://zh.wikipedia.org/wiki/%E9%AC%BC%E5%90%B9%E7%81%AF"]
    ]
  },
  {
    id: "0200000048",
    title: "第一次的亲密接触",
    author: "痞子蔡",
    year: 1998,
    otherTitles: ["第一次亲密接触"],
    tags: ["爱情", "网络文学", "青春"],
    genres: ["网络小说", "爱情小说"],
    summary: "早期中文网络文学代表作。小说以网络聊天和现实相遇为线索，讲述痞子蔡与轻舞飞扬之间带有青春、浪漫和遗憾色彩的爱情故事。",
    story: "主人公在网络上结识轻舞飞扬，两人从文字交流走向现实接触。故事在轻快幽默的网络语言背后，逐渐显露疾病、离别和青春记忆的伤感底色。",
    sources: [
      ["维基百科", "Wikipedia", "https://zh.wikipedia.org/wiki/%E7%AC%AC%E4%B8%80%E6%AC%A1%E7%9A%84%E8%A6%AA%E5%AF%86%E6%8E%A5%E8%A7%B8"],
      ["豆瓣", "豆瓣", "https://m.douban.com/book/subject/1566311/"]
    ]
  },
  {
    id: "0200000049",
    title: "悟空传",
    author: "今何在",
    year: 2000,
    tags: ["神话", "重写", "幻想"],
    genres: ["网络小说", "奇幻小说"],
    summary: "以《西游记》人物为基础的重写型网络小说。作品用现代意识重新诠释孙悟空、唐僧、猪八戒等角色，突出反抗、宿命和自我追问。",
    story: "孙悟空等角色在既定神佛秩序和个人自由之间挣扎。小说通过碎片化叙事与神话重构，呈现人物对命运、记忆、爱情和反抗意义的追寻。",
    sources: [
      ["维基百科", "Wikipedia", "https://zh.wikipedia.org/wiki/%E4%BB%8A%E4%BD%95%E5%9C%A8"],
      ["中国作家网", "中国作家网", "https://www.chinawriter.com.cn/n1/2017/0717/c404079-29409132.html"]
    ]
  },
  {
    id: "0200000050",
    title: "飘邈之旅",
    author: "萧潜",
    year: 2002,
    otherTitles: ["飘渺之旅"],
    tags: ["修真", "仙侠", "玄幻"],
    genres: ["网络小说", "仙侠小说"],
    summary: "早期修真小说代表作之一。作品以李强的修行历程为核心，展开从现代现实到修真世界、星际空间与多层境界的冒险。",
    story: "李强因机缘踏入修真道路，在不断突破境界和结识同伴的过程中游历多个世界。小说以升级、法宝、门派和异域冒险奠定了后来修真文的重要类型范式。",
    sources: [
      ["抖音百科", "抖音百科", "https://m.baike.com/wikiid/3469911547108204524"],
      ["搜狐", "搜狐", "https://www.sohu.com/a/674854587_121698175"]
    ]
  },
  {
    id: "0200000051",
    title: "亵渎",
    author: "烟雨江南",
    tags: ["奇幻", "史诗", "黑暗"],
    genres: ["网络小说", "奇幻小说"],
    summary: "西式奇幻风格网络小说。作品以罗格的成长与权力道路为主线，构建宗教、战争、欲望和命运交织的黑暗奇幻世界。",
    story: "罗格在复杂的大陆格局中不断攀爬，经历战争、阴谋、信仰和情感的试炼。故事以反英雄式人物和灰色价值观展开，呈现奇幻世界中的权力与代价。",
    sources: [
      ["豆瓣评论", "豆瓣", "https://m.douban.com/book/review/14604982/"],
      ["搜狐", "搜狐", "https://www.sohu.com/a/756234842_121698175"]
    ]
  },
  {
    id: "0200000052",
    title: "花千骨",
    author: "Fresh果果",
    otherTitles: ["仙侠奇缘之花千骨"],
    tags: ["仙侠", "爱情", "师徒"],
    genres: ["网络小说", "仙侠小说"],
    summary: "仙侠爱情题材网络小说。作品围绕花千骨与白子画之间的师徒情感、命运牵绊和仙门纷争展开，兼具虐恋、成长与仙侠世界观。",
    story: "花千骨拜入长留后与白子画产生深刻羁绊，却因身份、命格和仙魔冲突不断遭遇误解与磨难。故事在爱情、责任和正邪秩序之间推进悲剧性命运。",
    sources: [
      ["晋江文学城", "晋江文学城", "https://www.jjwxc.net/onebook.php?novelid=316358"],
      ["萌娘百科", "萌娘百科", "https://zh.moegirl.org.cn/%E8%8A%B1%E5%8D%83%E9%AA%A8"]
    ]
  },
  {
    id: "0200000053",
    title: "宰执天下",
    author: "cuslaa",
    tags: ["历史", "两宋元明", "穿越"],
    genres: ["网络小说", "历史小说"],
    summary: "宋代背景的架空历史小说。作品以主角进入北宋政治社会后的经历为核心，展开军事、政务、技术、士人政治和天下格局的长篇叙事。",
    story: "主角在北宋时代逐步进入权力中心，借助知识、制度和现实判断影响历史走向。小说通过朝堂、边疆和社会治理多线推进，呈现个人与时代结构的互动。",
    sources: [
      ["微信读书", "微信读书", "https://weread.qq.com/web/bookDetail/8f432ca052ba378f4cd737b"],
      ["抖音百科", "抖音百科", "https://m.baike.com/wikiid/8369379632458482201"]
    ]
  },
  {
    id: "0200000054",
    title: "十日终焉",
    author: "杀虫队队员",
    wordCount: 3201000,
    tags: ["悬疑", "无限流", "群像"],
    genres: ["网络小说", "悬疑小说"],
    summary: "悬疑生存题材网络小说。故事围绕被卷入异常空间的角色群体展开，在有限时间、规则博弈和不断反转的局面中推进。",
    story: "主角与众多人物被迫进入充满规则和危险的局面，需要在十日循环、谜题和人性考验中寻找生路。作品以群像、推理和世界观揭示为主要驱动力。",
    sources: [
      ["番茄小说", "番茄小说", "https://fanqienovel.com/page/7143038691944959011"],
      ["中国作家网", "中国作家网", "https://www.chinawriter.com.cn/n1/2024/0227/c404024-40184501.html"]
    ]
  }
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function externalSource(sources, title = "") {
  return sources.map(([name, id, link]) => ({
    name,
    id: `${id}:${title}`,
    link
  }));
}

function staging(record) {
  const sourceNames = record.sources.map((source) => source[0]).join(", ");
  const fieldSources = {
    title: "manual_fallback",
    country: "manual_fallback",
    language: "manual_fallback",
    summary: "manual_fallback",
    story: "manual_fallback"
  };
  if (record.year) fieldSources.year = "manual_fallback";
  if (record.wordCount) fieldSources.wordCount = "manual_fallback";

  return {
    id: record.id,
    title: record.title,
    titleOriginal: null,
    otherTitles: record.otherTitles || null,
    isbn: null,
    year: record.year || null,
    country: "中国",
    language: "中文",
    wordCount: record.wordCount || null,
    publisher: null,
    publishDate: null,
    pages: null,
    price: null,
    binding: null,
    format: null,
    edition: null,
    summary: record.summary,
    story: record.story,
    quotes: null,
    excerpts: null,
    seriesId: null,
    seriesOrder: null,
    scores: null,
    externalSource: externalSource(record.sources, record.title),
    images: null,
    reviews: null,
    related: null,
    status: "draft",
    _meta: {
      fieldSources,
      conflicts: [],
      authors: [record.author],
      translators: [],
      tags: record.tags,
      subjects: [],
      genres: record.genres,
      awards: [],
      series: null,
      seriesCandidates: [],
      coverUrls: {},
      prices: {},
      personDetails: [],
      isWebNovel: true,
      contentKind: "web_novel",
      batchRunId: runId,
      manualFallback: {
        reason: "Existing automated sources did not produce safe whole-work staging in the fast batch.",
        sourceNames,
        sourceGovernance: "candidate/reference/manual_fallback only; not a new automated adapter"
      }
    }
  };
}

function rawManual(record) {
  return {
    source: "manual_fallback",
    title: record.title,
    authors: [record.author],
    year: record.year || null,
    word_count: record.wordCount || null,
    summary: record.summary,
    story: record.story,
    tags: record.tags,
    genres: record.genres,
    sources: externalSource(record.sources, record.title),
    note: "Manual fallback raw compiled from reviewed candidate/reference anchors. This is not an automated source adapter."
  };
}

ensureDir(stagingDir);
ensureDir(rawDir);
ensureDir(manifestDir);

for (const record of records) {
  const itemRawDir = path.join(rawDir, record.id);
  ensureDir(itemRawDir);
  fs.writeFileSync(
    path.join(itemRawDir, "manual_fallback.json"),
    JSON.stringify(rawManual(record), null, 2),
    "utf8"
  );
  fs.writeFileSync(
    path.join(stagingDir, `${record.id}.json`),
    JSON.stringify(staging(record), null, 2),
    "utf8"
  );
}

const manifest = {
  runId,
  createdAt: "2026-06-11",
  status: "manual_fallback_staging_ready",
  sourceRunId: "2026-06-11-web-novel-blocked-source-review",
  profile: "manual-fallback",
  scope: {
    total: records.length,
    idRange: `${records[0].id}-${records[records.length - 1].id}`,
    writeDatabase: false,
    note: "Staging only. Import still requires import_staging.py precheck and explicit approval JSON."
  },
  items: records.map((record) => ({
    bookId: record.id,
    title: record.title,
    authors: [record.author],
    type: "web_novel",
    contentKind: "web_novel",
    expectedAction: "create",
    profile: "manual-fallback",
    sourcePolicy: "candidate/reference/manual_fallback; not automated adapter"
  }))
};

const manifestPath = path.join(manifestDir, `${runId}.json`);
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf8");
console.log(JSON.stringify({ runId, total: records.length, manifest: manifestPath }, null, 2));
