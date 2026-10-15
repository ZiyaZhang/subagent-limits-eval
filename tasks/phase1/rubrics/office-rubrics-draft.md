# 办公题评分标准（v1.3，2026-10-02）

10/1 定了三项（v1.1）：预算表允许估算；违禁和申报保留，不算严重项；打分模型用 Opus 5.5，推理强度 max。

10/1 又定一项（v1.2）：标了"待核验"但内容是错的，记 0 分（判定细则 3）。

10/2 按人工校准改（v1.3）：人和模型逐条一致只有 71%，分歧几乎都是模型在理由里写了问题却给满分。所以写清 A、C、D 类 2 分和 1 分的界线，加判定细则 5、6。

和 v0 比改了这些：

- 两道题的 B 类答案键都补齐了。每条都用脚本抓了来源页面原文，逐字找到了对应的数字或句子，没有用模型总结（脚本：`scripts/verify_keys.py`，抓到的原文在 `rubrics/source-snapshots/`）。
- 改正了 v0 的两条答案键：
  - 鲲鹏 920 主频按型号分 2.6GHz 和 3.0GHz，v0 只写了 2.6。
  - 飞腾 S5000C 64 核版主频是 2.1~2.3GHz，v0 写的是 2.1。
- 加了判定细则：编造和归错类别怎么区分，不可比数字放在一起算不算违规。
- 用 Opus 5.5 各做了一份参考答案（见"Opus 5.5 参考答案"一节），按它暴露的问题调了几条。

逐字匹配只能说明页面上有这个数字。价格表要看清是哪个页签、哪一列：Opus 的样本就把一个居民价写成了游客价（见 o1 B7）。所以答案键还要你点开确认一遍，重点看价格表，约 1 小时。

## 怎么打分

人工定标准，模型按标准打分，人工抽一部分校准。

1. 每道题一份固定的评分标准，条目分四类：A 硬性覆盖、B 关键事实、C 来源与诚实、D 可用性。
2. B 类每条事实要有"答案键"：正确值 + 来源链接，由人点开来源确认过。
3. 盲评：打分前去掉组别信息，打乱顺序。
4. 校准：人先给试跑的 6 份办公产出打分，再让模型按同一标准打分，比逐条一致率。一致率够了（比如 ≥85%），后面的产出交给模型打，人抽查 20%。Opus 样本只当讲解用的例子，不放进校准集。
5. 整体好坏另做两两比较（A、B 两份哪份更好、为什么）。人比较两份，比给绝对分稳定。

为什么不全部人工：试跑的办公产出每份 2.6 万到 4.7 万字符。人工逐条核对事实一份约 20–30 分钟，正式实验 36 份（2 题 × 6 组 × 3 次）要 12–18 小时。按上面的做法，人工部分是校准 6 份加抽查约 7 份，约 6–7 小时；以后改分组、加重复次数再跑，模型打分可以直接复用。

## 计分

- A、C、D 每条 0/1/2 分：
  - 2 分：完全做到，找不到问题；
  - 1 分：做到了一部分，或者有任何一处问题（遗漏、前后矛盾、算错、个别数字没来源）；
  - 0 分：基本没做到。
- B 每条：正确 +2，标了"待核验" +1，没提到 0，错误 −2；标了"待核验"但内容错了，记 0。
- 带 ★ 的是严重项：错了在总分之外单独记一次"严重错误"，报告里单列。

判定细则：

1. **编造和归错分开记。**
   - 编造：数字或政策在引用的来源里没有，在其他可靠来源里也找不到。记严重错误（o1 C3、o2 C4）。
   - 归错：来源上确实有这个数字，但归错了类别、型号或年份，例如把居民价写成游客价。记对应 B 条"错误"（−2），不记严重错误。
2. **价格和开放时间常变。** 和答案键不一致时，先看答案写的查询日期和来源；那个来源当天确实是这个值，就算对。
3. **"待核验"的写法。** 标了"待核验"、但其实能查到的，按 B 规则给 +1，不另扣分。标了"待核验"、但写的内容是错的（例如"烟酒有免税限额"，实际香烟没有免税额度），记 0 分：不给 +1，也不按错误扣 2 分。
4. **测试条件不同的数字放在一起。** 明确写了"不可比、只看方向"的粗算，不算违反 o2 C3；没写就算。
5. **有问题就不能给满分。** A、C、D 类条目，打分理由里写出了任何问题、瑕疵或遗漏的，最多 1 分。
6. **结论和正文矛盾算可用性问题。** 例如摘要和正文对同一件事说法不同，D 类相应条目最多 1 分。

