# Movie Ingest Acceptance

> 本文档用于验收当前电影样板在“旧数据 -> 新流程数据 -> 数据库目标字段”这一层是否对齐。
> 旧的当前数据内容：来自 `.local/staging/video/movie/*.json`。
> 新流程数据内容：来自 `.local/new-flow/video/movie/*.json`。
> 数据来源或处理逻辑：来自 `.local/new-flow-field-sources/video/movie/*.json`，并补充必要的派生说明。

> 当前基线说明：电影 DB-first 样板已扩展到 6 部，其中 `0101000005`《肖申克的救赎1》与 `0101000006`《星际穿越》已作为当前高标准录入样板，重点验证完整评论结构、主海报来源、地区推断与前台展示链路。

## 0101000001 肖申克的救赎

### `works.id`

旧的当前数据内容：
```json
"0101000001"
```

新流程数据内容：
```json
"0101000001"
```

数据来源或处理逻辑：system; 系统自动生成，递增序号

### `works.module`

旧的当前数据内容：
```json
"video"
```

新流程数据内容：
```json
"video"
```

数据来源或处理逻辑：system; 影视模块

### `works.submodule`

旧的当前数据内容：
```json
"movie"
```

新流程数据内容：
```json
"movie"
```

数据来源或处理逻辑：system; 电影子模块

### `works.schema_type`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"live_action_movie"
```

数据来源或处理逻辑：system; 电影样板当前固定写入 live_action_movie

### `works.title`

旧的当前数据内容：
```json
"肖申克的救赎"
```

新流程数据内容：
```json
"肖申克的救赎"
```

数据来源或处理逻辑：douban; 豆瓣条目标题

### `works.original_title`

旧的当前数据内容：
```json
"The Shawshank Redemption"
```

新流程数据内容：
```json
"The Shawshank Redemption"
```

数据来源或处理逻辑：douban

### `works.year`

旧的当前数据内容：
```json
1994
```

新流程数据内容：
```json
1994
```

数据来源或处理逻辑：douban

### `works.country`

旧的当前数据内容：
```json
"美国"
```

新流程数据内容：
```json
"美国"
```

数据来源或处理逻辑：douban

### `works.language`

旧的当前数据内容：
```json
"英语"
```

新流程数据内容：
```json
"英语"
```

数据来源或处理逻辑：douban

### `works.publish_company`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
null
```

数据来源或处理逻辑：system; 当前样板缺少稳定出品公司来源，先保留空值

### `works.runtime_minutes`

旧的当前数据内容：
```json
142
```

新流程数据内容：
```json
142
```

数据来源或处理逻辑：douban; 单位：分钟

### `works.synopsis_text`

旧的当前数据内容：
```json
"银行家安迪被误判入狱，在肖申克监狱与瑞德结下深厚友谊，并凭借冷静头脑在高墙之内为自己争取生存空间。\n\n当翻案希望被再次掐灭，他把多年隐忍、智慧与信念化为一场惊人的自我救赎，也让瑞德重新相信自由并非遥不可及。"
```

新流程数据内容：
```json
"银行家安迪被误判入狱，在肖申克监狱与瑞德结下深厚友谊，并凭借冷静头脑在高墙之内为自己争取生存空间。\n\n当翻案希望被再次掐灭，他把多年隐忍、智慧与信念化为一场惊人的自我救赎，也让瑞德重新相信自由并非遥不可及。"
```

数据来源或处理逻辑：merged: douban(text) + manual(text) + omdb(note); 短简介基于公开剧情整理，附加提名说明

### `works.synopsis_note`

旧的当前数据内容：
```json
"本片获得1995年奥斯卡最佳影片等7项提名。"
```

新流程数据内容：
```json
"本片获得1995年奥斯卡最佳影片等7项提名。"
```

数据来源或处理逻辑：merged: douban(text) + manual(text) + omdb(note); 短简介基于公开剧情整理，附加提名说明

### `works.story_text`

旧的当前数据内容：
```json
"1947年，年轻银行家安迪·杜佛兰因妻子及其情人被杀一案被判无期徒刑，押入肖申克监狱。沉默寡言的他很快引起老囚犯瑞德的注意，并通过瑞德弄到石锤、海报等小物件，在残酷秩序里一点点建立自己的生存方式。面对\"姐妹帮\"的欺凌、狱警的暴力和监狱制度的冷酷，安迪始终没有放弃对尊严的维护。\n\n凭借金融与税务知识，安迪先后帮助狱警处理报税问题，也被典狱长诺顿拿来经营账目、洗白黑钱。与此同时，他推动扩建图书馆、为囚犯争取读物和教育机会，让肖申克这座高墙之内第一次出现了真正意义上的精神空间。老布出狱后的崩溃与自尽，也让安迪和瑞德更清楚\"体制化\"对人的吞噬。\n\n后来，年轻囚犯汤米提供了可能证明安迪清白的关键线索。安迪满怀希望去找诺顿申诉，却发现典狱长为了保住自己的利益，宁可枪杀证人，也不愿让他重获自由。所有合法翻案的道路被堵死后，安迪把多年隐忍转化为最后一次行动。\n\n一个暴雨之夜，瑞德才明白石锤、海报与地质学兴趣背后藏着怎样漫长而坚定的计划：安迪用近二十年时间凿开牢墙，沿着下水道逃出生天，并顺手将诺顿的犯罪证据寄给媒体和检察机关。典狱长自尽、狱警被捕，安迪则以假身份取走存款，前往太平洋海边的芝华塔内霍等待新生活。\n\n多年后获假释的瑞德违背\"不再越界\"的承诺，依照安迪留下的线索找到一笔钱和一封信，终于鼓起勇气踏出被制度驯化的人生。他穿越边境来到海边，与正在修船的安迪重逢。"
```

新流程数据内容：
```json
"1947年，年轻银行家安迪·杜佛兰因妻子及其情人被杀一案被判无期徒刑，押入肖申克监狱。沉默寡言的他很快引起老囚犯瑞德的注意，并通过瑞德弄到石锤、海报等小物件，在残酷秩序里一点点建立自己的生存方式。面对\"姐妹帮\"的欺凌、狱警的暴力和监狱制度的冷酷，安迪始终没有放弃对尊严的维护。\n\n凭借金融与税务知识，安迪先后帮助狱警处理报税问题，也被典狱长诺顿拿来经营账目、洗白黑钱。与此同时，他推动扩建图书馆、为囚犯争取读物和教育机会，让肖申克这座高墙之内第一次出现了真正意义上的精神空间。老布出狱后的崩溃与自尽，也让安迪和瑞德更清楚\"体制化\"对人的吞噬。\n\n后来，年轻囚犯汤米提供了可能证明安迪清白的关键线索。安迪满怀希望去找诺顿申诉，却发现典狱长为了保住自己的利益，宁可枪杀证人，也不愿让他重获自由。所有合法翻案的道路被堵死后，安迪把多年隐忍转化为最后一次行动。\n\n一个暴雨之夜，瑞德才明白石锤、海报与地质学兴趣背后藏着怎样漫长而坚定的计划：安迪用近二十年时间凿开牢墙，沿着下水道逃出生天，并顺手将诺顿的犯罪证据寄给媒体和检察机关。典狱长自尽、狱警被捕，安迪则以假身份取走存款，前往太平洋海边的芝华塔内霍等待新生活。\n\n多年后获假释的瑞德违背\"不再越界\"的承诺，依照安迪留下的线索找到一笔钱和一封信，终于鼓起勇气踏出被制度驯化的人生。他穿越边境来到海边，与正在修船的安迪重逢。"
```

数据来源或处理逻辑：manual; 基于百科剧情介绍与现有条目整理的完整剧情；story.note 不再进入数据库主字段

### `works.aliases_json`

旧的当前数据内容：
```json
[
  "月黑高飞(港)",
  "刺激1995(台)",
  "地狱诺言",
  "铁窗岁月",
  "消香克的救赎"
]
```

新流程数据内容：
```json
[
  "月黑高飞(港)",
  "刺激1995(台)",
  "地狱诺言",
  "铁窗岁月",
  "消香克的救赎"
]
```

数据来源或处理逻辑：douban

### `works.release_dates_json`

旧的当前数据内容：
```json
[
  {
    "date": "1994-09-10",
    "location": "多伦多电影节"
  },
  {
    "date": "1994-10-14",
    "location": "美国"
  }
]
```

新流程数据内容：
```json
[
  {
    "date": "1994-09-10",
    "location": "多伦多电影节"
  },
  {
    "date": "1994-10-14",
    "location": "美国"
  }
]
```

数据来源或处理逻辑：douban

### `works.identifiers_json`

旧的当前数据内容：
```json
{
  "douban": "1292052",
  "imdb": "tt0111161",
  "tmdb": null
}
```

新流程数据内容：
```json
{
  "douban": "1292052",
  "imdb": "tt0111161",
  "tmdb": "278"
}
```

数据来源或处理逻辑：doubanId:douban; imdbId:douban; tmdbId:derived; 从 links.tmdb URL 解析出 TMDB movie id

### `works.ratings_json`

旧的当前数据内容：
```json
{
  "aggregate": {
    "value": 9.7,
    "scale": 10
  },
  "douban": {
    "value": 9.7,
    "scale": 10
  },
  "imdb": {
    "value": null,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": null
  },
  "awards": {
    "value": null
  }
}
```

新流程数据内容：
```json
{
  "aggregate": {
    "value": 9.7,
    "scale": 10
  },
  "douban": {
    "value": 9.7,
    "scale": 10
  },
  "imdb": {
    "value": null,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": null
  },
  "awards": {
    "value": null
  }
}
```

数据来源或处理逻辑：doubanRating:douban

### `works.links_json`

旧的当前数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1292052/",
  "imdb": "https://www.imdb.com/title/tt0111161/",
  "tmdb": "https://www.themoviedb.org/movie/278"
}
```

新流程数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1292052/",
  "imdb": "https://www.imdb.com/title/tt0111161/",
  "tmdb": "https://www.themoviedb.org/movie/278"
}
```

数据来源或处理逻辑：merged: douban(douban/imdb) + tmdb(tmdb)

### `works.images_json`

旧的当前数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.png",
    "poster-02.png",
    "poster-03.png",
    "poster-04.png",
    "poster-05.png",
    "poster-06.png",
    "poster-07.png",
    "poster-08.png",
    "poster-09.png",
    "poster-10.png"
  ],
  "stills": [
    "still-01.png",
    "still-02.png",
    "still-03.png",
    "still-04.png",
    "still-05.png",
    "still-06.png",
    "still-07.png",
    "still-08.png",
    "still-09.png",
    "still-10.png",
    "still-11.png",
    "still-12.png",
    "still-13.png"
  ],
  "wallpapers": [
    "wallpaper-01.png",
    "wallpaper-02.png",
    "wallpaper-03.png",
    "wallpaper-04.png"
  ],
  "postersTotal": 149,
  "stillsTotal": 918,
  "assetDir": "video/movie/0101000001"
}
```

新流程数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.png",
    "poster-02.png",
    "poster-03.png",
    "poster-04.png",
    "poster-05.png",
    "poster-06.png",
    "poster-07.png",
    "poster-08.png",
    "poster-09.png",
    "poster-10.png"
  ],
  "stills": [
    "still-01.png",
    "still-02.png",
    "still-03.png",
    "still-04.png",
    "still-05.png",
    "still-06.png",
    "still-07.png",
    "still-08.png",
    "still-09.png",
    "still-10.png",
    "still-11.png",
    "still-12.png",
    "still-13.png"
  ],
  "wallpapers": [
    "wallpaper-01.png",
    "wallpaper-02.png",
    "wallpaper-03.png",
    "wallpaper-04.png"
  ],
  "postersTotal": 149,
  "stillsTotal": 918,
  "assetDir": "video/movie/0101000001"
}
```

数据来源或处理逻辑：poster:douban; posters:douban; postersTotal:douban; stills:douban; stillsTotal:douban; wallpapers:manual

### `works.videos_json`

旧的当前数据内容：
```json
[
  {
    "title": "预告片1：25周年经典重映",
    "duration": "01:30",
    "thumbnail": "video-trailer-01.png",
    "url": "https://movie.douban.com/trailer/259258/"
  },
  {
    "title": "预告片2",
    "duration": "02:13",
    "thumbnail": "video-trailer-02.png",
    "url": "https://movie.douban.com/trailer/108756/"
  }
]
```

新流程数据内容：
```json
[
  {
    "title": "预告片1：25周年经典重映",
    "duration": "01:30",
    "thumbnail": "video-trailer-01.png",
    "url": "https://movie.douban.com/trailer/259258/"
  },
  {
    "title": "预告片2",
    "duration": "02:13",
    "thumbnail": "video-trailer-02.png",
    "url": "https://movie.douban.com/trailer/108756/"
  }
]
```

数据来源或处理逻辑：douban; 豆瓣预告片列表整理

### `works.reviews_json`

旧的当前数据内容：
```json
[
  {
    "source": "豆瓣",
    "author": "大头绿豆",
    "date": "2005-05-12",
    "rating": "力荐",
    "content": "距离斯蒂芬·金和德拉邦特缔造这部作品已经有十年了。在我眼里，《肖申克的救赎》与信念、自由和友谊有关。它真正动人的地方不在越狱奇观，而在安迪和瑞德如何在体制化的牢狱中保住内心的秩序，并把希望从一句空话变成一条通往海边的路。"
  },
  {
    "source": "豆瓣",
    "author": "隱居雲上",
    "date": "2005-07-12",
    "rating": "力荐",
    "content": "不同的人看同样的影片会有不同感受。对于无力改变现状的人，这部电影最有力量的地方，在于它提醒你：才华和毅力并不会立刻拯救人生，但会在最漫长的黑夜里替你守住方向。安迪的忍耐不是认命，而是在等待一个真正能改变命运的时刻。"
  },
  {
    "source": "豆瓣",
    "author": "泠十三",
    "date": "2019-07-29",
    "rating": "力荐",
    "content": "肖申克不只是监狱，也是每个人被规训、被命运判定的位置。安迪的救赎之所以成立，不仅因为他逃出高墙，更因为他拒绝接受\"习惯了就算了\"的人生。电影真正厉害的地方，是让观众在瑞德的变化里看见希望如何从怀疑变成相信。"
  },
  {
    "source": "豆瓣",
    "author": "aratana",
    "date": "2007-02-26",
    "rating": "力荐",
    "content": "这部电影最难复制的，是它把希望拍成了可以被相信的现实。它不是廉价鸡汤，而是让人在最灰暗的处境里，仍愿意相信自由、尊严和友谊值得被等待。时间越久，它越像一部会在不同年龄反复生效的电影。"
  }
]
```

