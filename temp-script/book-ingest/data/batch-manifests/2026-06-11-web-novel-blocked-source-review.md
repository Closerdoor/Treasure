# 2026-06-11 未入库网络小说候选来源审视清单

用途：这份清单只用于审视候选来源，不写数据库。

数据源边界：本清单中的 QQ阅读、微信读书、番茄小说、晋江文学城、中国作家网、抖音百科、好读、九九藏书、全本小说网、搜狐、萌娘百科等链接，暂时都是候选锚点或参考页，不是新增的正式自动采集数据源。当前正式自动来源仍以既有链路为准：douban、openlibrary、baike、wikipedia、goodreads、dangdang、qidian；网络小说 fast 批次默认只自动使用 qidian。任何新站点要进入正式入库流程，必须先补 adapter、字段映射、预检规则和文档。

| 书名 | 作者 | 置信度 | 建议 | 首选来源 | 你需要审视的问题 |
|---|---|---|---|---|---|
| 雪中悍刀行 | 烽火戏诸侯 | medium | Use whole-work source, not a single print volume. | [QQ阅读](https://ubook.reader.qq.com/book-detail/172865) | 确认按网络小说整体入库，而不是某一册实体书。 |
| 新宋 | 阿越 | high | Use encyclopedia/WeRead/Haodoo as whole-work anchor. | [Wikipedia](https://zh.wikipedia.org/wiki/%E6%96%B0%E5%AE%8B) | 确认按《新宋》整体作品入库。 |
| 风姿物语 | 罗森 | medium | Use Wikipedia and Douban/edition pages as metadata anchors; fallback page for synopsis. | [Wikipedia](https://zh.wikipedia.org/zh-hans/%E9%A2%A8%E5%A7%BF%E7%89%A9%E8%AA%9E) | 确认按《风姿物语》整体作品入库，不按单册《暹罗结义》入库。 |
| 陈二狗的妖孽人生 | 烽火戏诸侯 | high | Rerun with exact qidian URL. | [起点中文网](https://www.qidian.com/book/1204224/) | 确认使用起点《陈二狗的妖孽人生》作为主来源。 |
| 佣兵天下 | 说不得大师 | high | Rerun with exact qidian URL; fallback to WeRead/99csw for summary if truncation persists. | [起点中文网](https://www.qidian.com/book/1026121482/) | 确认使用起点作为主来源，允许必要时用微信读书/九九藏书补简介。 |
| 天行健 | 燕垒生 | high | Use WeRead or Douban as whole-work anchor. | [微信读书](https://weread.qq.com/web/bookDetail/fec32090811e1a5d6g019018) | 确认按《天行健》修订版全集/整体作品入库。 |
| 鬼吹灯 | 天下霸唱 | high | Use encyclopedia as whole-series anchor. | [Wikipedia](https://zh.wikipedia.org/wiki/%E9%AC%BC%E5%90%B9%E7%81%AF) | 确认按《鬼吹灯》全八卷/整体作品入库，而不是《鬼吹灯II》单部。 |
| 第一次的亲密接触 | 痞子蔡 | high | Use Wikipedia/Douban as metadata and story anchors. | [Wikipedia](https://zh.wikipedia.org/wiki/%E7%AC%AC%E4%B8%80%E6%AC%A1%E7%9A%84%E8%A6%AA%E5%AF%86%E6%8E%A5%E8%A7%B8) | 确认作者展示用“痞子蔡”，别名/本名可记录为蔡智恒。 |
| 悟空传 | 今何在 | medium | Use author/edition reference and treat qidian commemorative edition only as cover/edition candidate. | [Wikipedia author page](https://zh.wikipedia.org/wiki/%E4%BB%8A%E4%BD%95%E5%9C%A8) | 确认按《悟空传》整体作品入库，版本可不锁定典藏纪念版。 |
| 飘邈之旅 | 萧潜 | medium | Use encyclopedia/fallback source; verify spelling 飘邈 vs 飘渺 in metadata aliases. | [抖音百科](https://m.baike.com/wikiid/3469911547108204524) | 确认主标题使用用户原文《飘邈之旅》，并把《飘渺之旅》作为别名。 |
| 亵渎 | 烟雨江南 | medium | Use reference/fallback sources; do not use qidian search result. | [Douban review/context](https://m.douban.com/book/review/14604982/) | 确认按烟雨江南《亵渎》整体作品入库。 |
| 花千骨 | Fresh果果 | high | Use original Jinjiang page as primary source. | [晋江文学城](https://www.jjwxc.net/onebook.php?novelid=316358) | 确认按小说《花千骨》整体作品入库，原名/相关名可记录《仙侠奇缘之花千骨》。 |
| 宰执天下 | cuslaa | high | Use WeRead and encyclopedia/reference sources; if possible later locate Zongheng original page. | [微信读书](https://weread.qq.com/web/bookDetail/8f432ca052ba378f4cd737b) | 确认按《宰执天下》整体作品入库，作者展示为 cuslaa。 |
| 十日终焉 | 杀虫队队员 | high | Use Fanqie exact page as primary source. | [番茄小说](https://fanqienovel.com/page/7143038691944959011) | 确认使用番茄小说《十日终焉》作为主来源。 |

## 逐本候选来源

### 雪中悍刀行 / 烽火戏诸侯
- 上轮阻塞原因：qidian search matched a numbered volume, not the whole work; summary was truncated.
- 建议：Use whole-work source, not a single print volume.
- 需要审视：确认按网络小说整体入库，而不是某一册实体书。
- 候选来源：
  - [QQ阅读](https://ubook.reader.qq.com/book-detail/172865)：licensed_reading_platform；用途：title, author, summary, cover；备注：Search result presents the whole work and author; likely better than qidian numbered-volume result.
  - [中国作家网](https://www.chinawriter.com.cn/n1/2022/0125/c404027-32339304.html)：reference；用途：author, word_count_or_completion_context, work_context；备注：Authoritative article states the work began in 2011, took four and a half years, and is about 4.6 million characters.
  - [九九藏书 numbered volumes](https://read.99csw.com/book/10864/)：fallback；用途：story_fallback；备注：Volume pages only; use cautiously and never as whole-work title anchor.

### 新宋 / 阿越
- 上轮阻塞原因：qidian search matched 新宋风流 / 银箭.
- 建议：Use encyclopedia/WeRead/Haodoo as whole-work anchor.
- 需要审视：确认按《新宋》整体作品入库。
- 候选来源：
  - [Wikipedia](https://zh.wikipedia.org/wiki/%E6%96%B0%E5%AE%8B)：encyclopedia；用途：title, author, genre, publish_date, story；备注：Identifies 新宋 as 阿越's alternate-history novel.
  - [微信读书 author page](https://weread.qq.com/web/search/books?author=%E9%98%BF%E8%B6%8A)：licensed_reading_platform；用途：author, edition_anchor, cover；备注：Search result shows 新宋·大结局（全15册） under 阿越.
  - [好读](https://www.haodoo.net/?M=book&P=15Q0)：fallback；用途：summary_fallback, author_context；备注：Useful but not preferred over encyclopedia/licensed platform.

### 风姿物语 / 罗森
- 上轮阻塞原因：no usable raw source in fast pass.
- 建议：Use Wikipedia and Douban/edition pages as metadata anchors; fallback page for synopsis.
- 需要审视：确认按《风姿物语》整体作品入库，不按单册《暹罗结义》入库。
- 候选来源：
  - [Wikipedia](https://zh.wikipedia.org/zh-hans/%E9%A2%A8%E5%A7%BF%E7%89%A9%E8%AA%9E)：encyclopedia；用途：title, author, genre, work_context；备注：States it is a fantasy web novel by 罗森, serialized from 1997.
  - [Douban author works](https://book.douban.com/author/4513708/books?format=pic&sortby=time)：metadata；用途：edition_anchor, cover_candidates；备注：Includes 风姿物语1·暹罗结义 and related editions; use only as edition reference.
  - [全本小说网](https://quanben.io/n/fengziwuyu/)：fallback；用途：summary_fallback；备注：Third-party source with title, author, category and synopsis.

### 陈二狗的妖孽人生 / 烽火戏诸侯
- 上轮阻塞原因：no usable raw source in fast pass.
- 建议：Rerun with exact qidian URL.
- 需要审视：确认使用起点《陈二狗的妖孽人生》作为主来源。
- 候选来源：
  - [起点中文网](https://www.qidian.com/book/1204224/)：original_platform；用途：title, author, status, summary, cover；备注：Exact title/author match in search result.
  - [中国作家网](https://www.chinawriter.com.cn/n1/2020/0331/c404027-31655577.html)：reference；用途：story_context, author_context；备注：Article describes the work and protagonist; useful for story fallback.

### 佣兵天下 / 说不得大师
- 上轮阻塞原因：qidian raw existed but summary appeared truncated in fast pass.
- 建议：Rerun with exact qidian URL; fallback to WeRead/99csw for summary if truncation persists.
- 需要审视：确认使用起点作为主来源，允许必要时用微信读书/九九藏书补简介。
- 候选来源：
  - [起点中文网](https://www.qidian.com/book/1026121482/)：original_platform；用途：title, author, summary, cover；备注：Exact title/author candidate found.
  - [微信读书 author/work search](https://weread.qq.com/web/search/books?author=%E8%AF%B4%E4%B8%8D%E5%BE%97%E5%A4%A7%E5%B8%88)：licensed_reading_platform；用途：author, summary_fallback, cover_candidate；备注：Shows 佣兵天下 under 说不得大师.
  - [九九藏书](https://www.99csw.com/book/1734/index.htm)：fallback；用途：summary_fallback, story_fallback；备注：Third-party source with stable synopsis; use if qidian summary remains truncated.

### 天行健 / 燕垒生
- 上轮阻塞原因：qidian search matched 天行健：渡 / 薄酒敬余生.
- 建议：Use WeRead or Douban as whole-work anchor.
- 需要审视：确认按《天行健》修订版全集/整体作品入库。
- 候选来源：
  - [微信读书](https://weread.qq.com/web/bookDetail/fec32090811e1a5d6g019018)：licensed_reading_platform；用途：title, author, summary, cover；备注：Exact title/author and whole-work synopsis.
  - [豆瓣](https://book.douban.com/subject/1437858//)：metadata；用途：edition_anchor, rating, summary_fallback；备注：Exact title/author edition page.
  - [九九藏书](https://www.99csw.com/book/3143/index.htm)：fallback；用途：story_fallback；备注：First volume page; not whole-work primary anchor.

### 鬼吹灯 / 天下霸唱
- 上轮阻塞原因：qidian search matched 鬼吹灯II / 本物天下霸唱.
- 建议：Use encyclopedia as whole-series anchor.
- 需要审视：确认按《鬼吹灯》全八卷/整体作品入库，而不是《鬼吹灯II》单部。
- 候选来源：
  - [Wikipedia](https://zh.wikipedia.org/wiki/%E9%AC%BC%E5%90%B9%E7%81%AF)：encyclopedia；用途：title, author, genre, series_structure, story；备注：Identifies 鬼吹灯 as a web novel by 天下霸唱 and lists first/second part volumes.

### 第一次的亲密接触 / 痞子蔡
- 上轮阻塞原因：qidian search matched unrelated 第一次.
- 建议：Use Wikipedia/Douban as metadata and story anchors.
- 需要审视：确认作者展示用“痞子蔡”，别名/本名可记录为蔡智恒。
- 候选来源：
  - [Wikipedia](https://zh.wikipedia.org/wiki/%E7%AC%AC%E4%B8%80%E6%AC%A1%E7%9A%84%E8%A6%AA%E5%AF%86%E6%8E%A5%E8%A7%B8)：encyclopedia；用途：title, author, first_publication, story, work_context；备注：States the novel was written by 蔡智恆 under the pen name 痞子蔡 and first posted in 1998.
  - [Douban](https://m.douban.com/book/subject/1566311/)：metadata；用途：summary, author_bio, rating, cover_candidate；备注：Book page for 第一次亲密接触.
  - [中国作家网](https://www.chinawriter.com.cn/n1/2020/0113/c425784-31546524.html)：reference；用途：work_context, author_context；备注：Useful contextual article about the work's role in early Chinese web literature.

### 悟空传 / 今何在
- 上轮阻塞原因：qidian search matched a print commemorative edition; not necessarily wrong, but fast pass blocked as title mismatch.
- 建议：Use author/edition reference and treat qidian commemorative edition only as cover/edition candidate.
- 需要审视：确认按《悟空传》整体作品入库，版本可不锁定典藏纪念版。
- 候选来源：
  - [Wikipedia author page](https://zh.wikipedia.org/wiki/%E4%BB%8A%E4%BD%95%E5%9C%A8)：author_reference；用途：author, bibliography, publication_context；备注：Lists 悟空传 among 今何在's notable works and publication history.
  - [中国作家网](https://www.chinawriter.com.cn/n1/2017/0717/c404079-29409132.html)：reference；用途：summary_context, work_context；备注：States 悟空传 was serialized in 2000 and published in 2001.

### 飘邈之旅 / 萧潜
- 上轮阻塞原因：qidian raw lacked title/summary/author and failed temporary import.
- 建议：Use encyclopedia/fallback source; verify spelling 飘邈 vs 飘渺 in metadata aliases.
- 需要审视：确认主标题使用用户原文《飘邈之旅》，并把《飘渺之旅》作为别名。
- 候选来源：
  - [抖音百科](https://m.baike.com/wikiid/3469911547108204524)：encyclopedia；用途：title, alias, author, summary, story；备注：Entry states 飘邈之旅/飘渺之旅 is a 2002/2003 cultivation novel by 萧潜.
  - [Sohu article](https://www.sohu.com/a/674854587_121698175)：reference；用途：work_context, genre_context；备注：Useful context, not primary source.

### 亵渎 / 烟雨江南
- 上轮阻塞原因：qidian search matched 亵渎牧师 / 血腥queen.
- 建议：Use reference/fallback sources; do not use qidian search result.
- 需要审视：确认按烟雨江南《亵渎》整体作品入库。
- 候选来源：
  - [Douban review/context](https://m.douban.com/book/review/14604982/)：reference；用途：work_context, genre_context；备注：Discussion of 烟雨江南《亵渎》; useful for validation, not enough alone for full staging.
  - [Sohu synopsis article](https://www.sohu.com/a/756234842_121698175)：fallback；用途：summary_fallback, story_fallback；备注：Contains plot description; third-party fallback.

### 花千骨 / Fresh果果
- 上轮阻塞原因：qidian search matched derivative 花千骨之谭凡 / 白色的宇宙.
- 建议：Use original Jinjiang page as primary source.
- 需要审视：确认按小说《花千骨》整体作品入库，原名/相关名可记录《仙侠奇缘之花千骨》。
- 候选来源：
  - [晋江文学城](https://www.jjwxc.net/onebook.php?novelid=316358)：original_platform；用途：title, author, tags, summary, status；备注：Exact original platform candidate.
  - [Wikipedia TV page book section](https://zh.wikipedia.org/wiki/%E8%8A%B1%E5%8D%83%E9%AA%A8_%28%E9%9B%BB%E8%A6%96%E5%8A%87%29)：encyclopedia；用途：edition_context, adaptation_context；备注：TV page but includes novel publication editions; use only as supplemental reference.
  - [萌娘百科](https://zh.moegirl.org.cn/%E8%8A%B1%E5%8D%83%E9%AA%A8)：reference；用途：summary_fallback, work_context；备注：States it is by Fresh果果 and first serialized on Jinjiang.

### 宰执天下 / cuslaa
- 上轮阻塞原因：qidian search matched 红楼之宰执天下 / 太费神.
- 建议：Use WeRead and encyclopedia/reference sources; if possible later locate Zongheng original page.
- 需要审视：确认按《宰执天下》整体作品入库，作者展示为 cuslaa。
- 候选来源：
  - [微信读书](https://weread.qq.com/web/bookDetail/8f432ca052ba378f4cd737b)：licensed_reading_platform；用途：title, author, summary, word_count, cover；备注：Exact work page and useful metadata.
  - [抖音百科](https://m.baike.com/wikiid/8369379632458482201)：encyclopedia；用途：title, author, serialization_dates, summary, story；备注：States it is by cuslaa, serialized on Zongheng, completed in 2019.
  - [搜狐/北青网 article](https://www.sohu.com/a/712634939_255783)：reference；用途：author_context, award_context；备注：Context source only.

### 十日终焉 / 杀虫队队员
- 上轮阻塞原因：no usable raw source in fast pass.
- 建议：Use Fanqie exact page as primary source.
- 需要审视：确认使用番茄小说《十日终焉》作为主来源。
- 候选来源：
  - [番茄小说](https://fanqienovel.com/page/7143038691944959011)：original_platform；用途：title, author, status, word_count, summary, cover；备注：Exact work page; search result states completed, 3.201 million characters, author 杀虫队队员.
  - [番茄小说 author page](https://fanqienovel.com/author-page/66292947550-6914903776998462727)：author_platform；用途：author, author_works；备注：Author page lists 十日终焉 and 传说管理局.
  - [中国作家网 interview](https://www.chinawriter.com.cn/n1/2024/0227/c404024-40184501.html)：reference；用途：author_context, work_context；备注：Authoritative interview/context source.