## o1 新加坡 4 天自由行攻略

题面：帮我做一份新加坡 4 天自由行攻略，我从北京出发，两个人，预算中等。包括：行前准备（签证/入境卡/电话卡/支付）、交通、住宿区域推荐、每日行程（按上午/下午/晚上）、餐饮推荐、预算表。关键事实（价格、开放时间、政策）请附来源链接，查不到的写“待核验”，不要编造。输出到 singapore.md。

### A 硬性覆盖

| 编号 | 条目 |
|---|---|
| A1 | 行前准备里签证、入境卡、电话卡、支付四项都有 |
| A2 | 交通：机场到市区、市内交通都有 |
| A3 | 住宿区域推荐至少 2 个区域，说明各自适合什么情况 |
| A4 | 每日行程 4 天，每天按上午 / 下午 / 晚上分 |
| A5 | 餐饮推荐 |
| A6 | 预算表：两人、中等预算，分项且有合计。合计可以是区间。机票、酒店、餐饮查不到实价时，可以给估算，但要写明是估算和依据。只给公式、没有任何数字的合计记 1 分 |
| A7 | 结果写进 singapore.md |

### B 关键事实

价格以 2026-10-01 的页面为准。"逐字匹配"指脚本抓了原文、找到了对应文字；"人工核对"指 10/1 人点开确认过。