新流程数据内容：
```json
[
  {
    "author": "大头绿豆",
    "source": "豆瓣",
    "date": "2005-05-12",
    "content": "距离斯蒂芬·金和德拉邦特缔造这部作品已经有十年了。在我眼里，《肖申克的救赎》与信念、自由和友谊有关。它真正动人的地方不在越狱奇观，而在安迪和瑞德如何在体制化的牢狱中保住内心的秩序，并把希望从一句空话变成一条通往海边的路。",
    "url": "https://movie.douban.com/review/1000369/",
    "title": "十年·肖申克的救赎"
  },
  {
    "author": "隱居雲上",
    "source": "豆瓣",
    "date": "2005-07-12",
    "content": "不同的人看同样的影片会有不同感受。对于无力改变现状的人，这部电影最有力量的地方，在于它提醒你：才华和毅力并不会立刻拯救人生，但会在最漫长的黑夜里替你守住方向。安迪的忍耐不是认命，而是在等待一个真正能改变命运的时刻。",
    "url": "https://movie.douban.com/review/1001258/",
    "title": "终于找到了郁闷人生的原因――观《肖申克的救赎》有感"
  },
  {
    "author": "泠十三",
    "source": "豆瓣",
    "date": "2019-07-29",
    "content": "肖申克不只是监狱，也是每个人被规训、被命运判定的位置。安迪的救赎之所以成立，不仅因为他逃出高墙，更因为他拒绝接受\"习惯了就算了\"的人生。电影真正厉害的地方，是让观众在瑞德的变化里看见希望如何从怀疑变成相信。",
    "url": "https://movie.douban.com/review/10350620/",
    "title": "《肖申克的救赎》到底“救赎”了什么？"
  },
  {
    "author": "aratana",
    "source": "豆瓣",
    "date": "2007-02-26",
    "content": "这部电影最难复制的，是它把希望拍成了可以被相信的现实。它不是廉价鸡汤，而是让人在最灰暗的处境里，仍愿意相信自由、尊严和友谊值得被等待。时间越久，它越像一部会在不同年龄反复生效的电影。",
    "url": "https://movie.douban.com/review/1127585/",
    "title": "《肖申克的救赎》：1994—2007，希望就是现实"
  }
]
```

数据来源或处理逻辑：douban; 豆瓣影评页精选长评前4条；已补 review.url/title，rating 不再进入数据库

### `works.soundtrack_json`

旧的当前数据内容：
```json
{
  "albums": [
    {
      "name": "The Shawshank Redemption (Original Motion Picture Soundtrack)",
      "note": "托马斯·纽曼 / Thomas Newman",
      "coverImage": null,
      "releaseDate": "1994",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "Introduction",
          "artist": null,
          "duration": "0:04"
        },
        {
          "name": "End Title",
          "artist": null,
          "duration": "3:34"
        },
        {
          "name": "Shawshank Prison",
          "artist": null,
          "duration": "1:55"
        },
        {
          "name": "Brooks Was Here",
          "artist": null,
          "duration": "2:41"
        },
        {
          "name": "New Fish Arrive",
          "artist": null,
          "duration": "1:32"
        },
        {
          "name": "Rock Hammer",
          "artist": null,
          "duration": "1:52"
        },
        {
          "name": "An Innocent Man",
          "artist": null,
          "duration": "1:58"
        },
        {
          "name": "The Moocher",
          "artist": null,
          "duration": "1:36"
        },
        {
          "name": "Suds",
          "artist": null,
          "duration": "1:02"
        },
        {
          "name": "Loafing",
          "artist": null,
          "duration": "1:06"
        },
        {
          "name": "The Marriage of Figaro / Duettino - Sull'aria",
          "artist": null,
          "duration": "2:54"
        },
        {
          "name": "Compass and Guns",
          "artist": null,
          "duration": "2:04"
        },
        {
          "name": "The Riddle of Zihuatanejo",
          "artist": null,
          "duration": "1:25"
        },
        {
          "name": "The Riddle Solved",
          "artist": null,
          "duration": "1:30"
        },
        {
          "name": "The Tunnel",
          "artist": null,
          "duration": "1:30"
        },
        {
          "name": "Freedom",
          "artist": null,
          "duration": "1:42"
        }
      ]
    }
  ]
}
```

新流程数据内容：
```json
{
  "albums": [
    {
      "name": "The Shawshank Redemption (Original Motion Picture Soundtrack)",
      "note": "托马斯·纽曼 / Thomas Newman",
      "coverImage": null,
      "releaseDate": "1994",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "Introduction",
          "artist": null,
          "duration": "0:04"
        },
        {
          "name": "End Title",
          "artist": null,
          "duration": "3:34"
        },
        {
          "name": "Shawshank Prison",
          "artist": null,
          "duration": "1:55"
        },
        {
          "name": "Brooks Was Here",
          "artist": null,
          "duration": "2:41"
        },
        {
          "name": "New Fish Arrive",
          "artist": null,
          "duration": "1:32"
        },
        {
          "name": "Rock Hammer",
          "artist": null,
          "duration": "1:52"
        },
        {
          "name": "An Innocent Man",
          "artist": null,
          "duration": "1:58"
        },
        {
          "name": "The Moocher",
          "artist": null,
          "duration": "1:36"
        },
        {
          "name": "Suds",
          "artist": null,
          "duration": "1:02"
        },
        {
          "name": "Loafing",
          "artist": null,
          "duration": "1:06"
        },
        {
          "name": "The Marriage of Figaro / Duettino - Sull'aria",
          "artist": null,
          "duration": "2:54"
        },
        {
          "name": "Compass and Guns",
          "artist": null,
          "duration": "2:04"
        },
        {
          "name": "The Riddle of Zihuatanejo",
          "artist": null,
          "duration": "1:25"
        },
        {
          "name": "The Riddle Solved",
          "artist": null,
          "duration": "1:30"
        },
        {
          "name": "The Tunnel",
          "artist": null,
          "duration": "1:30"
        },
        {
          "name": "Freedom",
          "artist": null,
          "duration": "1:42"
        }
      ]
    }
  ]
}
```

数据来源或处理逻辑：manual; 原声带与曲目单按现有条目整理；已重组为 albums[] 结构

### `works.relations_json`

旧的当前数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "id": "0101000003",
      "title": "阿甘正传",
      "year": 1994,
      "rating": 9.5
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.4
    },
    {
      "title": "当幸福来敲门",
      "year": 2006,
      "rating": 9.1
    },
    {
      "title": "活着",
      "year": 1994,
      "rating": 9.3
    },
    {
      "title": "摔跤吧！爸爸",
      "year": 2016,
      "rating": 9
    },
    {
      "title": "我不是药神",
      "year": 2018,
      "rating": 9
    },
    {
      "title": "三傻大闹宝莱坞",
      "year": 2009,
      "rating": 9.2
    },
    {
      "title": "心灵捕手",
      "year": 1997,
      "rating": 9
    },
    {
      "title": "闻香识女人",
      "year": 1992,
      "rating": 9.1
    },
    {
      "title": "这个杀手不太冷",
      "year": 1994,
      "rating": 9.4
    }
  ]
}
```

新流程数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "id": "0101000003",
      "title": "阿甘正传",
      "year": 1994,
      "rating": 9.5
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.4
    },
    {
      "title": "当幸福来敲门",
      "year": 2006,
      "rating": 9.1
    },
    {
      "title": "活着",
      "year": 1994,
      "rating": 9.3
    },
    {
      "title": "摔跤吧！爸爸",
      "year": 2016,
      "rating": 9
    },
    {
      "title": "我不是药神",
      "year": 2018,
      "rating": 9
    },
    {
      "title": "三傻大闹宝莱坞",
      "year": 2009,
      "rating": 9.2
    },
    {
      "title": "心灵捕手",
      "year": 1997,
      "rating": 9
    },
    {
      "title": "闻香识女人",
      "year": 1992,
      "rating": 9.1
    },
    {
      "title": "这个杀手不太冷",
      "year": 1994,
      "rating": 9.4
    }
  ]
}
```

数据来源或处理逻辑：series:system; 当前4条样板未录入系列关系，先保留空数组; similar:manual; 手动整理的相似佳作列表，已收录条目优先补站内 id

### `works.quotes_json`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板未整理 quotes，先保留空数组

### `works.status`

旧的当前数据内容：
```json
"published"
```

新流程数据内容：
```json
"published"
```

数据来源或处理逻辑：system; 当前电影样板默认按 published 导入

### `works.created_at`

旧的当前数据内容：
```json
"2026-05-01"
```

新流程数据内容：
```json
"2026-05-01"
```

数据来源或处理逻辑：system; 录入时间

### `works.updated_at`

旧的当前数据内容：
```json
"2026-05-02"
```

新流程数据内容：
```json
"2026-05-02"
```

数据来源或处理逻辑：system; 最后更新时间

### `credits.director`

旧的当前数据内容：
```json
[
  {
    "name": "弗兰克·德拉邦特",
    "nameEn": "Frank Darabont",
    "avatar": "avatar-frank-darabont.png",
    "works": [
      "肖申克的救赎",
      "绿里奇迹",
      "迷雾"
    ]
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "弗兰克·德拉邦特",
    "nameEn": "Frank Darabont",
    "avatar": "avatar-frank-darabont.png",
    "works": [
      "肖申克的救赎",
      "绿里奇迹",
      "迷雾"
    ]
  }
]
```

数据来源或处理逻辑：merged: douban(name) + manual(nameEn/avatar/works)

### `credits.writer`

旧的当前数据内容：
```json
[
  {
    "name": "弗兰克·德拉邦特",
    "nameEn": "Frank Darabont",
    "role": "编剧",
    "baike": "https://baike.baidu.com/item/弗兰克·德拉邦特"
  },
  {
    "name": "斯蒂芬·金",
    "nameEn": "Stephen King",
    "role": "原著",
    "baike": "https://baike.baidu.com/item/斯蒂芬·金"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "弗兰克·德拉邦特",
    "nameEn": "Frank Darabont",
    "role": "编剧",
    "baike": "https://baike.baidu.com/item/弗兰克·德拉邦特"
  },
  {
    "name": "斯蒂芬·金",
    "nameEn": "Stephen King",
    "role": "原著",
    "baike": "https://baike.baidu.com/item/斯蒂芬·金"
  }
]
```

数据来源或处理逻辑：merged: douban(name/role) + manual(nameEn/baike)

### `credits.cast`

旧的当前数据内容：
```json
[
  {
    "name": "蒂姆·罗宾斯",
    "nameEn": "Tim Robbins",
    "role": "安迪·杜佛兰",
    "avatar": "avatar-tim-robbins.png"
  },
  {
    "name": "摩根·弗里曼",
    "nameEn": "Morgan Freeman",
    "role": "瑞德",
    "avatar": "avatar-morgan-freeman.png"
  },
  {
    "name": "鲍勃·冈顿",
    "nameEn": "Bob Gunton",
    "role": "监狱长诺顿",
    "avatar": "avatar-bob-gunton.png"
  },
  {
    "name": "威廉·赛德勒",
    "nameEn": "William Sadler",
    "role": "海伍德",
    "avatar": "avatar-william-sadler.png"
  },
  {
    "name": "克兰西·布朗",
    "nameEn": "Clancy Brown",
    "role": "上尉哈德利",
    "avatar": "avatar-clancy-brown.png"
  },
  {
    "name": "吉尔·贝罗斯",
    "nameEn": "Gil Bellows",
    "role": "汤米",
    "avatar": "avatar-gil-bellows.png"
  },
  {
    "name": "马克·罗斯顿",
    "nameEn": "Mark Rolston",
    "role": "包格斯",
    "avatar": "avatar-mark-rolston.png"
  },
  {
    "name": "詹姆斯·惠特摩",
    "nameEn": "James Whitmore",
    "role": "老布",
    "avatar": "avatar-james-whitmore.png"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "蒂姆·罗宾斯",
    "nameEn": "Tim Robbins",
    "role": "安迪·杜佛兰",
    "avatar": "avatar-tim-robbins.png"
  },
  {
    "name": "摩根·弗里曼",
    "nameEn": "Morgan Freeman",
    "role": "瑞德",
    "avatar": "avatar-morgan-freeman.png"
  },
  {
    "name": "鲍勃·冈顿",
    "nameEn": "Bob Gunton",
    "role": "监狱长诺顿",
    "avatar": "avatar-bob-gunton.png"
  },
  {
    "name": "威廉·赛德勒",
    "nameEn": "William Sadler",
    "role": "海伍德",
    "avatar": "avatar-william-sadler.png"
  },
  {
    "name": "克兰西·布朗",
    "nameEn": "Clancy Brown",
    "role": "上尉哈德利",
    "avatar": "avatar-clancy-brown.png"
  },
  {
    "name": "吉尔·贝罗斯",
    "nameEn": "Gil Bellows",
    "role": "汤米",
    "avatar": "avatar-gil-bellows.png"
  },
  {
    "name": "马克·罗斯顿",
    "nameEn": "Mark Rolston",
    "role": "包格斯",
    "avatar": "avatar-mark-rolston.png"
  },
  {
    "name": "詹姆斯·惠特摩",
    "nameEn": "James Whitmore",
    "role": "老布",
    "avatar": "avatar-james-whitmore.png"
  }
]
```

数据来源或处理逻辑：merged: douban(name/role) + manual(nameEn/avatar); 主演与头像按当前条目落库结果整理

### `credits.otherCast`