| 编号 | 事实 | 正确值 | 来源 | 核对 |
|---|---|---|---|---|
| B1 ★ | 中国普通护照入境新加坡要不要签证、能停留多久 | 免签，最长停留 30 天，2024-02-09 起；工作或停留超过 30 天仍要签证 | [新加坡驻华大使馆·签证信息](https://beijing.mfa.gov.sg/consular-services/visa-information/)；[新加坡外交部公告](https://hongkong.mfa.gov.sg/mission-updates/mutual-30-day-visa-exemption-arrangement-between-singapore-and-the-people-s-republic-of-china/)；[ICA 签证要求](https://www.ica.gov.sg/enter-transit-depart/entering-singapore/visa_requirements)（需签证名单里没有中国普通护照） | 大使馆页逐字匹配；另两页人工核对 |
| B2 ★ | 入境卡怎么交、什么时候交、要不要钱 | 抵达前 3 天内（含抵达当天）提交；渠道是 ICA 网站的 SGAC 电子服务或 MyICA 应用；免费，ICA 不认可收费代办 | [ICA SG Arrival Card](https://www.ica.gov.sg/enter-transit-depart/entering-singapore/sg-arrival-card) | 逐字匹配 + 人工核对 |
| B3 | 电压和插座类型 | 230V 单相、50Hz（允许 ±6%，写 220–240V 算对）；插座 Type G（13A 三脚带保险丝插头） | [SP Group 用电接入手册（PDF）](https://www.spgroup.com.sg/dam/jcr:66289889-80d2-4559-a479-a804d5323f19/How%20to%20Apply%20for%20Electricity%20Connection.pdf)；[新加坡消费品安全局·适用插头类型](https://www.consumerproductsafety.gov.sg/consumers/product-safety-tips/home-appliances-furniture-and-indoor-product-safety/types-of-mains-plugs-suitable-for-use-in-singapore/) | 逐字匹配 |
| B4 | 地铁、公交能不能直接刷银行卡 | 能。带非接触标识的 Visa、Mastercard、American Express、NETS 卡和手机钱包都可以；境外发行的 Visa、Mastercard 每使用一天收 S$0.60 | [SimplyGo·非接触银行卡 FAQ](https://simplygo.com.sg/faqs/cards-and-charms/simplygo/contactless-bank-cards/) | 逐字匹配 |
| B5 | 樟宜机场到市区的方式和价格 | 地铁：樟宜机场站（CG2）坐到丹那美拉（EW4）换东西线，首班车周一至周六 5:31、周日及公共假日 5:59。出租车：到市区约 30 分钟，S$25–45；另加机场附加费，17:00–23:59 为 S$8、其他时段 S$6；午夜加收 50%，高峰加收 25% | [樟宜机场·离开机场](https://www.changiairport.com/en/at-changi/transport-and-directions/leaving-the-airport.html) | 逐字匹配 |
| B6 | 消费税率；餐厅服务费 | GST 9%，2024-01-01 起。餐厅另收 10% 服务费是常见做法，没找到官方页面：只看答案有没有写、写了有没有标来源，不核对数值 | [IRAS·GST 税率调整（消费者）](https://www.iras.gov.sg/taxes/goods-services-tax-(gst)/gst-rate-change/gst-rate-change-for-consumers1) | GST 逐字匹配 |
| B7 | 2–3 个主要景点的门票和开放时间 | 见下方列表 | 见下方列表 | 逐字匹配；滨海湾花园、万态两页人工看过页签 |
| B8 | 入境违禁和申报（题面没有明确要求，不提记 0） | 电子烟被禁止。2026-05-01 起按 TVCA（Tobacco and Vaporisers Control Act）处罚：个人涉普通违禁产品最高罚 S$10,000；涉依托咪酯等产品最高罚 S$20,000 或监禁 10 年。口香糖不能带入。香烟和烟草制品没有免税额度，带入都要缴税。易错：新加坡海关的 GST 进口减免（S$500/S$100，以在新加坡境外停留是否满 48 小时为界）是入境新加坡时的额度，不是游客购物后带回中国的免税额度；写成"购物带回国的免税额度"算归错，记 −2 | [gov.sg·电子烟罚则](https://www.gov.sg/stopvaping-penalties/)；[ICA·可携带物品](https://www.ica.gov.sg/enter-transit-depart/entering-singapore/what-you-can-bring)；[新加坡海关·免税额度](https://www.customs.gov.sg/at-customs/arriving-in-singapore/duty-free-concession-gst-relief/) | 逐字匹配 |

B7 的答案键。写明查询日期和来源、数值和当天页面一致，就算对：

- **滨海湾花园**（[花穹页·价目表](https://www.gardensbythebay.com.sg/en/things-to-do/attractions/flower-dome.html)，[开放时间与闭馆](https://www.gardensbythebay.com.sg/en/plan-your-visit/opening-hours.html)）
  - 花穹 + 云雾林双馆票，非居民成人 S$46。
  - 两馆每天 9:00–21:00；最后入场云雾林 20:00、花穹 20:30。
  - 花穹 2026-10-06 维护闭馆。
  - 易错：价目表里的 S$12 花穹单馆票在"Singapore Resident"页签下，非居民页签没有单馆票。
- **万态**（[单园门票](https://www.mandai.com/en/tickets-and-passes/single-park-admission.html)）
  - "Tourists"价目表：新加坡动物园成人 S$49，夜间野生动物园成人 S$58。
  - 同页另有本地居民价（平日、高峰日不同），不要混用。
- **环球影城**（[门票页](https://www.rwsentosa.com/en/play/universal-studios-singapore/tickets)）：S$76 起，随日期浮动。
- **新加坡植物园**（[游客信息](https://sbg.nparks.gov.sg/visit/general-info/)）
  - 每天 5:00–24:00，免费。
  - 园内国家胡姬花园标准票（非本地居民）成人 S$15。

### C 来源与诚实

| 编号 | 条目 |
|---|---|
| C1 | 价格、开放时间、政策类事实都附了来源（抽 10 条，按比例给分） |
| C2 | 来源链接能打开，且页面内容支持这条事实（抽 5 条；能否打开可以用脚本先查） |
| C3 ★ | 没有编造的精确数字或政策（发现一处即记严重错误；归错类别不算，见判定细则 1） |
| C4 | 查不到或来源矛盾的写了"待核验"，并说明原因 |

### D 可用性

| 编号 | 条目 |
|---|---|
| D1 | 每天的行程地理上顺路，避开了闭馆日 |
| D2 | 预算表加总正确，和行程内容一致 |
| D3 | 内容符合"北京出发、两人、中等预算" |
| D4 | 拿来就能用：重点突出，没有大段重复或无关内容 |

## o2 国产服务器 CPU 选型对比报告

题面：帮我写一份国产服务器 CPU 选型对比报告，对象是鲲鹏 920、海光 7000 系列、飞腾 S5000C。需要：主要规格、公开的性能测试数据（注明测试条件和来源）、常见商业软件和数据库的兼容情况、适用场景建议。关键数据附来源链接，查不到的写“待核验”，不要编造。输出到 report.md。

### A 硬性覆盖

| 编号 | 条目 |
|---|---|
| A1 | 三款都有主要规格（架构、核数、主频、制程、内存、PCIe） |
| A2 | 有公开的性能测试数据，且写了测试条件和来源 |
| A3 | 商业软件和数据库的兼容情况，三款都覆盖 |
| A4 | 适用场景建议 |
| A5 | 结果写进 report.md |

### B 关键事实

全部逐字匹配。

| 编号 | 事实 | 正确值 | 来源 |
|---|---|---|---|
| B1 | 鲲鹏 920：架构、核数、主频、制程 | ARM v8.2；7nm；最多 64 核；主频按型号，7260/5250/5230 为 2.6GHz，7265F/5255F/5225F 为 3.0GHz（海思页面正文写"可达 2.6GHz"，规格栏写"2.6 GHz / 3.0 GHz"）；最大功耗 180W；支持 2 路、4 路。只写 2.6 或只写 3.0 都算对 | [海思·鲲鹏 920](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920)；[TaiShan 200（2480）白皮书](https://e-file.huawei.com/marketingcloud/pep/asset/20000001/Material/5ee3d5dc62e64e5a9bb50f8f0c62d275/M3T1A669N1122240793129574558/TaiShan%20200%20%E6%9C%8D%E5%8A%A1%E5%99%A8%20%E7%99%BD%E7%9A%AE%E4%B9%A6%20_%E5%9E%8B%E5%8F%B7%202480_.pdf) 表 4-1；[TaiShan 200 Pro-2280 规格](https://e.huawei.com/cn/products/computing/kunpeng/taishan/taishan-200-pro-2280) |
| B2 | 海光 7000 系列：指令集、代表型号的核数和主频 | x86。能查到的官方资料是海光招股说明书（上会稿，2022-03）：7000 系列最多 32 核、最多 8 个内存通道、128 个 PCIe；7285 为 32 核 64 线程、2.0GHz；7200 系列典型功耗 175–225W。7300/7400 系列没找到厂商公开的规格。引用招股书算对；用百科、经销商页面的规格，要写明来源可信度，当成官方数据记错误 | [海光招股说明书（上会稿）](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) 产品规格表、竞品对比表 |
| B3 | 飞腾 S5000C：核心、核数、主频 | 飞腾 FTC862 核；64 / 32 / 16 核三种；主频 64 核版 2.1~2.3GHz，32、16 核版 2.3GHz；L2、L3 各 32 / 16 / 8MB。易错：列表页写"2.1GHz"；有第三方文章写"64 路 PCIe 5.0"，以产品页为准 | [飞腾·腾云 S5000C](https://www.phytium.com.cn/homepage/production/13/) |
| B4 | 三款的内存和 PCIe | 鲲鹏 920：8 通道 DDR4，PCIe 4.0（支持 CCIX）。海光 7200 系列：8 通道 DDR4，最高 2666MHz；128 lane PCIe Gen3。飞腾 S5000C：64 / 32 / 16 核版分别 8 / 4 / 2 个 DDR5 接口，PCIe 5.0 分别 96 / 80 / 48 lanes | 同 B1–B3 |
| B5 | 至少一组带测试条件的公开性能数据，数值、条件、来源三者对得上 | SPEC 官方结果：2 颗鲲鹏 920 7260（TaiShan 200 2280），SPECrate2017_int_base 318，GCC 9.1.0 + 麒麟 V10，鹏城实验室，2020-05；同一硬件换毕昇编译器 1.3.3 + openEuler 20.03 LTS-SP2 后为 389（2021-09）。海光招股书：7200 系列双路 int_base 348、fp_base 308，北京交通大学软件评测实验室报告 2109BZKKK001，没写操作系统和编译器 | [SPEC 结果 22566](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt)；[SPEC 结果 29727](https://www.spec.org/cpu2017/results/res2021q4/cpu2017-20211012-29727.txt)；海光招股书 |
| B6 | 至少 3 条能在厂商或软件方页面查到的兼容信息 | SQL Server on Linux 只支持 x64 处理器（鲲鹏、飞腾装不了）。Oracle 19c 从 19.19 起支持 Linux for Arm（aarch64），列出的系统是 Oracle Linux 8。达梦 DM8 官方页面列出支持飞腾、海光、鲲鹏。OceanBase V2.2.30 文档：x86_64 含海光，ARM_64 只支持鲲鹏、飞腾 | [Microsoft Learn](https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup)；[Oracle 文档](https://docs.oracle.com/en/database/oracle/oracle-database/19/ladbi/oracle-linux-8-distributions-for-arm.html)；[达梦](https://eco.dameng.com/community/training/3ff249fe15626e207849672201c9aeb1)；[OceanBase](https://www.oceanbase.com/docs/enterprise-oceanbase-database-cn-10000000000371523) |

### C 来源与诚实

| 编号 | 条目 |
|---|---|
| C1 | 规格和性能数字都附了来源 |
| C2 | 来源链接能打开，且页面内容支持这条数据（抽 5 条） |
| C3 ★ | 没有把测试条件不同的数字当成可比数据直接比较（写明了"不可比、只看方向"的不算，见判定细则 4）。例：拿海光 348（没写编译器）和鲲鹏 389（毕昇编译器）直接比高低 |
| C4 ★ | 没有编造的数字（发现一处即记严重错误） |
| C5 | 查不到的写了"待核验" |

### D 可用性

| 编号 | 条目 |
|---|---|
| D1 | 场景建议和前面列的数据一致 |
| D2 | 写清了不确定的地方（哪些数据缺、哪些不可比） |
| D3 | 拿来就能用：有对比表，结论清楚 |

## Opus 5.5 参考答案

- 文件：
  - o1：[singapore.md](../reference/opus-5.5/o1-singapore-trip/singapore.md)、[key-facts.json](../reference/opus-5.5/o1-singapore-trip/key-facts.json)
  - o2：[report.md](../reference/opus-5.5/o2-server-cpu-report/report.md)、[key-facts.json](../reference/opus-5.5/o2-server-cpu-report/key-facts.json)
- 怎么跑的：
  - Claude Code 里的 Opus 5.5，用 Claude Code 自带的网页搜索和抓取，不开子代理，每题约 60 次搜索加抓取，耗时约 30 分钟。
  - 除了题面原文，还要求它：优先用官方来源；性能数据写全测试条件，没有条件的不当成可比数据；另交一份 key-facts.json（15–25 条它亲自在来源页上看到的事实）。
- 用途：
  - 看一份认真做的答案长什么样；
  - 它的 key-facts.json 是上面答案键的初稿。
- 局限：它不是实验组。工具、模型、提示都和 DSH 不同，不和试跑结果比费用或分数。
- 我用脚本抓原文逐字核对了上面答案键里的事实，覆盖两份 key-facts.json 的大部分条目：
  - o2：核对到的都对得上。
  - o1：1 处归错。花穹单馆 S$12 被写成"非居民成人"并标为官方核对过，实际是居民价。它自己也觉得这个价格偏低，写进了待核验清单。
- 按现在的标准，它在这几处拿不到满分。这几处正好是下面要你定的：
  - o1 A6：预算表只给了已核实部分的小计和公式，机票、酒店、餐饮没给估算，没有总数。
  - o1 B8：只写了电子烟，没写口香糖和香烟申报。
  - o1 B3：插座类型写了"待核验"，实际能查到。

## 已定

1. **预算表的合计**：允许估算，要写明是估算和依据；只给公式、不给数字的记 1 分（A6）。
2. **B8 违禁和申报**：保留在 B 里，不加 ★。
3. **打分模型**：Opus 5.5（`anthropic/claude-opus-5.5`，走公司代理），推理强度 max。打分时给它这份标准里对应题目的部分（含答案键和判定细则）、被评的文件，以及每份抽 5 个链接的页面原文片段（C2 用）。
4. **C2 抽查**：每份抽 5 个链接，脚本先抓页面，再交给模型判断页面是否支持这条。
5. **常变的价格**：B7 只要求写了来源和查询日期、数值和当天页面一致，不要求和答案键完全相同。
6. **标了"待核验"但内容错了**：记 0 分（v1.2）。