旧的当前数据内容：
```json
[
  {
    "name": "杰弗里·德曼",
    "nameEn": "Jeffrey DeMunn",
    "role": "1946地方检察官"
  },
  {
    "name": "拉里·布兰登伯格",
    "nameEn": "Larry Brandenburg",
    "role": "斯基特 Skeet"
  },
  {
    "name": "尼尔·吉恩托利",
    "nameEn": "Neil Giuntoli",
    "role": "基格 Jigger"
  },
  {
    "name": "布赖恩·利比",
    "nameEn": "Brian Libby",
    "role": "弗洛依德 Floyd"
  },
  {
    "name": "大卫·普罗瓦尔",
    "nameEn": "David Proval",
    "role": "瞌睡虫 Snooze"
  },
  {
    "name": "约瑟夫·劳格诺",
    "nameEn": "Joseph Ragno",
    "role": "厄尼 Ernie"
  },
  {
    "name": "祖德·塞克利拉",
    "nameEn": "Jude Ciccolella",
    "role": "守卫梅特 Guard Mert"
  },
  {
    "name": "保罗·麦克兰尼",
    "nameEn": "Paul McCrane",
    "role": "守卫特劳特 Guard Trout"
  },
  {
    "name": "芮妮·布莱恩",
    "nameEn": "Renee Blaine",
    "role": "安迪·杜佛兰的妻子"
  },
  {
    "name": "阿方索·弗里曼",
    "nameEn": "Alfonso Freeman",
    "role": "新囚犯 Fresh Fish Con"
  },
  {
    "name": "V·J·福斯特",
    "nameEn": "V.J. Foster",
    "role": "囚犯 Hungry Fish Con"
  },
  {
    "name": "弗兰克·梅德拉诺",
    "nameEn": "Frank Medrano",
    "role": "肥仔 Fat Ass"
  },
  {
    "name": "马克·迈尔斯",
    "nameEn": "Mack Miles",
    "role": "蒂雷尔 Tyrell"
  },
  {
    "name": "尼尔·萨默斯",
    "nameEn": "Neil Summers",
    "role": "皮特 Pete"
  },
  {
    "name": "耐德·巴拉米",
    "nameEn": "Ned Bellamy",
    "role": "守卫扬布拉德 Guard Youngblood"
  },
  {
    "name": "布赖恩·戴拉特",
    "nameEn": "Brian Delate",
    "role": "守卫德金斯 Guard Dekins"
  },
  {
    "name": "唐·麦克马纳斯",
    "nameEn": "Don McManus",
    "role": "守卫威利 Guard Wiley"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "杰弗里·德曼",
    "nameEn": "Jeffrey DeMunn",
    "role": "1946地方检察官"
  },
  {
    "name": "拉里·布兰登伯格",
    "nameEn": "Larry Brandenburg",
    "role": "斯基特 Skeet"
  },
  {
    "name": "尼尔·吉恩托利",
    "nameEn": "Neil Giuntoli",
    "role": "基格 Jigger"
  },
  {
    "name": "布赖恩·利比",
    "nameEn": "Brian Libby",
    "role": "弗洛依德 Floyd"
  },
  {
    "name": "大卫·普罗瓦尔",
    "nameEn": "David Proval",
    "role": "瞌睡虫 Snooze"
  },
  {
    "name": "约瑟夫·劳格诺",
    "nameEn": "Joseph Ragno",
    "role": "厄尼 Ernie"
  },
  {
    "name": "祖德·塞克利拉",
    "nameEn": "Jude Ciccolella",
    "role": "守卫梅特 Guard Mert"
  },
  {
    "name": "保罗·麦克兰尼",
    "nameEn": "Paul McCrane",
    "role": "守卫特劳特 Guard Trout"
  },
  {
    "name": "芮妮·布莱恩",
    "nameEn": "Renee Blaine",
    "role": "安迪·杜佛兰的妻子"
  },
  {
    "name": "阿方索·弗里曼",
    "nameEn": "Alfonso Freeman",
    "role": "新囚犯 Fresh Fish Con"
  },
  {
    "name": "V·J·福斯特",
    "nameEn": "V.J. Foster",
    "role": "囚犯 Hungry Fish Con"
  },
  {
    "name": "弗兰克·梅德拉诺",
    "nameEn": "Frank Medrano",
    "role": "肥仔 Fat Ass"
  },
  {
    "name": "马克·迈尔斯",
    "nameEn": "Mack Miles",
    "role": "蒂雷尔 Tyrell"
  },
  {
    "name": "尼尔·萨默斯",
    "nameEn": "Neil Summers",
    "role": "皮特 Pete"
  },
  {
    "name": "耐德·巴拉米",
    "nameEn": "Ned Bellamy",
    "role": "守卫扬布拉德 Guard Youngblood"
  },
  {
    "name": "布赖恩·戴拉特",
    "nameEn": "Brian Delate",
    "role": "守卫德金斯 Guard Dekins"
  },
  {
    "name": "唐·麦克马纳斯",
    "nameEn": "Don McManus",
    "role": "守卫威利 Guard Wiley"
  }
]
```

数据来源或处理逻辑：manual; 扩展演员表按当前条目整理

### `credits.producer`

旧的当前数据内容：
```json
[
  {
    "name": "妮基·马文",
    "nameEn": "Niki Marvin",
    "baike": "https://baike.baidu.com/item/妮基·马文"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "妮基·马文",
    "nameEn": "Niki Marvin",
    "baike": "https://baike.baidu.com/item/妮基·马文"
  }
]
```

数据来源或处理逻辑：manual; 制片信息按现有条目整理

### `terms.genre`

旧的当前数据内容：
```json
[
  "剧情",
  "犯罪"
]
```

新流程数据内容：
```json
[
  "剧情",
  "犯罪"
]
```

数据来源或处理逻辑：douban

### `terms.tags`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板尚未建立标签体系，先保留空数组

### `derived.tmdbId`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"278"
```

数据来源或处理逻辑：derived; 从 links.tmdb URL 解析出 TMDB movie id

## 0101000002 迈克尔·杰克逊：巨星之路

### `works.id`

旧的当前数据内容：
```json
"0101000002"
```

新流程数据内容：
```json
"0101000002"
```

数据来源或处理逻辑：system; 系统自动生成，递增序号

### `works.module`

旧的当前数据内容：
```json
"video"
```

新流程数据内容：
```json
"video"
```

数据来源或处理逻辑：system; 影视模块

### `works.submodule`

旧的当前数据内容：
```json
"movie"
```

新流程数据内容：
```json
"movie"
```

数据来源或处理逻辑：system; 电影子模块

### `works.schema_type`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"live_action_movie"
```

数据来源或处理逻辑：system; 电影样板当前固定写入 live_action_movie

### `works.title`

旧的当前数据内容：
```json
"迈克尔·杰克逊：巨星之路"
```

新流程数据内容：
```json
"迈克尔·杰克逊：巨星之路"
```

数据来源或处理逻辑：douban

### `works.original_title`

旧的当前数据内容：
```json
"Michael"
```

新流程数据内容：
```json
"Michael"
```

数据来源或处理逻辑：douban

### `works.year`

旧的当前数据内容：
```json
2026
```

新流程数据内容：
```json
2026
```

数据来源或处理逻辑：douban

### `works.country`

旧的当前数据内容：
```json
"美国"
```

新流程数据内容：
```json
"美国"
```

数据来源或处理逻辑：douban

### `works.language`

旧的当前数据内容：
```json
"英语"
```

新流程数据内容：
```json
"英语"
```

数据来源或处理逻辑：douban

### `works.publish_company`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
null
```

数据来源或处理逻辑：baike; 来自百度百科基本信息表-发行公司

### `works.runtime_minutes`

旧的当前数据内容：
```json
128
```

新流程数据内容：
```json
128
```

数据来源或处理逻辑：douban; 单位：分钟

### `works.synopsis_text`

旧的当前数据内容：
```json
"影片聚焦迈克尔·杰克逊从杰克逊五人组主唱到全球流行天王的成名过程，既重现其早期职业生涯中的代表性舞台时刻，也尝试展示舞台光环之外的私人生命与创作压力。"
```

新流程数据内容：
```json
"影片聚焦迈克尔·杰克逊从杰克逊五人组主唱到全球流行天王的成名过程，既重现其早期职业生涯中的代表性舞台时刻，也尝试展示舞台光环之外的私人生命与创作压力。"
```

数据来源或处理逻辑：douban

### `works.synopsis_note`

旧的当前数据内容：
```json
""
```

新流程数据内容：
```json
""
```

数据来源或处理逻辑：douban

### `works.story_text`

旧的当前数据内容：
```json
"影片从迈克尔在杰克逊五人组时期切入。年少成名给他带来舞台上的光芒，也把他推入被父亲严格控制、被行业凝视的成长环境。随着组合走红，迈克尔开始展现对编曲、舞台和个人表达的强烈主导欲，他既想摆脱家族与唱片工业的安排，又必须在公众期待中不断证明自己。\n\n成年后的迈克尔逐步完成从偶像歌手到流行文化中心人物的转变。影片把大量篇幅放在《Off the Wall》《Thriller》到《Bad》时期，重现他对录音、编舞、造型和现场表演近乎偏执的要求，也展示他与家人、经纪团队、律师及合作者之间的拉扯。\n\n随着名声扩张，舞台上的掌声与私人生活的压力开始同时堆积。电影通过多场经典演出和排练段落，呈现他如何在童年缺失、自我要求与外界消费之间寻找位置，并以事业高峰阶段的大型巡演作为这一阶段人生的收束。\n\n注：当前公开版本主要覆盖杰克逊五人组出道至《Bad》全球巡演阶段，不等同于迈克尔完整一生。"
```

新流程数据内容：
```json
"影片从迈克尔在杰克逊五人组时期切入。年少成名给他带来舞台上的光芒，也把他推入被父亲严格控制、被行业凝视的成长环境。随着组合走红，迈克尔开始展现对编曲、舞台和个人表达的强烈主导欲，他既想摆脱家族与唱片工业的安排，又必须在公众期待中不断证明自己。\n\n成年后的迈克尔逐步完成从偶像歌手到流行文化中心人物的转变。影片把大量篇幅放在《Off the Wall》《Thriller》到《Bad》时期，重现他对录音、编舞、造型和现场表演近乎偏执的要求，也展示他与家人、经纪团队、律师及合作者之间的拉扯。\n\n随着名声扩张，舞台上的掌声与私人生活的压力开始同时堆积。电影通过多场经典演出和排练段落，呈现他如何在童年缺失、自我要求与外界消费之间寻找位置，并以事业高峰阶段的大型巡演作为这一阶段人生的收束。\n\n注：当前公开版本主要覆盖杰克逊五人组出道至《Bad》全球巡演阶段，不等同于迈克尔完整一生。"
```

数据来源或处理逻辑：manual; 基于豆瓣公开简介与已上映后评论信息整理，不补写未公开阶段剧情；story.note 不再进入数据库主字段

### `works.aliases_json`

旧的当前数据内容：
```json
[
  "米高积逊(港)",
  "麦可·杰克森(台)",
  "迈克尔"
]
```

新流程数据内容：
```json
[
  "米高积逊(港)",
  "麦可·杰克森(台)",
  "迈克尔"
]
```

数据来源或处理逻辑：douban

### `works.release_dates_json`

旧的当前数据内容：
```json
[
  {
    "date": "2026-04-24",
    "location": "美国/中国大陆"
  },
  {
    "date": "2026-04-22",
    "location": "中国香港"
  }
]
```

新流程数据内容：
```json
[
  {
    "date": "2026-04-24",
    "location": "美国/中国大陆"
  },
  {
    "date": "2026-04-22",
    "location": "中国香港"
  }
]
```

数据来源或处理逻辑：douban

### `works.identifiers_json`

旧的当前数据内容：
```json
{
  "douban": "35948919",
  "imdb": "tt11378946",
  "tmdb": null
}
```

新流程数据内容：
```json
{
  "douban": "35948919",
  "imdb": "tt11378946",
  "tmdb": null
}
```

数据来源或处理逻辑：doubanId:douban; imdbId:douban; tmdbId:system; 当前样板未提供可解析的 TMDB id

### `works.ratings_json`

旧的当前数据内容：
```json
{
  "aggregate": {
    "value": 7.5,
    "scale": 10
  },
  "douban": {
    "value": 7.5,
    "scale": 10
  },
  "imdb": {
    "value": null,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "PG-13"
  },
  "awards": {
    "value": "2 wins & 1 nomination"
  }
}
```

新流程数据内容：
```json
{
  "aggregate": {
    "value": 7.5,
    "scale": 10
  },
  "douban": {
    "value": 7.5,
    "scale": 10
  },
  "imdb": {
    "value": null,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "PG-13"
  },
  "awards": {
    "value": "2 wins & 1 nomination"
  }
}
```

数据来源或处理逻辑：doubanRating:douban; rated:omdb; MPAA评级; awards:omdb

### `works.links_json`

旧的当前数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/35948919/",
  "imdb": "https://www.imdb.com/title/tt11378946/",
  "tmdb": null
}
```

新流程数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/35948919/",
  "imdb": "https://www.imdb.com/title/tt11378946/",
  "tmdb": null
}
```

数据来源或处理逻辑：merged: douban(douban) + douban(imdb)

### `works.images_json`

旧的当前数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01-cn.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg",
    "poster-06.jpg",
    "poster-07.jpg",
    "poster-08.jpg",
    "poster-09.jpg",
    "poster-10.jpg",
    "poster-11.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg",
    "still-06.jpg",
    "still-07.jpg",
    "still-08.jpg",
    "still-09.jpg",
    "still-10.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 79,
  "stillsTotal": 215,
  "assetDir": "video/movie/0101000002"
}
```

新流程数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01-cn.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg",
    "poster-06.jpg",
    "poster-07.jpg",
    "poster-08.jpg",
    "poster-09.jpg",
    "poster-10.jpg",
    "poster-11.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg",
    "still-06.jpg",
    "still-07.jpg",
    "still-08.jpg",
    "still-09.jpg",
    "still-10.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 79,
  "stillsTotal": 215,
  "assetDir": "video/movie/0101000002"
}
```

数据来源或处理逻辑：poster:douban; posters:douban; postersTotal:douban; stills:douban; stillsTotal:douban; wallpapers:system

### `works.videos_json`

旧的当前数据内容：
```json
[
  {
    "title": "中国大陆预告片1：终极版 (中文字幕)",
    "duration": "01:00",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/324247/"
  },
  {
    "title": "中国大陆预告片2：定档版 (中文字幕)",
    "duration": "00:30",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/324145/"
  },
  {
    "title": "中国大陆预告片3 (中文字幕)",
    "duration": "00:15",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323960/"
  },
  {
    "title": "中国大陆预告片4 (中文字幕)",
    "duration": "02:17",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323591/"
  },
  {
    "title": "预告片5",
    "duration": "02:17",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323590/"
  }
]
```

新流程数据内容：
```json
[
  {
    "title": "中国大陆预告片1：终极版 (中文字幕)",
    "duration": "01:00",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/324247/"
  },
  {
    "title": "中国大陆预告片2：定档版 (中文字幕)",
    "duration": "00:30",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/324145/"
  },
  {
    "title": "中国大陆预告片3 (中文字幕)",
    "duration": "00:15",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323960/"
  },
  {
    "title": "中国大陆预告片4 (中文字幕)",
    "duration": "02:17",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323591/"
  },
  {
    "title": "预告片5",
    "duration": "02:17",
    "thumbnail": null,
    "url": "https://movie.douban.com/trailer/323590/"
  }
]
```

数据来源或处理逻辑：system; videos 当前沿用系统生成或空值占位

### `works.reviews_json`

旧的当前数据内容：
```json
[
  {
    "source": "豆瓣",
    "author": "Division_Bell",
    "date": "2026-04-24",
    "rating": "",
    "content": "从电影角度看，这部片子的叙事并不算成熟；但作为 Michael Jackson 的传记片，它又让人很难真的对它苛刻。制作层面足够华丽，表演与舞台还原也确实能打，可它最明显的问题，是电影语言始终没能完全承载这位巨星复杂而巨大的生命。"
  },
  {
    "source": "豆瓣",
    "author": "一资产阶级铁锅",
    "date": "2026-04-24",
    "rating": "还行",
    "content": "如果买到杜比或 IMAX 场次，这部电影在影院里听 MJ 的作品依然震撼；但作为一部传记片，它对人物与时代的处理明显失衡。老粉能从舞台重建和经典段落里获得情感回报，可一旦把它当成电影来衡量，剧情推进和人物弧光都显得不够扎实。"
  },
  {
    "source": "豆瓣",
    "author": "木木东子",
    "date": "2026-04-24",
    "rating": "较差",
    "content": "全片两小时出头却塞进了三十多首歌曲，声音系统好的影厅会让人觉得这趟票价值回一半。但也正因为音乐段落过于强势，电影本身反而暴露出结构上的单薄：它足够像一场精选演出，却还配不上\"流行音乐之王\"这样的人生体量。"
  },
  {
    "source": "豆瓣",
    "author": "团小纸",
    "date": "2026-04-23",
    "rating": "力荐",
    "content": "即使不是 MJ 的核心歌迷，也能在这部片子里重新理解他为什么会成为一代又一代偶像的偶像。那些被反复模仿的舞步、编排和表演方式，并不是天赋神话的简单复制，而是一个人把审美、训练和意志压缩到极致后留下的文化震波。"
  }
]
```

新流程数据内容：
```json
[
  {
    "author": "Division_Bell",
    "source": "豆瓣",
    "date": "2026-04-24",
    "content": "从电影角度看，这部片子的叙事并不算成熟；但作为 Michael Jackson 的传记片，它又让人很难真的对它苛刻。制作层面足够华丽，表演与舞台还原也确实能打，可它最明显的问题，是电影语言始终没能完全承载这位巨星复杂而巨大的生命。",
    "url": "https://movie.douban.com/review/17567525/",
    "title": "优秀的制作，勉强及格的MJ，不合格的电影。"
  },
  {
    "author": "一资产阶级铁锅",
    "source": "豆瓣",
    "date": "2026-04-24",
    "content": "如果买到杜比或 IMAX 场次，这部电影在影院里听 MJ 的作品依然震撼；但作为一部传记片，它对人物与时代的处理明显失衡。老粉能从舞台重建和经典段落里获得情感回报，可一旦把它当成电影来衡量，剧情推进和人物弧光都显得不够扎实。",
    "url": "https://movie.douban.com/review/17567438/",
    "title": "老粉的失望"
  },
  {
    "author": "木木东子",
    "source": "豆瓣",
    "date": "2026-04-24",
    "content": "全片两小时出头却塞进了三十多首歌曲，声音系统好的影厅会让人觉得这趟票价值回一半。但也正因为音乐段落过于强势，电影本身反而暴露出结构上的单薄：它足够像一场精选演出，却还配不上\"流行音乐之王\"这样的人生体量。",
    "url": "https://movie.douban.com/review/17566820/",
    "title": "值得去影院一听，但作为电影配不上流行音乐之王的地位"
  },
  {
    "author": "团小纸",
    "source": "豆瓣",
    "date": "2026-04-23",
    "content": "即使不是 MJ 的核心歌迷，也能在这部片子里重新理解他为什么会成为一代又一代偶像的偶像。那些被反复模仿的舞步、编排和表演方式，并不是天赋神话的简单复制，而是一个人把审美、训练和意志压缩到极致后留下的文化震波。",
    "url": "https://movie.douban.com/review/17565826/",
    "title": "终于懂了！为什么我的偶像会说MJ是他们的偶像！"
  }
]
```

数据来源或处理逻辑：douban; 豆瓣影评页精选长评前4条；已补 review.url/title，rating 不再进入数据库

### `works.soundtrack_json`

旧的当前数据内容：
```json
{
  "albums": [
    {
      "name": "Michael: Songs From The Motion Picture",
      "note": "迈克尔·杰克逊 / Michael Jackson",
      "coverImage": null,
      "releaseDate": "2026",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "I'll Be There",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Never Can Say Goodbye (Single Version)",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Who's Lovin' You",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Medley: I Want You Back / ABC / The Love You Save",
          "artist": "The Jacksons",
          "duration": null
        },
        {
          "name": "Ben (Live from the 1981 U.S. Tour)",
          "artist": "The Jacksons",
          "duration": null
        },
        {
          "name": "Don't Stop 'Til You Get Enough",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Beat It",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Thriller",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Billie Jean",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Wanna Be Startin' Somethin'",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Human Nature",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Workin' Day and Night",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Bad (2012 Remaster)",
          "artist": "迈克尔·杰克逊",
          "duration": null
        }
      ]
    }
  ]
}
```

新流程数据内容：
```json
{
  "albums": [
    {
      "name": "Michael: Songs From The Motion Picture",
      "note": "迈克尔·杰克逊 / Michael Jackson",
      "coverImage": null,
      "releaseDate": "2026",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "I'll Be There",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Never Can Say Goodbye (Single Version)",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Who's Lovin' You",
          "artist": "Jackson 5",
          "duration": null
        },
        {
          "name": "Medley: I Want You Back / ABC / The Love You Save",
          "artist": "The Jacksons",
          "duration": null
        },
        {
          "name": "Ben (Live from the 1981 U.S. Tour)",
          "artist": "The Jacksons",
          "duration": null
        },
        {
          "name": "Don't Stop 'Til You Get Enough",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Beat It",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Thriller",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Billie Jean",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Wanna Be Startin' Somethin'",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Human Nature",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Workin' Day and Night",
          "artist": "迈克尔·杰克逊",
          "duration": null
        },
        {
          "name": "Bad (2012 Remaster)",
          "artist": "迈克尔·杰克逊",
          "duration": null
        }
      ]
    }
  ]
}
```

数据来源或处理逻辑：baike; 百度百科音乐原声章节，共13首曲目；已重组为 albums[] 结构

### `works.relations_json`

旧的当前数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "title": "波西米亚狂想曲",
      "year": 2018,
      "rating": 8.6
    },
    {
      "title": "奥本海默",
      "year": 2023,
      "rating": 8.8
    },
    {
      "title": "极速车王",
      "year": 2019,
      "rating": 8.5
    },
    {
      "title": "摇滚诗人：未知的传奇",
      "year": 2024,
      "rating": 6.5
    },
    {
      "title": "倒数时刻",
      "year": 2021,
      "rating": 8.1
    },
    {
      "title": "气垫传奇",
      "year": 2023,
      "rating": 7.5
    },
    {
      "title": "猫王",
      "year": 2022,
      "rating": 6.9
    }
  ]
}
```

新流程数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "title": "波西米亚狂想曲",
      "year": 2018,
      "rating": 8.6
    },
    {
      "title": "奥本海默",
      "year": 2023,
      "rating": 8.8
    },
    {
      "title": "极速车王",
      "year": 2019,
      "rating": 8.5
    },
    {
      "title": "摇滚诗人：未知的传奇",
      "year": 2024,
      "rating": 6.5
    },
    {
      "title": "倒数时刻",
      "year": 2021,
      "rating": 8.1
    },
    {
      "title": "气垫传奇",
      "year": 2023,
      "rating": 7.5
    },
    {
      "title": "猫王",
      "year": 2022,
      "rating": 6.9
    }
  ]
}
```

数据来源或处理逻辑：series:system; 当前4条样板未录入系列关系，先保留空数组; similar:douban

### `works.quotes_json`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板未整理 quotes，先保留空数组

### `works.status`

旧的当前数据内容：
```json
"published"
```

新流程数据内容：
```json
"published"
```

数据来源或处理逻辑：system; 当前电影样板默认按 published 导入

### `works.created_at`

旧的当前数据内容：
```json
"2026-05-01"
```

新流程数据内容：
```json
"2026-05-01"
```

数据来源或处理逻辑：system; 录入时间

### `works.updated_at`

旧的当前数据内容：
```json
"2026-05-02"
```

新流程数据内容：
```json
"2026-05-02"
```

数据来源或处理逻辑：system; 最后更新时间

### `credits.director`

旧的当前数据内容：
```json
[
  {
    "name": "安东尼·福奎阿",
    "nameEn": "Antoine Fuqua",
    "avatar": "avatar-antoine-fuqua.jpg",
    "avatarSource": "wikipedia",
    "works": [
      "好家伙",
      "生死狙击",
      "伸冤人"
    ]
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "安东尼·福奎阿",
    "nameEn": "Antoine Fuqua",
    "avatar": "avatar-antoine-fuqua.jpg",
    "avatarSource": "wikipedia",
    "works": [
      "好家伙",
      "生死狙击",
      "伸冤人"
    ]
  }
]
```

数据来源或处理逻辑：douban

### `credits.writer`

旧的当前数据内容：
```json
[
  {
    "name": "约翰·洛根",
    "nameEn": "John Logan",
    "role": "编剧",
    "baike": "https://baike.baidu.com/item/约翰·洛根"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "约翰·洛根",
    "nameEn": "John Logan",
    "role": "编剧",
    "baike": "https://baike.baidu.com/item/约翰·洛根"
  }
]
```

数据来源或处理逻辑：douban

### `credits.cast`

旧的当前数据内容：
```json
[
  {
    "name": "贾法尔·杰克逊",
    "nameEn": "Jaafar Jackson",
    "role": "迈克尔·杰克逊 Michael Jackson",
    "avatar": "avatar-jaafar-jackson.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "尼娅·朗",
    "nameEn": "Nia Long",
    "role": "凯瑟琳·杰克逊 Katherine Jackson",
    "avatar": "avatar-nia-long.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "朱利亚诺·瓦尔迪",
    "nameEn": "Juliano Valdi",
    "role": "小迈克尔·杰克逊 Young Michael Jackson",
    "avatar": "",
    "avatarSource": "",
    "avatarNote": "Wikipedia无此演员页面，待补充"
  },
  {
    "name": "科尔曼·多明戈",
    "nameEn": "Colman Domingo",
    "role": "约瑟夫·杰克逊 Joseph Jackson",
    "avatar": "avatar-colman-domingo.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "迈尔斯·特勒",
    "nameEn": "Miles Teller",
    "role": "约翰·布兰卡 John Branca",
    "avatar": "avatar-miles-teller.png",
    "avatarSource": "wikipedia"
  },
  {
    "name": "劳拉·哈里尔",
    "nameEn": "Laura Harrier",
    "role": "苏珊·德·帕斯 Suzanne de Passe",
    "avatar": "avatar-laura-harrier.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "杰西卡·苏拉",
    "nameEn": "Jessica Sula",
    "role": "拉托娅·杰克逊 La Toya Jackson",
    "avatar": "avatar-jessica-sula.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "麦克·梅伊斯",
    "nameEn": "Mike Myers",
    "role": "沃特·耶特尼科夫 Walter Yetnikoff",
    "avatar": "avatar-mike-myers.jpg",
    "avatarSource": "wikipedia"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "贾法尔·杰克逊",
    "nameEn": "Jaafar Jackson",
    "role": "迈克尔·杰克逊 Michael Jackson",
    "avatar": "avatar-jaafar-jackson.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "尼娅·朗",
    "nameEn": "Nia Long",
    "role": "凯瑟琳·杰克逊 Katherine Jackson",
    "avatar": "avatar-nia-long.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "朱利亚诺·瓦尔迪",
    "nameEn": "Juliano Valdi",
    "role": "小迈克尔·杰克逊 Young Michael Jackson",
    "avatar": "",
    "avatarSource": "",
    "avatarNote": "Wikipedia无此演员页面，待补充"
  },
  {
    "name": "科尔曼·多明戈",
    "nameEn": "Colman Domingo",
    "role": "约瑟夫·杰克逊 Joseph Jackson",
    "avatar": "avatar-colman-domingo.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "迈尔斯·特勒",
    "nameEn": "Miles Teller",
    "role": "约翰·布兰卡 John Branca",
    "avatar": "avatar-miles-teller.png",
    "avatarSource": "wikipedia"
  },
  {
    "name": "劳拉·哈里尔",
    "nameEn": "Laura Harrier",
    "role": "苏珊·德·帕斯 Suzanne de Passe",
    "avatar": "avatar-laura-harrier.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "杰西卡·苏拉",
    "nameEn": "Jessica Sula",
    "role": "拉托娅·杰克逊 La Toya Jackson",
    "avatar": "avatar-jessica-sula.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "麦克·梅伊斯",
    "nameEn": "Mike Myers",
    "role": "沃特·耶特尼科夫 Walter Yetnikoff",
    "avatar": "avatar-mike-myers.jpg",
    "avatarSource": "wikipedia"
  }
]
```

数据来源或处理逻辑：douban; 主演前8位，头像待从IMDb补充

### `credits.otherCast`

旧的当前数据内容：
```json
[
  {
    "name": "凯林·多瑞尔·琼斯",
    "nameEn": "KeiLyn Durrel Jones",
    "role": "比尔·布雷 Bill Bray"
  },
  {
    "name": "肯德里克·桑普森",
    "nameEn": "Kendrick Sampson",
    "role": "昆西·琼斯 Quincy Jones"
  },
  {
    "name": "拉伦兹·泰特",
    "nameEn": "Larenz Tate",
    "role": "贝瑞·高迪 Berry Gordy"
  },
  {
    "name": "约瑟夫·戴维-琼斯",
    "nameEn": "Joseph David-Jones",
    "role": "杰基·杰克逊 Jackie Jackson"
  },
  {
    "name": "贾马尔·亨德森",
    "nameEn": "Jamal Henderson",
    "role": "杰梅因·杰克逊 Jermaine Jackson"
  },
  {
    "name": "莱恩·希尔",
    "nameEn": "Rhyan Hill",
    "role": "蒂托·杰克逊 Tito Jackson"
  },
  {
    "name": "特雷·霍顿",
    "nameEn": "Tre Horton",
    "role": "马龙·杰克逊 Marlon Jackson"
  },
  {
    "name": "卡特琳娜·格兰厄姆",
    "nameEn": "Katerina Graham",
    "role": "Diana Ross"
  },
  {
    "name": "德里克·卢克",
    "nameEn": "Derek Luke",
    "role": "Johnnie Cochran"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "凯林·多瑞尔·琼斯",
    "nameEn": "KeiLyn Durrel Jones",
    "role": "比尔·布雷 Bill Bray"
  },
  {
    "name": "肯德里克·桑普森",
    "nameEn": "Kendrick Sampson",
    "role": "昆西·琼斯 Quincy Jones"
  },
  {
    "name": "拉伦兹·泰特",
    "nameEn": "Larenz Tate",
    "role": "贝瑞·高迪 Berry Gordy"
  },
  {
    "name": "约瑟夫·戴维-琼斯",
    "nameEn": "Joseph David-Jones",
    "role": "杰基·杰克逊 Jackie Jackson"
  },
  {
    "name": "贾马尔·亨德森",
    "nameEn": "Jamal Henderson",
    "role": "杰梅因·杰克逊 Jermaine Jackson"
  },
  {
    "name": "莱恩·希尔",
    "nameEn": "Rhyan Hill",
    "role": "蒂托·杰克逊 Tito Jackson"
  },
  {
    "name": "特雷·霍顿",
    "nameEn": "Tre Horton",
    "role": "马龙·杰克逊 Marlon Jackson"
  },
  {
    "name": "卡特琳娜·格兰厄姆",
    "nameEn": "Katerina Graham",
    "role": "Diana Ross"
  },
  {
    "name": "德里克·卢克",
    "nameEn": "Derek Luke",
    "role": "Johnnie Cochran"
  }
]
```

数据来源或处理逻辑：system; otherCast 当前沿用系统生成或空值占位

### `credits.producer`

旧的当前数据内容：
```json
[
  {
    "name": "格拉汉姆·金",
    "nameEn": "Graham King",
    "role": "制片人",
    "baike": "https://baike.baidu.com/item/格拉汉姆·金"
  },
  {
    "name": "约翰·布兰卡",
    "nameEn": "John Branca",
    "role": "制片人"
  },
  {
    "name": "约翰·麦克莱恩",
    "nameEn": "John McClain",
    "role": "制片人"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "格拉汉姆·金",
    "nameEn": "Graham King",
    "role": "制片人",
    "baike": "https://baike.baidu.com/item/格拉汉姆·金"
  },
  {
    "name": "约翰·布兰卡",
    "nameEn": "John Branca",
    "role": "制片人"
  },
  {
    "name": "约翰·麦克莱恩",
    "nameEn": "John McClain",
    "role": "制片人"
  }
]
```

数据来源或处理逻辑：system; producer 当前沿用系统生成或空值占位

### `terms.genre`

旧的当前数据内容：
```json
[
  "剧情",
  "音乐",
  "传记"
]
```

新流程数据内容：
```json
[
  "剧情",
  "音乐",
  "传记"
]
```

数据来源或处理逻辑：douban

### `terms.tags`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板尚未建立标签体系，先保留空数组

### `derived.tmdbId`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
null
```

数据来源或处理逻辑：system; 当前样板未提供可解析的 TMDB id

## 0101000003 阿甘正传

### `works.id`

旧的当前数据内容：
```json
"0101000003"
```

新流程数据内容：
```json
"0101000003"
```

数据来源或处理逻辑：system; 系统自动生成，递增序号

### `works.module`

旧的当前数据内容：
```json
"video"
```

新流程数据内容：
```json
"video"
```

数据来源或处理逻辑：system; 影视模块

### `works.submodule`

旧的当前数据内容：
```json
"movie"
```

新流程数据内容：
```json
"movie"
```

数据来源或处理逻辑：system; 电影子模块

### `works.schema_type`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"live_action_movie"
```

数据来源或处理逻辑：system; 电影样板当前固定写入 live_action_movie

### `works.title`

旧的当前数据内容：
```json
"阿甘正传"
```

新流程数据内容：
```json
"阿甘正传"
```

数据来源或处理逻辑：baike; 百度百科词条标题

### `works.original_title`

旧的当前数据内容：
```json
"Forrest Gump"
```

新流程数据内容：
```json
"Forrest Gump"
```

数据来源或处理逻辑：omdb

### `works.year`

旧的当前数据内容：
```json
1994
```

新流程数据内容：
```json
1994
```

数据来源或处理逻辑：omdb

### `works.country`

旧的当前数据内容：
```json
"美国"
```

新流程数据内容：
```json
"美国"
```

数据来源或处理逻辑：baike

### `works.language`

旧的当前数据内容：
```json
"英语"
```

新流程数据内容：
```json
"英语"
```

数据来源或处理逻辑：baike

### `works.publish_company`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"The Tisch Company"
```

数据来源或处理逻辑：wikipedia; 来自英文维基 infobox Production company

### `works.runtime_minutes`

旧的当前数据内容：
```json
142
```

新流程数据内容：
```json
142
```

数据来源或处理逻辑：baike; 单位：分钟

### `works.synopsis_text`

旧的当前数据内容：
```json
"智商不高却心地纯粹的阿甘，在母亲的教导和珍妮的陪伴中一路奔跑着进入大学、军队与商业世界，意外见证了美国数十年社会变迁。\n\n他始终用近乎天真的执着去爱人、做事，也在跌宕人生里把幸运、善良与失去一并活成了传奇。"
```

新流程数据内容：
```json
"智商不高却心地纯粹的阿甘，在母亲的教导和珍妮的陪伴中一路奔跑着进入大学、军队与商业世界，意外见证了美国数十年社会变迁。\n\n他始终用近乎天真的执着去爱人、做事，也在跌宕人生里把幸运、善良与失去一并活成了传奇。"
```

数据来源或处理逻辑：baike; 由百度百科长剧情压缩整理为列表页短简介

### `works.synopsis_note`

旧的当前数据内容：
```json
""
```

新流程数据内容：
```json
""
```

数据来源或处理逻辑：baike; 由百度百科长剧情压缩整理为列表页短简介

### `works.story_text`

旧的当前数据内容：
```json
"阿甘出生在阿拉巴马州，智商只有 75，却在母亲坚持下进入普通学校。童年时期，他为了躲避欺负学会奔跑，也在珍妮那句\"跑，阿甘，跑\"的呼喊里找到面对世界的方式。凭借惊人的耐力，他从被嘲笑的孩子一路跑进大学橄榄球赛场，成了校队明星，还因此见到了肯尼迪总统。\n\n大学毕业后，阿甘应征入伍，被派往越南。在那里，他结识了热衷捕虾的布巴与性格强硬的丹中尉。战争改变了他们的命运：布巴阵亡，丹失去双腿，而阿甘因为救人立功，再度以\"英雄\"身份被国家看见。此后他又阴差阳错加入乒乓球队、参与中美交流、被卷入水门事件等历史瞬间，以几乎不带功利心的姿态穿行在美国几十年社会巨变之间。\n\n阿甘始终放不下的人是珍妮。她从小就是唯一愿意坐到他身边的人，却在成长中不断逃离家乡、逃离阿甘，也逃离自己。她经历创伤、漂泊、药物和失败，始终难以相信自己值得被爱；阿甘却无论她在何处、变成什么样子，都用最笨拙也最坚定的方式等着她回来。\n\n为了完成和布巴的约定，阿甘退伍后买下捕虾船，在丹中尉帮助下建立了布巴甘公司，意外成为富翁。母亲去世后，珍妮再次短暂回到他身边，又在与他共度一夜后悄然离开。失落的阿甘开始了一场横跨全美的长跑，把自己的茫然、哀伤与执念都交给漫长公路，也再次让自己成为媒体追逐的传奇人物。\n\n直到收到珍妮来信，阿甘才停下脚步去见她，并第一次知道自己有个儿子。此时珍妮身患重病，终于决定和阿甘一起回家生活。两人结婚后不久，珍妮离世，阿甘独自承担起父亲的责任。影片最终回到公交站与校车站：阿甘把儿子送去上学，看着那片羽毛再次随风飘远，也回望了自己既被命运推动、又始终真诚向前的一生。"
```

新流程数据内容：
```json
"阿甘出生在阿拉巴马州，智商只有 75，却在母亲坚持下进入普通学校。童年时期，他为了躲避欺负学会奔跑，也在珍妮那句\"跑，阿甘，跑\"的呼喊里找到面对世界的方式。凭借惊人的耐力，他从被嘲笑的孩子一路跑进大学橄榄球赛场，成了校队明星，还因此见到了肯尼迪总统。\n\n大学毕业后，阿甘应征入伍，被派往越南。在那里，他结识了热衷捕虾的布巴与性格强硬的丹中尉。战争改变了他们的命运：布巴阵亡，丹失去双腿，而阿甘因为救人立功，再度以\"英雄\"身份被国家看见。此后他又阴差阳错加入乒乓球队、参与中美交流、被卷入水门事件等历史瞬间，以几乎不带功利心的姿态穿行在美国几十年社会巨变之间。\n\n阿甘始终放不下的人是珍妮。她从小就是唯一愿意坐到他身边的人，却在成长中不断逃离家乡、逃离阿甘，也逃离自己。她经历创伤、漂泊、药物和失败，始终难以相信自己值得被爱；阿甘却无论她在何处、变成什么样子，都用最笨拙也最坚定的方式等着她回来。\n\n为了完成和布巴的约定，阿甘退伍后买下捕虾船，在丹中尉帮助下建立了布巴甘公司，意外成为富翁。母亲去世后，珍妮再次短暂回到他身边，又在与他共度一夜后悄然离开。失落的阿甘开始了一场横跨全美的长跑，把自己的茫然、哀伤与执念都交给漫长公路，也再次让自己成为媒体追逐的传奇人物。\n\n直到收到珍妮来信，阿甘才停下脚步去见她，并第一次知道自己有个儿子。此时珍妮身患重病，终于决定和阿甘一起回家生活。两人结婚后不久，珍妮离世，阿甘独自承担起父亲的责任。影片最终回到公交站与校车站：阿甘把儿子送去上学，看着那片羽毛再次随风飘远，也回望了自己既被命运推动、又始终真诚向前的一生。"
```

数据来源或处理逻辑：baike; 基于百度百科剧情介绍章节整理；story.note 不再进入数据库主字段

### `works.aliases_json`

旧的当前数据内容：
```json
[
  "福雷斯特·冈普"
]
```

新流程数据内容：
```json
[
  "福雷斯特·冈普"
]
```

数据来源或处理逻辑：baike

### `works.release_dates_json`

旧的当前数据内容：
```json
[
  {
    "date": "1994-07-06",
    "location": "美国"
  },
  {
    "date": "1994-10-07",
    "location": "英国"
  },
  {
    "date": "1994-12-15",
    "location": "中国香港"
  }
]
```

新流程数据内容：
```json
[
  {
    "date": "1994-07-06",
    "location": "美国"
  },
  {
    "date": "1994-10-07",
    "location": "英国"
  },
  {
    "date": "1994-12-15",
    "location": "中国香港"
  }
]
```

数据来源或处理逻辑：baike; 百度百科上映信息表

### `works.identifiers_json`

旧的当前数据内容：
```json
{
  "douban": "1292720",
  "imdb": "tt0109830",
  "tmdb": null
}
```

新流程数据内容：
```json
{
  "douban": "1292720",
  "imdb": "tt0109830",
  "tmdb": "13"
}
```

数据来源或处理逻辑：doubanId:known; 已知豆瓣ID（经典电影）; imdbId:omdb; tmdbId:derived; 从 links.tmdb URL 解析出 TMDB movie id

### `works.ratings_json`

旧的当前数据内容：
```json
{
  "aggregate": {
    "value": 9.2,
    "scale": 10
  },
  "douban": {
    "value": 9.5,
    "scale": 10
  },
  "imdb": {
    "value": 8.8,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "PG-13"
  },
  "awards": {
    "value": "Won 6 Oscars. 51 wins & 74 nominations total"
  }
}
```

新流程数据内容：
```json
{
  "aggregate": {
    "value": 9.2,
    "scale": 10
  },
  "douban": {
    "value": 9.5,
    "scale": 10
  },
  "imdb": {
    "value": 8.8,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "PG-13"
  },
  "awards": {
    "value": "Won 6 Oscars. 51 wins & 74 nominations total"
  }
}
```

数据来源或处理逻辑：doubanRating:baike; 百度百科大众评分表; imdbRating:omdb; rated:omdb; MPAA评级; awards:omdb; 获奖信息

### `works.links_json`

旧的当前数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1292720/",
  "imdb": "https://www.imdb.com/title/tt0109830/",
  "tmdb": "https://www.themoviedb.org/movie/13"
}
```

新流程数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1292720/",
  "imdb": "https://www.imdb.com/title/tt0109830/",
  "tmdb": "https://www.themoviedb.org/movie/13"
}
```

数据来源或处理逻辑：merged: known(douban) + omdb(imdb)

### `works.images_json`

旧的当前数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.jpg",
    "poster-02.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg",
    "poster-06.jpg",
    "poster-07.jpg",
    "poster-08.jpg",
    "poster-09.jpg",
    "poster-10.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg",
    "still-06.jpg",
    "still-07.jpg",
    "still-08.jpg",
    "still-09.jpg",
    "still-10.jpg",
    "still-11.jpg",
    "still-12.jpg",
    "still-13.jpg",
    "still-14.jpg",
    "still-15.jpg",
    "still-16.jpg",
    "still-17.jpg",
    "still-18.jpg",
    "still-19.jpg",
    "still-20.jpg",
    "still-21.jpg",
    "still-22.jpg",
    "still-23.jpg",
    "still-24.jpg",
    "still-25.jpg",
    "still-26.jpg",
    "still-27.jpg",
    "still-28.jpg",
    "still-29.jpg",
    "still-30.jpg",
    "still-31.jpg",
    "still-32.jpg",
    "still-33.jpg",
    "still-34.jpg",
    "still-35.jpg",
    "still-36.jpg",
    "still-37.jpg",
    "still-38.jpg",
    "still-39.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 10,
  "stillsTotal": 39,
  "assetDir": "video/movie/0101000003"
}
```

新流程数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.jpg",
    "poster-02.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg",
    "poster-06.jpg",
    "poster-07.jpg",
    "poster-08.jpg",
    "poster-09.jpg",
    "poster-10.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg",
    "still-06.jpg",
    "still-07.jpg",
    "still-08.jpg",
    "still-09.jpg",
    "still-10.jpg",
    "still-11.jpg",
    "still-12.jpg",
    "still-13.jpg",
    "still-14.jpg",
    "still-15.jpg",
    "still-16.jpg",
    "still-17.jpg",
    "still-18.jpg",
    "still-19.jpg",
    "still-20.jpg",
    "still-21.jpg",
    "still-22.jpg",
    "still-23.jpg",
    "still-24.jpg",
    "still-25.jpg",
    "still-26.jpg",
    "still-27.jpg",
    "still-28.jpg",
    "still-29.jpg",
    "still-30.jpg",
    "still-31.jpg",
    "still-32.jpg",
    "still-33.jpg",
    "still-34.jpg",
    "still-35.jpg",
    "still-36.jpg",
    "still-37.jpg",
    "still-38.jpg",
    "still-39.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 10,
  "stillsTotal": 39,
  "assetDir": "video/movie/0101000003"
}
```

数据来源或处理逻辑：poster:wikipedia; posters:tmdb; postersTotal:system; stills:tmdb; stillsTotal:tmdb; wallpapers:system

### `works.videos_json`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; videos 当前为空数组，保留为空并等待后续补录

### `works.reviews_json`

旧的当前数据内容：
```json
[
  {
    "source": "豆瓣",
    "author": "kino",
    "date": "2008-07-12",
    "rating": "力荐",
    "content": "一个南阿拉巴马州的傻子阿甘，一辈子喜欢的女人就是珍妮。从小到大，他对她的感情几乎没有变过：不管她做什么，不管她变得多狼狈、不安或遥远，阿甘都始终在原地等她回来。电影最动人的，并不是传奇经历，而是这种近乎不设条件的爱。"
  },
  {
    "source": "豆瓣",
    "author": "山河大地",
    "date": "2005-06-13",
    "rating": "力荐",
    "content": "很多人说阿甘只是运气太好，但如果你认真听他在长椅上讲述自己的一生，就会发现这不是一个人在炫耀好运，而是在回答\"人为什么活着\"。他并不聪明，却比多数人更少自我消耗，所以也更接近生命最朴素的力量。"
  },
  {
    "source": "豆瓣",
    "author": "蹊默",
    "date": "2005-11-25",
    "rating": "力荐",
    "content": "片头片尾那片随风飘动的羽毛，不只是形式上的呼应，更像是对人生的概括：每个人都像羽毛一样被时代气流托举、吹落、偏转，却又在落地之前经历了只属于自己的轨迹。阿甘的一生因此既像偶然，也像命运。"
  },
  {
    "source": "豆瓣",
    "author": "楚荆",
    "date": "2007-10-07",
    "rating": "力荐",
    "content": "珍妮总说阿甘不懂什么是爱，可恰恰可能是他最懂得爱。他爱母亲、爱朋友、爱布巴、爱丹中尉，也爱珍妮；这些感情没有技巧，没有算计，却因为始终如一而显得格外珍贵。与其说阿甘幸运，不如说他在复杂世界里保住了最难得的真诚。"
  }
]
```

新流程数据内容：
```json
[
  {
    "author": "kino",
    "source": "豆瓣",
    "date": "2008-07-12",
    "content": "一个南阿拉巴马州的傻子阿甘，一辈子喜欢的女人就是珍妮。从小到大，他对她的感情几乎没有变过：不管她做什么，不管她变得多狼狈、不安或遥远，阿甘都始终在原地等她回来。电影最动人的，并不是传奇经历，而是这种近乎不设条件的爱。",
    "url": "https://movie.douban.com/review/1436379/",
    "title": "阿甘的爱情"
  },
  {
    "author": "山河大地",
    "source": "豆瓣",
    "date": "2005-06-13",
    "content": "很多人说阿甘只是运气太好，但如果你认真听他在长椅上讲述自己的一生，就会发现这不是一个人在炫耀好运，而是在回答\"人为什么活着\"。他并不聪明，却比多数人更少自我消耗，所以也更接近生命最朴素的力量。",
    "url": "https://movie.douban.com/review/1000747/",
    "title": "飘飞的羽毛"
  },
  {
    "author": "蹊默",
    "source": "豆瓣",
    "date": "2005-11-25",
    "content": "片头片尾那片随风飘动的羽毛，不只是形式上的呼应，更像是对人生的概括：每个人都像羽毛一样被时代气流托举、吹落、偏转，却又在落地之前经历了只属于自己的轨迹。阿甘的一生因此既像偶然，也像命运。",
    "url": "https://movie.douban.com/review/1012226/",
    "title": "一羽人生"
  },
  {
    "author": "楚荆",
    "source": "豆瓣",
    "date": "2007-10-07",
    "content": "珍妮总说阿甘不懂什么是爱，可恰恰可能是他最懂得爱。他爱母亲、爱朋友、爱布巴、爱丹中尉，也爱珍妮；这些感情没有技巧，没有算计，却因为始终如一而显得格外珍贵。与其说阿甘幸运，不如说他在复杂世界里保住了最难得的真诚。",
    "url": "https://movie.douban.com/review/2803231/",
    "title": "每个人心中都有自己的阿甘"
  }
]
```

数据来源或处理逻辑：douban; 豆瓣影评页精选长评前4条；已补 review.url/title，rating 不再进入数据库

### `works.soundtrack_json`

旧的当前数据内容：
```json
{
  "albums": [
    {
      "name": "Forrest Gump: The Soundtrack",
      "note": "亚伦·史维斯查 / Alan Silvestri",
      "coverImage": null,
      "releaseDate": "1994",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "Hound Dog",
          "artist": "Elvis Presley",
          "duration": null
        },
        {
          "name": "Rebel Rouser",
          "artist": "Duane Eddy",
          "duration": null
        },
        {
          "name": "(I Don't Know Why) But I Do",
          "artist": "Clarence 'Frogman' Henry",
          "duration": null
        },
        {
          "name": "Walk Right In",
          "artist": "The Rooftop Singers",
          "duration": null
        },
        {
          "name": "Land of 1000 Dances",
          "artist": "Wilson Pickett",
          "duration": null
        },
        {
          "name": "Blowin' in the Wind",
          "artist": "Bob Dylan",
          "duration": null
        },
        {
          "name": "Fortunate Son",
          "artist": "Creedence Clearwater Revival",
          "duration": null
        },
        {
          "name": "I Can't Help Myself (Sugar Pie Honey Bunch)",
          "artist": "Four Tops",
          "duration": null
        },
        {
          "name": "Respect",
          "artist": "Aretha Franklin",
          "duration": null
        },
        {
          "name": "Raindrops Keep Falling on My Head",
          "artist": "B.J. Thomas",
          "duration": null
        },
        {
          "name": "Sloop John B",
          "artist": "The Beach Boys",
          "duration": null
        },
        {
          "name": "California Dreamin'",
          "artist": "The Mamas & The Papas",
          "duration": null
        },
        {
          "name": "For What It's Worth",
          "artist": "Buffalo Springfield",
          "duration": null
        },
        {
          "name": "What the World Needs Now Is Love",
          "artist": "Jackie DeShannon",
          "duration": null
        },
        {
          "name": "Break On Through (To the Other Side)",
          "artist": "The Doors",
          "duration": null
        },
        {
          "name": "Mrs. Robinson",
          "artist": "Simon & Garfunkel",
          "duration": null
        },
        {
          "name": "Volunteers",
          "artist": "Jefferson Airplane",
          "duration": null
        },
        {
          "name": "Let's Get Together",
          "artist": "Chet Powers",
          "duration": null
        },
        {
          "name": "San Francisco (Be Sure to Wear Flowers in Your Hair)",
          "artist": "Scott McKenzie",
          "duration": null
        },
        {
          "name": "Turn! Turn! Turn! (To Everything There Is a Season)",
          "artist": "The Byrds",
          "duration": null
        },
        {
          "name": "Medley: Aquarius/Let the Sunshine In",
          "artist": "The 5th Dimension",
          "duration": null
        },
        {
          "name": "Everybody's Talkin'",
          "artist": "Harry Nilsson",
          "duration": null
        },
        {
          "name": "Joy to the World",
          "artist": "Three Dog Night",
          "duration": null
        },
        {
          "name": "Stoned Love",
          "artist": "The Supremes",
          "duration": null
        },
        {
          "name": "Rainy Day Women #12 & 35",
          "artist": "Bob Dylan",
          "duration": null
        },
        {
          "name": "Mr. President (Have Pity on the Working Man)",
          "artist": "Randy Newman",
          "duration": null
        },
        {
          "name": "Sweet Home Alabama",
          "artist": "Lynyrd Skynyrd",
          "duration": null
        },
        {
          "name": "It Keeps You Runnin'",
          "artist": "The Doobie Brothers",
          "duration": null
        },
        {
          "name": "I've Got to Use My Imagination",
          "artist": "Gladys Knight & The Pips",
          "duration": null
        },
        {
          "name": "On the Road Again",
          "artist": "Willie Nelson",
          "duration": null
        },
        {
          "name": "Against the Wind",
          "artist": "Bob Seger",
          "duration": null
        },
        {
          "name": "Forrest Gump Suite",
          "artist": "Alan Silvestri",
          "duration": null
        }
      ]
    }
  ]
}
```

新流程数据内容：
```json
{
  "albums": [
    {
      "name": "Forrest Gump: The Soundtrack",
      "note": "亚伦·史维斯查 / Alan Silvestri",
      "coverImage": null,
      "releaseDate": "1994",
      "type": "soundtrack",
      "tracks": [
        {
          "name": "Hound Dog",
          "artist": "Elvis Presley",
          "duration": null
        },
        {
          "name": "Rebel Rouser",
          "artist": "Duane Eddy",
          "duration": null
        },
        {
          "name": "(I Don't Know Why) But I Do",
          "artist": "Clarence 'Frogman' Henry",
          "duration": null
        },
        {
          "name": "Walk Right In",
          "artist": "The Rooftop Singers",
          "duration": null
        },
        {
          "name": "Land of 1000 Dances",
          "artist": "Wilson Pickett",
          "duration": null
        },
        {
          "name": "Blowin' in the Wind",
          "artist": "Bob Dylan",
          "duration": null
        },
        {
          "name": "Fortunate Son",
          "artist": "Creedence Clearwater Revival",
          "duration": null
        },
        {
          "name": "I Can't Help Myself (Sugar Pie Honey Bunch)",
          "artist": "Four Tops",
          "duration": null
        },
        {
          "name": "Respect",
          "artist": "Aretha Franklin",
          "duration": null
        },
        {
          "name": "Raindrops Keep Falling on My Head",
          "artist": "B.J. Thomas",
          "duration": null
        },
        {
          "name": "Sloop John B",
          "artist": "The Beach Boys",
          "duration": null
        },
        {
          "name": "California Dreamin'",
          "artist": "The Mamas & The Papas",
          "duration": null
        },
        {
          "name": "For What It's Worth",
          "artist": "Buffalo Springfield",
          "duration": null
        },
        {
          "name": "What the World Needs Now Is Love",
          "artist": "Jackie DeShannon",
          "duration": null
        },
        {
          "name": "Break On Through (To the Other Side)",
          "artist": "The Doors",
          "duration": null
        },
        {
          "name": "Mrs. Robinson",
          "artist": "Simon & Garfunkel",
          "duration": null
        },
        {
          "name": "Volunteers",
          "artist": "Jefferson Airplane",
          "duration": null
        },
        {
          "name": "Let's Get Together",
          "artist": "Chet Powers",
          "duration": null
        },
        {
          "name": "San Francisco (Be Sure to Wear Flowers in Your Hair)",
          "artist": "Scott McKenzie",
          "duration": null
        },
        {
          "name": "Turn! Turn! Turn! (To Everything There Is a Season)",
          "artist": "The Byrds",
          "duration": null
        },
        {
          "name": "Medley: Aquarius/Let the Sunshine In",
          "artist": "The 5th Dimension",
          "duration": null
        },
        {
          "name": "Everybody's Talkin'",
          "artist": "Harry Nilsson",
          "duration": null
        },
        {
          "name": "Joy to the World",
          "artist": "Three Dog Night",
          "duration": null
        },
        {
          "name": "Stoned Love",
          "artist": "The Supremes",
          "duration": null
        },
        {
          "name": "Rainy Day Women #12 & 35",
          "artist": "Bob Dylan",
          "duration": null
        },
        {
          "name": "Mr. President (Have Pity on the Working Man)",
          "artist": "Randy Newman",
          "duration": null
        },
        {
          "name": "Sweet Home Alabama",
          "artist": "Lynyrd Skynyrd",
          "duration": null
        },
        {
          "name": "It Keeps You Runnin'",
          "artist": "The Doobie Brothers",
          "duration": null
        },
        {
          "name": "I've Got to Use My Imagination",
          "artist": "Gladys Knight & The Pips",
          "duration": null
        },
        {
          "name": "On the Road Again",
          "artist": "Willie Nelson",
          "duration": null
        },
        {
          "name": "Against the Wind",
          "artist": "Bob Seger",
          "duration": null
        },
        {
          "name": "Forrest Gump Suite",
          "artist": "Alan Silvestri",
          "duration": null
        }
      ]
    }
  ]
}
```

数据来源或处理逻辑：baike; 百度百科音乐原声章节，共32首曲目；已重组为 albums[] 结构

### `works.relations_json`

旧的当前数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "id": "0101000001",
      "title": "肖申克的救赎",
      "year": 1994,
      "rating": 9.7
    },
    {
      "title": "这个杀手不太冷",
      "year": 1994,
      "rating": 9.4
    },
    {
      "title": "美丽人生",
      "year": 1997,
      "rating": 9.5
    },
    {
      "title": "泰坦尼克号",
      "year": 1997,
      "rating": 9.5
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.3
    }
  ]
}
```

新流程数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "id": "0101000001",
      "title": "肖申克的救赎",
      "year": 1994,
      "rating": 9.7
    },
    {
      "title": "这个杀手不太冷",
      "year": 1994,
      "rating": 9.4
    },
    {
      "title": "美丽人生",
      "year": 1997,
      "rating": 9.5
    },
    {
      "title": "泰坦尼克号",
      "year": 1997,
      "rating": 9.5
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.3
    }
  ]
}
```

数据来源或处理逻辑：series:system; 当前4条样板未录入系列关系，先保留空数组; similar:manual; 手动补充经典同类型电影

### `works.quotes_json`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板未整理 quotes，先保留空数组

### `works.status`

旧的当前数据内容：
```json
"published"
```

新流程数据内容：
```json
"published"
```

数据来源或处理逻辑：system; 当前电影样板默认按 published 导入

### `works.created_at`

旧的当前数据内容：
```json
"2026-05-01"
```

新流程数据内容：
```json
"2026-05-01"
```

数据来源或处理逻辑：system; 录入时间

### `works.updated_at`

旧的当前数据内容：
```json
"2026-05-02"
```

新流程数据内容：
```json
"2026-05-02"
```

数据来源或处理逻辑：system; 最后更新时间

### `credits.director`

旧的当前数据内容：
```json
[
  {
    "name": "罗伯特·泽米吉斯",
    "nameEn": "Robert Zemeckis",
    "avatar": "avatar-robert-zemeckis.jpg",
    "avatarSource": "wikipedia",
    "works": [
      "回到未来",
      "荒岛余生",
      "云中行走"
    ]
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "罗伯特·泽米吉斯",
    "nameEn": "Robert Zemeckis",
    "avatar": "avatar-robert-zemeckis.jpg",
    "avatarSource": "wikipedia",
    "works": [
      "回到未来",
      "荒岛余生",
      "云中行走"
    ]
  }
]
```

数据来源或处理逻辑：merged: baike(name) + omdb(nameEn) + wikipedia(avatar)

### `credits.writer`

旧的当前数据内容：
```json
[
  {
    "name": "艾瑞克·罗斯",
    "nameEn": "Eric Roth",
    "role": "编剧"
  },
  {
    "name": "温斯顿·格鲁姆",
    "nameEn": "Winston Groom",
    "role": "原著"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "艾瑞克·罗斯",
    "nameEn": "Eric Roth",
    "role": "编剧"
  },
  {
    "name": "温斯顿·格鲁姆",
    "nameEn": "Winston Groom",
    "role": "原著"
  }
]
```

数据来源或处理逻辑：merged: baike(name/role) + omdb(nameEn)

### `credits.cast`

旧的当前数据内容：
```json
[
  {
    "name": "汤姆·汉克斯",
    "nameEn": "Tom Hanks",
    "role": "阿甘 Forrest Gump",
    "avatar": "avatar-tom-hanks.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "罗宾·怀特",
    "nameEn": "Robin Wright",
    "role": "珍妮·库伦 Jenny Curran",
    "avatar": "avatar-robin-wright.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "加里·西尼斯",
    "nameEn": "Gary Sinise",
    "role": "邓·泰勒 Dan Taylor",
    "avatar": "avatar-gary-sinise.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "麦凯尔泰·威廉逊",
    "nameEn": "Mykelti Williamson",
    "role": "布巴·布鲁 Bubba Blue",
    "avatar": "avatar-mykelti-williamson.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "莎莉·菲尔德",
    "nameEn": "Sally Field",
    "role": "甘普太太 Mrs. Gump",
    "avatar": "avatar-sally-field.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "海利·乔·奥斯蒙",
    "nameEn": "Haley Joel Osment",
    "role": "小阿甘 Forrest Gump Jr.",
    "avatar": "avatar-haley-joel-osment.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "迈克尔·康纳·汉弗莱斯",
    "nameEn": "Michael Conner Humphreys",
    "role": "年幼阿甘 Young Forrest",
    "avatar": "avatar-michael-conner-humphreys.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "汉娜·豪尔",
    "nameEn": "Hanna R. Hall",
    "role": "年幼珍妮 Young Jenny",
    "avatar": "",
    "avatarSource": "",
    "avatarNote": "Wikipedia无头像"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "汤姆·汉克斯",
    "nameEn": "Tom Hanks",
    "role": "阿甘 Forrest Gump",
    "avatar": "avatar-tom-hanks.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "罗宾·怀特",
    "nameEn": "Robin Wright",
    "role": "珍妮·库伦 Jenny Curran",
    "avatar": "avatar-robin-wright.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "加里·西尼斯",
    "nameEn": "Gary Sinise",
    "role": "邓·泰勒 Dan Taylor",
    "avatar": "avatar-gary-sinise.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "麦凯尔泰·威廉逊",
    "nameEn": "Mykelti Williamson",
    "role": "布巴·布鲁 Bubba Blue",
    "avatar": "avatar-mykelti-williamson.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "莎莉·菲尔德",
    "nameEn": "Sally Field",
    "role": "甘普太太 Mrs. Gump",
    "avatar": "avatar-sally-field.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "海利·乔·奥斯蒙",
    "nameEn": "Haley Joel Osment",
    "role": "小阿甘 Forrest Gump Jr.",
    "avatar": "avatar-haley-joel-osment.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "迈克尔·康纳·汉弗莱斯",
    "nameEn": "Michael Conner Humphreys",
    "role": "年幼阿甘 Young Forrest",
    "avatar": "avatar-michael-conner-humphreys.jpg",
    "avatarSource": "wikipedia"
  },
  {
    "name": "汉娜·豪尔",
    "nameEn": "Hanna R. Hall",
    "role": "年幼珍妮 Young Jenny",
    "avatar": "",
    "avatarSource": "",
    "avatarNote": "Wikipedia无头像"
  }
]
```

数据来源或处理逻辑：merged: baike(name/role) + omdb(nameEn) + wikipedia(avatar); 主演前8位，部分头像待补充

### `credits.otherCast`

旧的当前数据内容：
```json
[
  {
    "name": "库尔特·拉塞尔",
    "nameEn": "Kurt Russell",
    "role": "艾维斯·普斯里（配音）"
  },
  {
    "name": "彼得·多布森",
    "nameEn": "Peter Dobson",
    "role": "猫王"
  },
  {
    "name": "索尼·施罗耶",
    "nameEn": "Sonny Shroyer",
    "role": "布莱恩特教练"
  },
  {
    "name": "理查德·戴萨特",
    "nameEn": "Richard D'Alessandro",
    "role": "约翰·列侬"
  },
  {
    "name": "杰弗里·布莱克",
    "nameEn": "Geoffrey Blake",
    "role": "长腿漂流者"
  },
  {
    "name": "丹尼尔C.斯崔普",
    "nameEn": "Daniel C. Striepeke",
    "role": "越战老兵"
  },
  {
    "name": "大卫·布里斯宾",
    "nameEn": "David Brisbin",
    "role": "巴士司机"
  },
  {
    "name": "迪克·史泰尔斯",
    "nameEn": "Dick Stahl",
    "role": "巴士司机"
  },
  {
    "name": "山姆·安德森",
    "nameEn": "Sam Anderson",
    "role": "历史老师"
  },
  {
    "name": "伊丽莎白·汉克斯",
    "nameEn": "Elizabeth Hanks",
    "role": "巴士上的女孩"
  },
  {
    "name": "海利·乔·奥斯蒙",
    "nameEn": "Haley Joel Osment",
    "role": "小阿甘（公交站台）"
  },
  {
    "name": "迈克尔·伯吉斯",
    "nameEn": "Michael Burgess",
    "role": "越战士兵"
  },
  {
    "name": "特里·温格特",
    "nameEn": "Terry Wright",
    "role": "越战士兵"
  },
  {
    "name": "马修·麦克纳",
    "nameEn": "Matthew MacNabb",
    "role": "越战士兵"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "库尔特·拉塞尔",
    "nameEn": "Kurt Russell",
    "role": "艾维斯·普斯里（配音）"
  },
  {
    "name": "彼得·多布森",
    "nameEn": "Peter Dobson",
    "role": "猫王"
  },
  {
    "name": "索尼·施罗耶",
    "nameEn": "Sonny Shroyer",
    "role": "布莱恩特教练"
  },
  {
    "name": "理查德·戴萨特",
    "nameEn": "Richard D'Alessandro",
    "role": "约翰·列侬"
  },
  {
    "name": "杰弗里·布莱克",
    "nameEn": "Geoffrey Blake",
    "role": "长腿漂流者"
  },
  {
    "name": "丹尼尔C.斯崔普",
    "nameEn": "Daniel C. Striepeke",
    "role": "越战老兵"
  },
  {
    "name": "大卫·布里斯宾",
    "nameEn": "David Brisbin",
    "role": "巴士司机"
  },
  {
    "name": "迪克·史泰尔斯",
    "nameEn": "Dick Stahl",
    "role": "巴士司机"
  },
  {
    "name": "山姆·安德森",
    "nameEn": "Sam Anderson",
    "role": "历史老师"
  },
  {
    "name": "伊丽莎白·汉克斯",
    "nameEn": "Elizabeth Hanks",
    "role": "巴士上的女孩"
  },
  {
    "name": "海利·乔·奥斯蒙",
    "nameEn": "Haley Joel Osment",
    "role": "小阿甘（公交站台）"
  },
  {
    "name": "迈克尔·伯吉斯",
    "nameEn": "Michael Burgess",
    "role": "越战士兵"
  },
  {
    "name": "特里·温格特",
    "nameEn": "Terry Wright",
    "role": "越战士兵"
  },
  {
    "name": "马修·麦克纳",
    "nameEn": "Matthew MacNabb",
    "role": "越战士兵"
  }
]
```

数据来源或处理逻辑：system; otherCast 当前沿用系统生成或空值占位

### `credits.producer`

旧的当前数据内容：
```json
[
  {
    "name": "温迪·芬erman",
    "nameEn": "Wendy Finerman",
    "role": "制片人"
  },
  {
    "name": "斯蒂夫·斯塔基",
    "nameEn": "Steve Starkey",
    "role": "制片人"
  },
  {
    "name": "史蒂夫·蒂施",
    "nameEn": "Steve Tisch",
    "role": "制片人"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "温迪·芬erman",
    "nameEn": "Wendy Finerman",
    "role": "制片人"
  },
  {
    "name": "斯蒂夫·斯塔基",
    "nameEn": "Steve Starkey",
    "role": "制片人"
  },
  {
    "name": "史蒂夫·蒂施",
    "nameEn": "Steve Tisch",
    "role": "制片人"
  }
]
```

数据来源或处理逻辑：system; producer 当前沿用系统生成或空值占位

### `terms.genre`

旧的当前数据内容：
```json
[
  "剧情",
  "爱情"
]
```

新流程数据内容：
```json
[
  "剧情",
  "爱情"
]
```

数据来源或处理逻辑：baike; 百度百科类型

### `terms.tags`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板尚未建立标签体系，先保留空数组

### `derived.tmdbId`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"13"
```

数据来源或处理逻辑：derived; 从 links.tmdb URL 解析出 TMDB movie id

## 0101000004 霸王别姬

### `works.id`

旧的当前数据内容：
```json
"0101000004"
```

新流程数据内容：
```json
"0101000004"
```

数据来源或处理逻辑：system; 系统自动生成，递增序号

### `works.module`

旧的当前数据内容：
```json
"video"
```

新流程数据内容：
```json
"video"
```

数据来源或处理逻辑：system; 影视模块

### `works.submodule`

旧的当前数据内容：
```json
"movie"
```

新流程数据内容：
```json
"movie"
```

数据来源或处理逻辑：system; 电影子模块

### `works.schema_type`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"live_action_movie"
```

数据来源或处理逻辑：system; 电影样板当前固定写入 live_action_movie

### `works.title`

旧的当前数据内容：
```json
"霸王别姬"
```

新流程数据内容：
```json
"霸王别姬"
```

数据来源或处理逻辑：douban; 豆瓣条目标题

### `works.original_title`

旧的当前数据内容：
```json
"Farewell My Concubine"
```

新流程数据内容：
```json
"Farewell My Concubine"
```

数据来源或处理逻辑：omdb

### `works.year`

旧的当前数据内容：
```json
1993
```

新流程数据内容：
```json
1993
```

数据来源或处理逻辑：omdb

### `works.country`

旧的当前数据内容：
```json
"中国大陆 / 中国香港"
```

新流程数据内容：
```json
"中国大陆 / 中国香港"
```

数据来源或处理逻辑：douban

### `works.language`

旧的当前数据内容：
```json
"汉语普通话"
```

新流程数据内容：
```json
"汉语普通话"
```

数据来源或处理逻辑：douban

### `works.publish_company`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
null
```

数据来源或处理逻辑：system; 当前样板缺少稳定出品公司来源，先保留空值

### `works.runtime_minutes`

旧的当前数据内容：
```json
171
```

新流程数据内容：
```json
171
```

数据来源或处理逻辑：douban; 豆瓣显示 171 分钟；另有 155 分钟美国剧场版

### `works.synopsis_text`

旧的当前数据内容：
```json
"程蝶衣与段小楼自幼在梨园一同长大，凭《霸王别姬》名满京城，却因对戏与人生的不同理解走向分裂。\n\n当菊仙闯入二人关系，时代风云又不断改写命运，一场跨越半生的情感纠葛最终把舞台、欲望与历史一并推向悲剧。"
```

新流程数据内容：
```json
"程蝶衣与段小楼自幼在梨园一同长大，凭《霸王别姬》名满京城，却因对戏与人生的不同理解走向分裂。\n\n当菊仙闯入二人关系，时代风云又不断改写命运，一场跨越半生的情感纠葛最终把舞台、欲望与历史一并推向悲剧。"
```

数据来源或处理逻辑：douban

### `works.synopsis_note`

旧的当前数据内容：
```json
"豆瓣剧情简介。"
```

新流程数据内容：
```json
"豆瓣剧情简介。"
```

数据来源或处理逻辑：douban

### `works.story_text`

旧的当前数据内容：
```json
"上世纪二十年代的北平，妓女出身的母亲为了让小豆子有口饭吃，把他送进严苛的戏班。为了符合学戏规矩，小豆子被硬生生切去多出的手指，从此与小石头一起在关师傅门下受尽打骂与规训。小豆子天生适合旦角，却始终抗拒\"我本是女娇娥\"的唱词；经历逃班、小癞子之死与长期驯化后，他终于把\"程蝶衣\"这层身份唱进骨血，也把戏台人生与现实人生逐渐混为一体。\n\n成年后的程蝶衣与段小楼凭《霸王别姬》红遍京城，一个演虞姬，一个演霸王，台上台下都像命定搭档。蝶衣把\"一辈子差一年、一个月、一天、一个时辰都不算一辈子\"当成誓言，对师兄、对戏、对自我身份都投入了近乎宗教般的执念。段小楼却始终把唱戏当营生，把台上情义和台下生活分得更开。\n\n名妓菊仙的出现打破了这段微妙平衡。段小楼与菊仙成婚后，蝶衣把她视作闯入者，也第一次真正感到被背叛。与此同时，袁四爷这样的戏迷与权势人物不断介入，使蝶衣在被欣赏、被占有与自我献祭之间越陷越深。抗战、日本投降、政权更替接连到来，三人的关系也在不同历史时刻被迫重新站队、相互伤害。\n\n新中国成立后，他们一度迎来短暂稳定，但旧日恩怨和角色错位并未真正结束。到文革时期，昔日名角在群众批斗中被推上审判席，为了自保彼此揭短、互相刺伤。段小楼否认与蝶衣的深情，蝶衣也说出菊仙最无法承受的真相，最终逼得菊仙在绝望中自尽。曾经把戏唱到极致的三个人，至此都被时代和自身选择彻底碾碎。\n\n十一年后，程蝶衣与段小楼再度同台《霸王别姬》。当熟悉的唱段重新响起，蝶衣终于以虞姬的方式完成了自己与舞台、与霸王、与一生执念的最后合一，在戏里戏外都走向了真正的诀别。"
```

新流程数据内容：
```json
"上世纪二十年代的北平，妓女出身的母亲为了让小豆子有口饭吃，把他送进严苛的戏班。为了符合学戏规矩，小豆子被硬生生切去多出的手指，从此与小石头一起在关师傅门下受尽打骂与规训。小豆子天生适合旦角，却始终抗拒\"我本是女娇娥\"的唱词；经历逃班、小癞子之死与长期驯化后，他终于把\"程蝶衣\"这层身份唱进骨血，也把戏台人生与现实人生逐渐混为一体。\n\n成年后的程蝶衣与段小楼凭《霸王别姬》红遍京城，一个演虞姬，一个演霸王，台上台下都像命定搭档。蝶衣把\"一辈子差一年、一个月、一天、一个时辰都不算一辈子\"当成誓言，对师兄、对戏、对自我身份都投入了近乎宗教般的执念。段小楼却始终把唱戏当营生，把台上情义和台下生活分得更开。\n\n名妓菊仙的出现打破了这段微妙平衡。段小楼与菊仙成婚后，蝶衣把她视作闯入者，也第一次真正感到被背叛。与此同时，袁四爷这样的戏迷与权势人物不断介入，使蝶衣在被欣赏、被占有与自我献祭之间越陷越深。抗战、日本投降、政权更替接连到来，三人的关系也在不同历史时刻被迫重新站队、相互伤害。\n\n新中国成立后，他们一度迎来短暂稳定，但旧日恩怨和角色错位并未真正结束。到文革时期，昔日名角在群众批斗中被推上审判席，为了自保彼此揭短、互相刺伤。段小楼否认与蝶衣的深情，蝶衣也说出菊仙最无法承受的真相，最终逼得菊仙在绝望中自尽。曾经把戏唱到极致的三个人，至此都被时代和自身选择彻底碾碎。\n\n十一年后，程蝶衣与段小楼再度同台《霸王别姬》。当熟悉的唱段重新响起，蝶衣终于以虞姬的方式完成了自己与舞台、与霸王、与一生执念的最后合一，在戏里戏外都走向了真正的诀别。"
```

数据来源或处理逻辑：manual; 基于中文维基可读正文与现有条目整理；story.note 不再进入数据库主字段

### `works.aliases_json`

旧的当前数据内容：
```json
[
  "再见，我的妾",
  "Farewell My Concubine",
  "Adieu Ma Concubine"
]
```

新流程数据内容：
```json
[
  "再见，我的妾",
  "Farewell My Concubine",
  "Adieu Ma Concubine"
]
```

数据来源或处理逻辑：douban

### `works.release_dates_json`

旧的当前数据内容：
```json
[
  {
    "date": "1993-07-26",
    "location": "中国大陆"
  },
  {
    "date": "1993-01-01",
    "location": "中国香港"
  }
]
```

新流程数据内容：
```json
[
  {
    "date": "1993-07-26",
    "location": "中国大陆"
  },
  {
    "date": "1993-01-01",
    "location": "中国香港"
  }
]
```

数据来源或处理逻辑：douban

### `works.identifiers_json`

旧的当前数据内容：
```json
{
  "douban": "1291546",
  "imdb": "tt0106332",
  "tmdb": null
}
```

新流程数据内容：
```json
{
  "douban": "1291546",
  "imdb": "tt0106332",
  "tmdb": "10997"
}
```

数据来源或处理逻辑：doubanId:douban; imdbId:douban; tmdbId:derived; 从 links.tmdb URL 解析出 TMDB movie id

### `works.ratings_json`

旧的当前数据内容：
```json
{
  "aggregate": {
    "value": 8.9,
    "scale": 10
  },
  "douban": {
    "value": 9.6,
    "scale": 10
  },
  "imdb": {
    "value": 8.1,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "R"
  },
  "awards": {
    "value": "Nominated for 2 Oscars. 24 wins & 12 nominations total"
  }
}
```

新流程数据内容：
```json
{
  "aggregate": {
    "value": 8.9,
    "scale": 10
  },
  "douban": {
    "value": 9.6,
    "scale": 10
  },
  "imdb": {
    "value": 8.1,
    "scale": 10
  },
  "tmdb": {
    "value": null,
    "scale": 10
  },
  "rottenTomatoes": {
    "value": null,
    "scale": null
  },
  "metascore": {
    "value": null,
    "scale": null
  },
  "certification": {
    "value": "R"
  },
  "awards": {
    "value": "Nominated for 2 Oscars. 24 wins & 12 nominations total"
  }
}
```

数据来源或处理逻辑：doubanRating:douban; imdbRating:omdb; rated:omdb; awards:omdb

### `works.links_json`

旧的当前数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1291546/",
  "imdb": "https://www.imdb.com/title/tt0106332/",
  "tmdb": "https://www.themoviedb.org/movie/10997"
}
```

新流程数据内容：
```json
{
  "douban": "https://movie.douban.com/subject/1291546/",
  "imdb": "https://www.imdb.com/title/tt0106332/",
  "tmdb": "https://www.themoviedb.org/movie/10997"
}
```

数据来源或处理逻辑：merged: douban(douban/imdb) + tmdb(tmdb)

### `works.images_json`

旧的当前数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.jpg",
    "poster-02.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 79,
  "stillsTotal": 27,
  "assetDir": "video/movie/0101000004"
}
```

新流程数据内容：
```json
{
  "poster": "poster-main.jpg",
  "posters": [
    "poster-01.jpg",
    "poster-02.jpg",
    "poster-03.jpg",
    "poster-04.jpg",
    "poster-05.jpg"
  ],
  "stills": [
    "still-01.jpg",
    "still-02.jpg",
    "still-03.jpg",
    "still-04.jpg",
    "still-05.jpg"
  ],
  "wallpapers": [],
  "postersTotal": 79,
  "stillsTotal": 27,
  "assetDir": "video/movie/0101000004"
}
```

数据来源或处理逻辑：poster:tmdb; posters:tmdb; postersTotal:tmdb; stills:tmdb; stillsTotal:tmdb; wallpapers:system

### `works.videos_json`

旧的当前数据内容：
```json
[
  {
    "title": "Trailer",
    "duration": "01:34",
    "thumbnail": "video-trailer-01.jpg",
    "url": "https://www.youtube.com/watch?v=FFiHfDBt9lE"
  }
]
```

新流程数据内容：
```json
[
  {
    "title": "Trailer",
    "duration": "01:34",
    "thumbnail": "video-trailer-01.jpg",
    "url": "https://www.youtube.com/watch?v=FFiHfDBt9lE"
  }
]
```

数据来源或处理逻辑：tmdb; TMDB 视频列表仅抓到 1 条 Trailer

### `works.reviews_json`

旧的当前数据内容：
```json
[
  {
    "source": "豆瓣",
    "author": "陈野犁",
    "date": "2008-05-15",
    "rating": "力荐",
    "content": "《霸王别姬》最厉害的地方，不只是把一段梨园旧梦拍得华丽，而是让戏与人、爱与欲、时代与命运层层缠绕。程蝶衣不是单纯地活在戏里，而是在被命运反复撕裂之后，只剩下戏还能容纳他的全部真心。"
  },
  {
    "source": "豆瓣",
    "author": "psyduck",
    "date": "2006-02-14",
    "rating": "力荐",
    "content": "程蝶衣与段小楼的关系从戏班时代起就带着极深的依附与错位：一个把台上的誓言当成一生，一个始终想把戏和生活分开。影片真正残忍之处，在于这份感情既撑起了他们的艺术巅峰，也注定会在现实世界里一步步走向崩塌。"
  },
  {
    "source": "豆瓣",
    "author": "阿底",
    "date": "2006-06-02",
    "rating": "力荐",
    "content": "在看这部电影之前，很容易对国产电影抱有偏见；但《霸王别姬》会迅速把这种傲慢击碎。它的大手笔不只是制作层面的精致，而是敢于把迷恋、背叛、欲望和历史灾难同时放进人物命运里，让每一次相爱与相弃都带着时代的回声。"
  },
  {
    "source": "豆瓣",
    "author": "从嘉",
    "date": "2008-04-19",
    "rating": "力荐",
    "content": "小豆子被切去手指、被迫改口唱词的过程，不只是残酷训练，更像一场被强行完成的身份塑造。等到程蝶衣终于活成虞姬，他已经无法再把舞台当成表演，而只能把现实当成戏来承受；这正是影片最令人心惊的地方。"
  }
]
```

新流程数据内容：
```json
[
  {
    "author": "陈野犁",
    "source": "豆瓣",
    "date": "2008-05-15",
    "content": "《霸王别姬》最厉害的地方，不只是把一段梨园旧梦拍得华丽，而是让戏与人、爱与欲、时代与命运层层缠绕。程蝶衣不是单纯地活在戏里，而是在被命运反复撕裂之后，只剩下戏还能容纳他的全部真心。",
    "url": "https://movie.douban.com/review/1380398/",
    "title": "最懂蝶衣袁四爷"
  },
  {
    "author": "psyduck",
    "source": "豆瓣",
    "date": "2006-02-14",
    "content": "程蝶衣与段小楼的关系从戏班时代起就带着极深的依附与错位：一个把台上的誓言当成一生，一个始终想把戏和生活分开。影片真正残忍之处，在于这份感情既撑起了他们的艺术巅峰，也注定会在现实世界里一步步走向崩塌。",
    "url": "https://movie.douban.com/review/1025873/",
    "title": "关于《霸王别姬》-"
  },
  {
    "author": "阿底",
    "source": "豆瓣",
    "date": "2006-06-02",
    "content": "在看这部电影之前，很容易对国产电影抱有偏见；但《霸王别姬》会迅速把这种傲慢击碎。它的大手笔不只是制作层面的精致，而是敢于把迷恋、背叛、欲望和历史灾难同时放进人物命运里，让每一次相爱与相弃都带着时代的回声。",
    "url": "https://movie.douban.com/review/1049362/",
    "title": "迷恋与背叛——[霸王别姬]"
  },
  {
    "author": "从嘉",
    "source": "豆瓣",
    "date": "2008-04-19",
    "content": "小豆子被切去手指、被迫改口唱词的过程，不只是残酷训练，更像一场被强行完成的身份塑造。等到程蝶衣终于活成虞姬，他已经无法再把舞台当成表演，而只能把现实当成戏来承受；这正是影片最令人心惊的地方。",
    "url": "https://movie.douban.com/review/1356540/",
    "title": "胡说霸王别姬"
  }
]
```

数据来源或处理逻辑：douban; 豆瓣影评页精选长评前4条；已补 review.url/title，rating 不再进入数据库

### `works.soundtrack_json`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
null
```

数据来源或处理逻辑：无来源记录

### `works.relations_json`

旧的当前数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "title": "活着",
      "year": 1994,
      "rating": 9.3
    },
    {
      "title": "春光乍泄",
      "year": 1997,
      "rating": 9
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.4
    },
    {
      "title": "重庆森林",
      "year": 1994,
      "rating": 8.8
    },
    {
      "title": "罗马假日",
      "year": 1953,
      "rating": 9.1
    },
    {
      "title": "花样年华",
      "year": 2000,
      "rating": 8.8
    }
  ]
}
```

新流程数据内容：
```json
{
  "series": [],
  "similar": [
    {
      "title": "活着",
      "year": 1994,
      "rating": 9.3
    },
    {
      "title": "春光乍泄",
      "year": 1997,
      "rating": 9
    },
    {
      "title": "楚门的世界",
      "year": 1998,
      "rating": 9.4
    },
    {
      "title": "重庆森林",
      "year": 1994,
      "rating": 8.8
    },
    {
      "title": "罗马假日",
      "year": 1953,
      "rating": 9.1
    },
    {
      "title": "花样年华",
      "year": 2000,
      "rating": 8.8
    }
  ]
}
```

数据来源或处理逻辑：series:system; 当前4条样板未录入系列关系，先保留空数组; similar:merged: douban(title/rating) + omdb(year)

### `works.quotes_json`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板未整理 quotes，先保留空数组

### `works.status`

旧的当前数据内容：
```json
"published"
```

新流程数据内容：
```json
"published"
```

数据来源或处理逻辑：system; 当前电影样板默认按 published 导入

### `works.created_at`

旧的当前数据内容：
```json
"2026-05-02"
```

新流程数据内容：
```json
"2026-05-02"
```

数据来源或处理逻辑：system; 录入时间

### `works.updated_at`

旧的当前数据内容：
```json
"2026-05-02"
```

新流程数据内容：
```json
"2026-05-02"
```

数据来源或处理逻辑：system; 最后更新时间

### `credits.director`

旧的当前数据内容：
```json
[
  {
    "name": "陈凯歌",
    "nameEn": "Chen Kaige",
    "avatar": "avatar-chen-kaige.jpg",
    "avatarSource": "tmdb"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "陈凯歌",
    "nameEn": "Chen Kaige",
    "avatar": "avatar-chen-kaige.jpg",
    "avatarSource": "tmdb"
  }
]
```

数据来源或处理逻辑：merged: douban(name) + omdb(nameEn) + tmdb(avatar)

### `credits.writer`

旧的当前数据内容：
```json
[
  {
    "name": "芦苇",
    "nameEn": "Wei Lu",
    "role": "编剧"
  },
  {
    "name": "李碧华",
    "nameEn": "Lilian Lee Pik-Wah",
    "role": "原著/编剧"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "芦苇",
    "nameEn": "Wei Lu",
    "role": "编剧"
  },
  {
    "name": "李碧华",
    "nameEn": "Lilian Lee Pik-Wah",
    "role": "原著/编剧"
  }
]
```

数据来源或处理逻辑：merged: douban(name) + tmdb(nameEn/role)

### `credits.cast`

旧的当前数据内容：
```json
[
  {
    "name": "张国荣",
    "nameEn": "Leslie Cheung",
    "role": "程蝶衣",
    "avatar": "avatar-leslie-cheung.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "张丰毅",
    "nameEn": "Zhang Fengyi",
    "role": "段小楼",
    "avatar": "avatar-zhang-fengyi.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "巩俐",
    "nameEn": "Gong Li",
    "role": "菊仙",
    "avatar": "avatar-gong-li.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "葛优",
    "nameEn": "Ge You",
    "role": "袁四爷",
    "avatar": "avatar-ge-you.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "英达",
    "nameEn": "Ying Da",
    "role": "那坤",
    "avatar": "avatar-ying-da.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "蒋雯丽",
    "nameEn": "Jiang Wenli",
    "role": "小豆子娘",
    "avatar": "avatar-jiang-wenli.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "吴大维",
    "nameEn": "David Wu",
    "role": "红卫兵",
    "avatar": "avatar-david-wu.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "吕齐",
    "nameEn": "Qi Lu",
    "role": "关师傅",
    "avatar": "avatar-lv-qi.jpg",
    "avatarSource": "tmdb"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "张国荣",
    "nameEn": "Leslie Cheung",
    "role": "程蝶衣",
    "avatar": "avatar-leslie-cheung.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "张丰毅",
    "nameEn": "Zhang Fengyi",
    "role": "段小楼",
    "avatar": "avatar-zhang-fengyi.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "巩俐",
    "nameEn": "Gong Li",
    "role": "菊仙",
    "avatar": "avatar-gong-li.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "葛优",
    "nameEn": "Ge You",
    "role": "袁四爷",
    "avatar": "avatar-ge-you.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "英达",
    "nameEn": "Ying Da",
    "role": "那坤",
    "avatar": "avatar-ying-da.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "蒋雯丽",
    "nameEn": "Jiang Wenli",
    "role": "小豆子娘",
    "avatar": "avatar-jiang-wenli.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "吴大维",
    "nameEn": "David Wu",
    "role": "红卫兵",
    "avatar": "avatar-david-wu.jpg",
    "avatarSource": "tmdb"
  },
  {
    "name": "吕齐",
    "nameEn": "Qi Lu",
    "role": "关师傅",
    "avatar": "avatar-lv-qi.jpg",
    "avatarSource": "tmdb"
  }
]
```

数据来源或处理逻辑：merged: douban(name/role) + tmdb(nameEn/avatar)

### `credits.otherCast`

旧的当前数据内容：
```json
[
  {
    "name": "雷汉",
    "nameEn": "Han Lei",
    "role": "小四(成年)"
  },
  {
    "name": "童弟",
    "nameEn": "Tong Di",
    "role": "张公公"
  },
  {
    "name": "尹治",
    "nameEn": "Yin Zhi",
    "role": "小豆子(少年)"
  },
  {
    "name": "马明威",
    "nameEn": "Ma Mingwei",
    "role": "小豆子(童年)"
  },
  {
    "name": "费振翔",
    "nameEn": "Zhenxiang Fei",
    "role": "小石头(童年)"
  },
  {
    "name": "赵海龙",
    "nameEn": "Zhao Hailong",
    "role": "小石头(少年)"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "雷汉",
    "nameEn": "Han Lei",
    "role": "小四(成年)"
  },
  {
    "name": "童弟",
    "nameEn": "Tong Di",
    "role": "张公公"
  },
  {
    "name": "尹治",
    "nameEn": "Yin Zhi",
    "role": "小豆子(少年)"
  },
  {
    "name": "马明威",
    "nameEn": "Ma Mingwei",
    "role": "小豆子(童年)"
  },
  {
    "name": "费振翔",
    "nameEn": "Zhenxiang Fei",
    "role": "小石头(童年)"
  },
  {
    "name": "赵海龙",
    "nameEn": "Zhao Hailong",
    "role": "小石头(少年)"
  }
]
```

数据来源或处理逻辑：tmdb

### `credits.producer`

旧的当前数据内容：
```json
[
  {
    "name": "徐枫",
    "nameEn": "Feng Hsu",
    "role": "制片人"
  },
  {
    "name": "徐杰",
    "nameEn": "Jade Hsu",
    "role": "监制"
  },
  {
    "name": "汤君年",
    "nameEn": "Jun-Nian Tang",
    "role": "出品人"
  }
]
```

新流程数据内容：
```json
[
  {
    "name": "徐枫",
    "nameEn": "Feng Hsu",
    "role": "制片人"
  },
  {
    "name": "徐杰",
    "nameEn": "Jade Hsu",
    "role": "监制"
  },
  {
    "name": "汤君年",
    "nameEn": "Jun-Nian Tang",
    "role": "出品人"
  }
]
```

数据来源或处理逻辑：douban

### `terms.genre`

旧的当前数据内容：
```json
[
  "剧情",
  "爱情",
  "同性"
]
```

新流程数据内容：
```json
[
  "剧情",
  "爱情",
  "同性"
]
```

数据来源或处理逻辑：douban

### `terms.tags`

旧的当前数据内容：
```json
[]
```

新流程数据内容：
```json
[]
```

数据来源或处理逻辑：system; 当前4条样板尚未建立标签体系，先保留空数组

### `derived.tmdbId`

旧的当前数据内容：
```json
null
```

新流程数据内容：
```json
"10997"
```

数据来源或处理逻辑：derived; 从 links.tmdb URL 解析出 TMDB movie id
