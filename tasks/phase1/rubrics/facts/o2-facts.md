# o2 国产服务器 CPU 选型报告：事实清单（99 条）

核对日期 2026-10-03 至 10-04。每条的标准答案都在来源页面上逐字找到过，原文摘在 `o2-facts.json` 的 `source_quote` 里，在页面的哪个位置写在 `source_locator` 里。打分规则、没收的事实、旧答案键的变化见 `o2-notes.md`。

各类条数：鲲鹏 920 规格 19；海光 7000 规格 19；飞腾 S5000C 规格 12；基准测试 25；认证与安全可靠测评 10；生态与兼容 11；其他 3。

“样本”一栏的两个数是：12 份样本报告里提到这条的份数 / 写对的份数。提到但标了“待核验”的、写错的，在括号里列出是哪几份。

## 抽查这 10 条

按种子 20261004 从 99 条里随机抽的（`random.seed(20261004); sorted(random.sample(ids, 10))`，`ids` 是 G01 到 G99）。请点开来源，对照“标准答案”和“页面上要找的原文”。

| 编号 | 问题 | 标准答案 | 页面上要找的原文 | 在页面的哪里 | 来源 |
|---|---|---|---|---|---|
| G07 | 鲲鹏 920 每颗处理器的内存通道数和内存类型 | 8 个 DDR4 通道 | Memory • 8 DDR4 Channels | 页面上“关键特性”一栏 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) |
| G23 | 海光 7000 系列单颗 CPU 最大支持多少内存 | 2 TB | 集成16-32核心,支持128路 PCIe 通道,8个 DDR4 内存通道;单颗 CPU 最大支持2 TB 内存容量 | “系列介绍”里 7000 系列那一段；页面由脚本加载，要用浏览器打开 | [来源](https://www.hygon.cn/product/cpu) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) |
| G25 | 海光 7285 的基准主频 | 2.0 GHz | 其主要参数为：32 核心、主频 2.0GHz、单核睿频加速最高 3.4GHz、三级缓存 64MB、功耗 190W。 | 海光第二轮审核问询函回复 PDF 第 93 页（页码 8-1-2-93） | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) |
| G36 | 海光官网所列 7000 系列型号（7390、7380 等）支持的 CPU 插槽数 | 1P / 2P（最多双路） | 基准时钟频率 2.7 GHz 支持的CPU插槽数 1 P/2 P 典型功耗 110 W L3 Cache 64 MB 封装 LGA | “型号规格”页，点海光7390 下面的“了解更多”，看弹出的规格卡；页面由脚本加载，要用浏览器打开 | [来源](https://www.hygon.cn/product/productlist?category=category2) |
| G39 | 飞腾腾云 S5000C 用的处理器核 | FTC862 | 核心 ｜ 飞腾自主高性能处理器核FTC862 | 产品页的“产品技术规格”表 | [来源](https://www.phytium.com.cn/homepage/production/13/) |
| G51 | SPEC CPU2017：2 颗鲲鹏 920 7260（128 核，TaiShan 200 2280）用 GCC + 麒麟 V10 跑出的 SPECrate2017_int_base | 318 | SPECrate(R)2017_int_base 318 … CPU Name: Huawei Kunpeng 920 7260 … Enabled: 128 cores, 2 chips | 纯文本结果页：分数在各项基准成绩表的最后一行，CPU 型号和核数在 HARDWARE 一节 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) |
| G67 | 168.2 这条结果的计算节点配置 | 12 个计算节点，每节点 2 颗 S5000C-E（每颗 80 核，2600 MHz），2048 GB ECC DDR5 5600MT/s；整机长城擎天 RF6260 V5；CTyunOS V4.0 25.07；KVM | type 1_Compute_nodes ｜ 12 ｜ … type 1_CPU_Type ｜ Phytium Tengyun S5000C-E ｜ type 1_CPU_Frequency_MHz ｜ 2600 ｜ type 1_CPU_Count ｜ 2 ｜ type 1_CPU_Cores_Per ｜ 80 | 结果页“Cloud Configuration”一节的 Cloud Computes Nodes 表（页面有 2 MB 以上，加载慢） | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) |
| G91 | openGauss 官方对鲲鹏、飞腾、海光的说法 | 支持鲲鹏服务器和通用 x86 服务器；在飞腾 / 海光等服务器上安装需要重新适配编译 | 统信 ubuntu / centos8 /centos10 / 红旗需要适配编译数据库；在飞腾/海光等服务器上安装需要重新适配编译。 | 常见问题页第 3 问“openGauss 有哪些版本？”前面那一段 | [来源](https://docs.opengauss.org/zh/docs/common/faq/faq.html) · [第二来源](https://docs.opengauss.org/zh/docs/2.0.0/docs/Description/%E8%BF%90%E8%A1%8C%E7%8E%AF%E5%A2%83.html) |
| G96 | 飞腾官网“软件适配认证”列表里，适配飞腾腾云 S5000C 的认证记录有多少条 | 541 条（全库 7063 条；S5000C-E 为 0 条） | 软件适配认证列表 … 适配处理器型号 … 飞腾腾云S5000C … 显示第 1 到第 10 条记录，总共 541 条记录 | “软件适配认证列表”里，在“适配处理器型号”一行点“飞腾腾云S5000C”，看表格下面的总条数；页面由脚本加载，要用浏览器打开 | [来源](https://www.phytium.com.cn/product/) |
| G97 | 鲲鹏 920 是哪一年发布的 | 2019 年（新华社通稿的日期是 2019-01-07） | 发布兼容 ARM的处理器鲲鹏 920，推出基于鲲鹏 920的TaiShan系列服务器产品和云服务。 | 华为 2019 年年度报告 PDF 第 7 页（印刷页码 05，“2019年关键业务进展”） | [来源](https://www-file.huawei.com/-/media/corporate/pdf/annual-report/annual_report_2019_cn.pdf) · [第二来源](https://en.people.cn/n3/2019/0107/c90000-9535298.html) |

抽查时注意：

- 摘录里的竖线是表格单元格的分隔，“…”是省略，都不是页面上的字符。
- 鲲鹏社区的鲲鹏 920 产品页、华为技术支持网站的用户指南、海光官网的两个页面、飞腾官网的软件适配认证列表都由脚本加载，要用浏览器打开；海光“型号规格”页还要点型号下面的“了解更多”才出完整规格。
- 海光的两份上交所披露文件是 PDF（招股说明书上会稿 380 页左右，问询回复 3 MB），页码写在“在页面的哪里”一栏。
- SPEC Cloud 的结果页很长（2 MB 以上），硬件配置在页面中部的“Cloud Configuration”一节。

## 鲲鹏 920 规格（19 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G01 | 鲲鹏 920 的指令集架构（旧键 B1） | ARMv8.2（AArch64） | 写 ARMv8.2 / ARMv8.2-A / Armv8.2 算对。只写 ARM64、aarch64、ARMv8 而没写小版本也算对。写成 ARMv8.0/8.1、ARMv9 或 x86 算错。 也算对：ARM64 / aarch64 / ARMv8（没写小版本）（架构写对即可）。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 12 / 12 |
| G02 | 鲲鹏 920 的制程工艺（旧键 B1） | 7 nm | 必须是 7 nm。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) | 12 / 11（待核验 1：D2-K8-r1） |
| G03 | 鲲鹏 920 单芯片最多多少核（旧键 B1） | 64 核 | 必须是 64。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 12 / 12 |
| G04 | 鲲鹏 920 官方标称的主频（旧键 B1） | 2.6 GHz / 3.0 GHz（7260、5250、5220、3210 为 2.6 GHz；7265F 等 F 型号为 3.0 GHz） | 只写 2.6、只写 3.0、两个都写，都算对（沿用旧键 B1）。把 3.0 GHz 写成 7260 的主频算错。 也算对：2.5 GHz（明确指 7261R / 5251R / 5221R / 3211R 这些 R 型号（鲲鹏社区规格表））。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://e.huawei.com/cn/products/computing/kunpeng/taishan/taishan-200-pro-2280) | 12 / 12 |
| G05 | 鲲鹏 920 的最大功耗（也就是 7260 的 TDP）（旧键 B1） | 180 W | 必须是 180 W。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 12 / 12 |
| G06 | 鲲鹏 920 最多支持几路互联、最多多少物理核（旧键 B1） | 最多 4 路（2S & 4S），最高 256 个物理核 | 写“最多 4 路”或“2 路/4 路”算对；写了总核数的，必须是 256。 也算对：最高 2 路（明确指 5220 / 3210（及 5221R / 3211R）；鲲鹏社区规格表写这几款“支持最高2路互联”）。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) | 12 / 12 |
| G07 | 鲲鹏 920 每颗处理器的内存通道数和内存类型（旧键 B4） | 8 个 DDR4 通道 | 通道数 8、类型 DDR4，两项都要对。写成 DDR5 算错。 也算对：4 个 DDR4 通道（明确指 5220 / 3210 等 4 通道型号）。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 12 / 12 |
| G08 | 鲲鹏 920 支持的最高内存速率 | 2933 MT/s | 写 2933（MT/s 或 MHz 都行）算对；写成“SPEC 实测配置为 DDR4-2933”也算对。 也算对：3200（明确指 TaiShan 200 Pro 2280（7265F 等 F 型号）整机的 DDR4-3200 插槽，或 SPEC Cloud 提交页里填的内存条规格）。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://support.huawei.com/enterprise/zh/doc/EDOC1100088652/ecfd64a5) | 12 / 12 |
| G09 | 鲲鹏 920 的 PCIe 代际（旧键 B4） | PCIe 4.0 | 必须是 4.0。 | [来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 12 / 12 |
| G10 | 鲲鹏 920 的 PCIe 通道（lane）数 | 40 lanes | 必须是 40。整机的 PCIe 插槽数量（例如“最多 8 个 PCIe 4.0 x8”）不算这一条。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 7 / 3（待核验 4：D1-K1-r1、D1-K1-r2、D1-K4-r2、D3-K8-r2） |
| G11 | 鲲鹏 920 7260 的核心数和主频 | 64 核，2.6 GHz | 两项都要对。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) | 12 / 12 |
| G12 | 鲲鹏 920 5250 的核心数 | 48 核 | 必须是 48。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://www.hikunpeng.com/document/detail/zh/kunpengfaq/productfaq/hardwarefaq/hardware_faq_0001.html) | 11 / 10（待核验 1：D3-K8-r1） |
| G13 | 鲲鹏 920 5220 的核心数和内存通道数 | 32 核，4 个内存通道 | 写到的每一项都要对；只写核数也算对。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://support.huawei.com/enterprise/zh/doc/EDOC1100088652/ecfd64a5) | 10 / 10 |
| G14 | 鲲鹏 920 5250 和 5220 的 TDP | 5250：150 W；5220：115 W | 写到的每一个都要对；只写其中一个也算对。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202601/002046_20260126_U5XK.pdf) | 9 / 7（待核验 2：D1-K8-r1、D2-K8-r2） |
| G15 | 鲲鹏 920 的缓存 | 每核 L1 64 KB 指令 + 64 KB 数据，L2 512 KB；L3 每核 1 MB（7260 为 64 MB，全系 24~64 MB） | 写到的每一级都要对。只写其中一级也算对。 | [来源](https://www.hikunpeng.com/zh/compute/kunpeng920) · [第二来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) | 11 / 11 |
| G16 | 鲲鹏 920 7260 支不支持超线程（SMT） | 不支持，每核 1 个线程 | 写“不支持 / 1 线程每核 / 64C64T”算对。说 7260 支持超线程或 64 核 128 线程算错。 也算对：“鲲鹏 920 系列部分型号支持 SMT”（作为系列级说法（华为常见问题页有“部分型号可以支持超线程”一句）；不能说成 7260 支持）。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.hikunpeng.com/document/detail/zh/kunpengfaq/productfaq/hardwarefaq/hardware_faq_0001.html) | 8 / 7（待核验 1：D1-K8-r2） |
| G17 | 鲲鹏 920 的虚拟化限制：支不支持 AArch32（在 KVM 里跑 32 位 Linux）、支不支持嵌套虚拟化 | 都不支持 | 写到的每一项都要对；只写其中一项也算对。 | [来源](https://www.hikunpeng.com/document/detail/zh/kunpengfaq/productfaq/hardwarefaq/hardware_faq_0001.html) | 3 / 3 |
| G18 | 鲲鹏 920 对国密 SM3/SM4 的硬件支持方式 | 集成 SM3/SM4 硬件加速器（另有 AES、SHA-2、RSA）；没有 SM3/SM4 指令 | 写“支持 SM3/SM4 硬件加解密（加速）”算对；写出“没有指令、走加速器”更完整。写“支持 SM3/SM4 指令”或“支持 SM2 硬件加速”算错。 | [来源](https://www.hikunpeng.com/document/detail/zh/kunpengfaq/productfaq/hardwarefaq/hardware_faq_0001.html) · [第二来源](https://www.hikunpeng.com/zh/compute/kunpeng920) | 11 / 11 |
| G19 | 鲲鹏 920 旧型号 6426、4826 现在对应哪两个型号 | 6426 → 7260，4826 → 5250 | 两组对应都要对。3226 对应哪个型号不判（见说明）。 | [来源](https://support.huawei.com/enterprise/zh/doc/EDOC1100088652/ecfd64a5) | 7 / 6（待核验 1：D0-r1） |

## 海光 7000 规格（19 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G20 | 海光 7000 系列的指令集（旧键 B2） | x86（x86-64） | 写 x86 / x86-64 / x86_64 / C86 算对。 | [来源](https://www.hygon.cn/product/cpu) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 12 / 12 |
| G21 | 海光官网和招股书给出的 7000 系列单颗最多核心数（旧键 B2） | 32 核 | 写“16–32 核”或“最多 32 核”算对。 也算对：64 核（明确指海光四号 C86-4G（如 7490 / 7480），来源是 SPEC 提交页或整机配置，见 G37）。 | [来源](https://www.hygon.cn/product/cpu) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 12 / 12 |
| G22 | 海光 7000 系列最多支持多少个内存通道、多少个 PCIe 通道（旧键 B2/B4） | 8 个内存通道，128 个 PCIe 通道 | 写到的每一项都要对。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) · [第二来源](https://www.hygon.cn/product/cpu) | 11 / 11 |
| G23 | 海光 7000 系列单颗 CPU 最大支持多少内存 | 2 TB | 必须是 2 TB（每颗）。 | [来源](https://www.hygon.cn/product/cpu) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 8 / 8 |
| G24 | 海光 7285 的核心数和线程数（旧键 B2） | 32 核 64 线程 | 核数必须是 32；写了线程数的必须是 64。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 11 / 11 |
| G25 | 海光 7285 的基准主频（旧键 B2） | 2.0 GHz | 必须是 2.0 GHz。 也算对：3.4 GHz（明确写的是单核睿频（最高加速频率））。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 10 / 10 |
| G26 | 海光 7285 的功耗（或 7200 系列的典型功耗）（旧键 B2） | 7285：190 W；7200 系列典型功耗 175–225 W | 写 190 W（7285）或 175–225 W（7200 系列）任意一个都算对；两个都写的都要对。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 9 / 8（待核验 1：D3-K8-r1） |
| G27 | 海光 7285 的制程工艺 | 14 nm | 必须是 14 nm，而且说的是 7285（海光二号）。把 14 nm 写在 73xx / 74xx 头上的，不算提到这一条。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) | 8 / 3（待核验 5：D0-r1、D0-r2、D1-K4-r2、D2-K8-r2、D3-K8-r2） |
| G28 | 海光 7200 系列（含 7285）的内存最高频率和 PCIe 代际（旧键 B4） | DDR4 最高 2666 MHz；PCIe Gen3（128 lane） | 写到的每一项都要对。 也算对：DDR4-2933（写明是 SPEC Cloud 提交页或采购记录里整机配的内存条，不是 CPU 规格（D0-r1、D3-K8-r1 是这种写法））。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 10 / 10 |
| G29 | 海光 7285 的发布时间 | 2020 年第一季度 | 写 2020 年第一季度 / 2020Q1 / 2020 年初 算对。 也算对：2020 年 1 月量产（招股书：“2020 年 1 月，海光二号实现量产”）。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 6 / 5（待核验 1：D0-r1） |
| G30 | 海光一号、海光二号分别对应哪些型号系列 | 海光一号：31xx / 51xx / 71xx；海光二号：32xx / 52xx / 72xx | 写到的对应关系都要对；只写 7000 系列的那一半（71xx = 一号，72xx / 7285 = 二号）也算对。73xx = 三号、74xx = 四号招股书没写，不判。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 9 / 8（待核验 1：D2-K8-r1） |
| G31 | 海光 7390 的核心数和线程数 | 32 核 64 线程 | 核数必须是 32；写了线程数的必须是 64。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 11 |
| G32 | 海光 7390 的基准主频和最大加速频率 | 基准 2.7 GHz，最大加速 3.3 GHz | 写到的每一项都要对；只写基准 2.7 GHz 也算对。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 11 |
| G33 | 海光 7390 的内存规格 | DDR4，最高 3200 MHz，8 通道 | 写到的每一项都要对。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 11 |
| G34 | 海光 7390 的 PCIe 规格 | PCIe 4.0，128 条通道 | 代际必须是 4.0；写了通道数的必须是 128。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 10（待核验 1：D1-K8-r1） |
| G35 | 海光 7380 的基准主频和最大加速频率 | 基准 2.2 GHz，最大加速 3.0 GHz | 写到的每一项都要对；只写基准 2.2 GHz 也算对。把 3.0 GHz 写成“主频”而不说明是最高/加速频率，算错（归错）。 样本里的错法：主频 3.0 GHz（D0-r1）。 样本里的错法：加速频率 2.5 GHz（D3-K8-r1）。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 9（写错 2：D0-r1、D3-K8-r1） |
| G36 | 海光官网所列 7000 系列型号（7390、7380 等）支持的 CPU 插槽数 | 1P / 2P（最多双路） | 写“1P/2P”“最多 2 路”“双路”算对。 | [来源](https://www.hygon.cn/product/productlist?category=category2) | 11 / 6（待核验 5：D0-r1、D1-K1-r1、D1-K4-r2、D1-K8-r1、D2-K8-r2） |
| G37 | 海光 C86-4G（OPN 7490）每颗多少核 | 64 核（每核 2 线程） | 核数必须是 64；写了线程的，必须是每核 2 线程 / 128 线程。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q1/cloudiaas2018-20251201-00035.html) · [第二来源](https://www.spec.org/virt_sc2013/results/res2026q1/virt_sc2013-20260118-00157-perf.html) | 12 / 11（待核验 1：D2-K8-r1） |
| G38 | 海光 C86-4G（OPN 7490）用什么内存 | DDR5 | 必须是 DDR5。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q1/cloudiaas2018-20251201-00035.html) · [第二来源](https://www.spec.org/virt_sc2013/results/res2026q1/virt_sc2013-20260118-00157-perf.html) | 12 / 10（待核验 2：D2-K8-r1、D3-K8-r2） |

## 飞腾 S5000C 规格（12 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G39 | 飞腾腾云 S5000C 用的处理器核（旧键 B3） | FTC862 | 必须是 FTC862。写 FTC860 / FTC870 / FTC663 算错。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G40 | 飞腾腾云 S5000C 的指令集 | 兼容 ARMv8 | 写 ARMv8 / ARM64 / aarch64 算对。 也算对：ARMv8.2（国资委《中央企业科技创新成果推荐目录（2024年版）》写“兼容ARMv8.2指令集规范”）。 | [来源](https://www.phytium.com.cn/homepage/production/13/) · [第二来源](http://www.sasac.gov.cn/n4470048/n32559362/n35167919/n35167924/n35167949/c35256513/content.html) | 12 / 12 |
| G41 | 飞腾腾云 S5000C 有哪几种核数形态（旧键 B3） | 64 核、32 核、16 核三种 | 三种都列出，或只说“最高 64 核”，都算对。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G42 | 飞腾腾云 S5000C 的主频（旧键 B3） | 64 核版 2.1~2.3 GHz；32 核、16 核版 2.3 GHz | 64 核版写 2.1~2.3 GHz 或 2.1 GHz 都算对；写了 32 核、16 核版的，必须是 2.3 GHz。把 S5000C-E 的 2.6 GHz 写成 S5000C 的主频算错。64 核版只写 2.3 GHz 的不判。 也算对：64 核版 2.1 GHz（不要求注明出处；国资委目录和兆芯问询回复都这样写）。 | [来源](https://www.phytium.com.cn/homepage/production/13/) · [第二来源](http://www.sasac.gov.cn/n4470048/n32559362/n35167919/n35167924/n35167949/c35256513/content.html) | 12 / 12 |
| G43 | 飞腾腾云 S5000C 的二级、三级缓存（旧键 B3） | 64 / 32 / 16 核版：L2 32 / 16 / 8 MB，L3 32 / 16 / 8 MB | 写到的每一项都要对；只写 64 核版（L2 32 MB、L3 32 MB）也算对。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G44 | 飞腾腾云 S5000C 的内存接口（旧键 B4） | 64 / 32 / 16 核版分别有 8 / 4 / 2 个 DDR5 接口 | 类型必须是 DDR5；写到的接口数都要对；只写 64 核版的 8 个也算对。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G45 | 飞腾腾云 S5000C 的 PCIe 规格（旧键 B4） | PCIe 5.0；64 / 32 / 16 核版分别 96 / 80 / 48 lanes | 代际必须是 5.0；写到的通道数都要对；只写 64 核版的 96 lanes 也算对。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G46 | 飞腾腾云 S5000C 的多路支持 | 最多 128 核心互联（64 核版即双路） | 写“最多 128 核心互联”算对；说 64 核版最多双路也算对。说 64 核版支持 4 路或更多（超过 128 核）算错。32 核、16 核版按 128 核上限推出的 4 路、8 路不算错。 | [来源](https://www.phytium.com.cn/homepage/production/13/) | 12 / 12 |
| G47 | 飞腾腾云 S5000C-E 最多多少核 | 80 核 | 必须是 80。 | [来源](https://www.phytium.com.cn/homepage/production/18/) | 12 / 12 |
| G48 | 飞腾腾云 S5000C-E 的主频 | ≥2.6 GHz | 写 ≥2.6 GHz 或 2.6 GHz 算对。 | [来源](https://www.phytium.com.cn/homepage/production/18/) · [第二来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) | 12 / 12 |
| G49 | 飞腾腾云 S5000C-E 的内存接口和 PCIe 规格 | 8 个 DDR5 接口；48 lanes PCIe 5.0 | 写到的每一项都要对。 | [来源](https://www.phytium.com.cn/homepage/production/18/) | 12 / 12 |
| G50 | 飞腾腾云 S5000C-E 的多路支持 | 2~4 路互联 | 写 2~4 路 / 最多 4 路算对。 | [来源](https://www.phytium.com.cn/homepage/production/18/) | 12 / 12 |

## 基准测试（25 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G51 | SPEC CPU2017：2 颗鲲鹏 920 7260（128 核，TaiShan 200 2280）用 GCC + 麒麟 V10 跑出的 SPECrate2017_int_base（旧键 B5） | 318 | 分数必须是 318（带小数的写法四舍五入后是 318 也算对），而且对应的是 2 路 128 核。把 318 说成 4 路或单路的成绩算错。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) | 10 / 10 |
| G52 | 318 这条成绩的编译器、操作系统和测试时间（旧键 B5） | GCC 9.1.0；kylin release 10（银河麒麟 V10）；Test date May-2020，2020-06-30 发布 | 写到的每一项都要对；只写其中一两项也算对。编译器写 GCC 9.1 即可。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) | 10 / 9（待核验 1：D1-K1-r1） |
| G53 | 鲲鹏 920 这几条 SPEC CPU2017 结果的 Test Sponsor / 测试方是谁 | 鹏城实验室（Peng Cheng Laboratory） | 写鹏城实验室算对。把华为写成 Test Sponsor 算错（华为是硬件厂商）。 样本里的错法：测试方鹏城实验室、赞助方（Sponsor）华为（D3-K8-r1）。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=SPONSOR&pattern=Peng+Cheng&icase=1) | 10 / 9（写错 1：D3-K8-r1） |
| G54 | SPEC CPU2017：同一平台（2 颗 7260）换毕昇编译器 + openEuler 后的 SPECrate2017_int_base（旧键 B5） | 389 | 分数必须是 389，对应 2 路 128 核。 | [来源](https://www.spec.org/cpu2017/results/res2021q4/cpu2017-20211012-29727.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) | 11 / 11 |
| G55 | 389 这条成绩的编译器、操作系统和测试时间（旧键 B5） | 毕昇编译器 BiSheng 1.3.3；openEuler 20.03 (LTS-SP2)；Test date Sep-2021 | 写到的每一项都要对；只写其中一两项也算对。 也算对：2021-10（页脚的运行时间戳是 2021-10-12（D0-r2、D3-K8-r1 这么写））。 也算对：2021-11（写明是发布时间）。 | [来源](https://www.spec.org/cpu2017/results/res2021q4/cpu2017-20211012-29727.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) | 11 / 11 |
| G56 | SPEC CPU2017：4 颗鲲鹏 920 7260（256 核，TaiShan 200 2480）的 SPECrate2017_int_base | 628 | 分数必须是 628（带小数的写法四舍五入后是 628 也算对），对应 4 路 256 核。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22564.txt) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) | 12 / 12 |
| G57 | SPEC CPU2017：2 颗鲲鹏 920 7260 的 SPECrate2017_fp_base（有两条） | 263 和 257 | 写其中任意一条或两条都算对（带小数的写法四舍五入后对得上也算对），对应 2 路 128 核。 | [来源](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200621-22956.txt) · [第二来源](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200622-23015.txt) | 11 / 11 |
| G58 | SPEC CPU2017：4 颗鲲鹏 920 7260 的 SPECrate2017_fp_base（有两条） | 516 和 501 | 写其中任意一条或两条都算对（带小数的写法四舍五入后对得上也算对），对应 4 路 256 核。 | [来源](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200621-22957.txt) · [第二来源](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200622-23014.txt) | 11 / 11 |
| G59 | SPEC CPU2017 官方结果库里鲲鹏的结果一共几条 | 7 条（int rate 3 条：318、389、628；fp rate 4 条：263、257、516、501；全部是 7260） | 必须是 7。只列出其中几条但没说“一共几条”的，不算提到这一条。 样本里的错法：两项（int_rate base），未包含 fp_rate 成绩（D2-K8-r1）。 | [来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Kunpeng&icase=1) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=SYSTEM&pattern=TaiShan&icase=1) | 10 / 9（写错 1：D2-K8-r1） |
| G60 | SPEC CPU2017 官方结果库里海光、飞腾各有几条结果 | 都是 0 条 | 写“没有 / 未检索到 / 0 条”算对。给出海光或飞腾的 SPEC 官网 CPU2017 成绩算错（招股书里的 348/308 不是 SPEC 官网结果）。 | [来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Hygon&icase=1) · [第二来源](https://www.spec.org/cgi-bin/osgresults?conf=cpu2017&op=fetch&field=CPU&pattern=Phytium&icase=1) | 12 / 12 |
| G61 | 鲲鹏 920 这几条 SPEC CPU2017 结果的内存配置 | 2 路的四条（318、389、263、257）都是 512 GB（16 × 32 GB）；4 路的三条（628、516、501）都是 1 TB（32 × 32 GB）；都是 PC4-2933 | 写到的每一条都要对。 样本里的错法：318 那条的内存写成 1 TB（D3-K8-r2）。 样本里的错法：7 条结果的内存都写成 512 GB（D2-K8-r2）。 | [来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22566.txt) · [第二来源](https://www.spec.org/cpu2017/results/res2020q2/cpu2017-20200529-22564.txt) | 11 / 9（写错 2：D2-K8-r2、D3-K8-r2） |
| G62 | 海光招股书披露的海光 7200 系列（7285）双路 SPECrate2017_int_base / fp_base（旧键 B5） | 348 / 308 | 两个数都要对，并且是双路（2 颗处理器）。必须说明出自招股书或问询回复，不是 SPEC 官网结果；当成 SPEC 官网结果写算错。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) · [第二来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) | 9 / 9 |
| G63 | 348 / 308 这组数据出自哪份测试报告（旧键 B5） | 北京交通大学软件评测实验室出具的《测试报告》，报告编号 2109BZKKK001（招股书的表注） | 写出北京交通大学软件评测实验室或报告编号算对。只写“招股书披露 / 厂商自测”的，不算提到这一条。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 6 / 6 |
| G64 | 海光招股书拿 7285 和 Intel 至强铂金比较时，Intel 的数字是怎么来的 | Intel 只有 4 路成绩，按约 2 倍（1.97–2.01 倍）折算成双路后再比 | 写出“4 路成绩折算成双路”算对。把折算后的 392 / 329 等当成 Intel 的双路实测成绩且不提折算，不算提到这一条。 | [来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 6 / 6 |
| G65 | SPEC Cloud IaaS 2018：飞腾腾云 S5000C-E 平台（中国电信天翼云 TeleCloudOS V4.0）的 Performance Score | 168.2 | 必须是 168.2。必须说明这是云平台整体成绩；当成单颗 CPU 的跑分去比，按 C3 判。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) · [第二来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) | 11 / 11 |
| G66 | 168.2 这条结果的副本数、相对扩展性、平均实例开通时间 | 160 copies；85.9%；47 s | 写到的每一项都要对。总实例数 1039，写了也要对。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) · [第二来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) | 11 / 11 |
| G67 | 168.2 这条结果的计算节点配置 | 12 个计算节点，每节点 2 颗 S5000C-E（每颗 80 核，2600 MHz），2048 GB ECC DDR5 5600MT/s；整机长城擎天 RF6260 V5；CTyunOS V4.0 25.07；KVM | 写到的每一项都要对；不要求写全。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) | 11 / 11 |
| G68 | 168.2 这条结果页上的 Test Date | 2026-03-30 | 写 2026-03-30 或 2026 年 3 月算对。 也算对：2026 年 5 月（写明是提交 / 实际运行时间）。 也算对：2026 年第二季度（写明是发布季度）。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) | 10 / 10 |
| G69 | SPEC Cloud IaaS 2018：海光 C86-4G（OPN 7490）平台（浪潮 InCloudOS V8）的 Performance Score | 154.9 | 必须是 154.9。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q1/cloudiaas2018-20251201-00035.html) · [第二来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) | 9 / 9 |
| G70 | 154.9 这条结果的条件 | 126 copies；相对扩展性 91.6%；平均开通 27 s；9 个计算节点，每节点 2 颗 × 64 核、3000 MHz；Test Date 2025-10-29；KOS 5.8 | 写到的每一项都要对；不要求写全。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2026q1/cloudiaas2018-20251201-00035.html) · [第二来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) | 9 / 9 |
| G71 | SPEC Cloud IaaS 2018：鲲鹏 920 在 2025 年的两条结果 | 153.7（鲲鹏 920-7260，山东大学 ICP 3.7，136 copies，95.2%，30 s）；148.6（鲲鹏 920-7260T，中国电信 TeleCloudOS 4.0，125 copies，89.0%，29 s） | 写到的每一个数都要对，并且和各自的平台对得上；只写其中一条也算对。测试日期不判（见说明）。 | [来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) · [第二来源](https://www.spec.org/cloud_iaas2018/results/res2025q4/cloudiaas2018-20250818-00034.html) | 8 / 8 |
| G72 | SPEC Cloud IaaS 2018：2022 年含海光 7285 的那条浪潮结果（48.7 分），计算节点是什么 | 混合平台：7 台 Intel Xeon Gold 5218，加 1 台海光 C86 7285、1 台飞腾 S2500 | 分数必须是 48.7；必须说明是混合平台或主体是 Intel 节点。把 48.7 当成海光 7285 的成绩且不加说明，算错。 | [来源](https://www.spec.org/cloud_iaas2018/results/res2023q1/cloudiaas2018-20221117-00017.html) · [第二来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) | 5 / 5 |
| G73 | 截至 2026 年 10 月初，SPEC Cloud IaaS 2018 已公布结果里最高的 Performance Score | 168.2（飞腾 S5000C-E 平台；共 19 条结果，次高是海光 C86-4G 的 154.9） | 写“已公布结果中最高 / 第一”算对。写了次高或条数的，也要对。 | [来源](https://www.spec.org/cloud_iaas2018/results/cloud_iaas2018/) · [第二来源](https://www.spec.org/cloud_iaas2018/results/res2026q2/cloudiaas2018-20260508-00037.html) | 10 / 9（待核验 1：D1-K8-r1） |
| G74 | SPECvirt_sc2013：鲲鹏 920 双路服务器（武汉长江计算 R220K V2）的成绩 | 1509 @ 84 VMs | 两个数都要对。 | [来源](https://www.spec.org/virt_sc2013/results/res2024q4/virt_sc2013-20241106-00145-perf.html) · [第二来源](https://www.spec.org/virt_sc2013/results/specvirt_sc2013_perf.html) | 3 / 3 |
| G75 | 海思官网宣称的鲲鹏 920 SPECint 分数 | 超过 930（英文页写的是 estimated，基准是 SPECint_rate_base2006；页面没给测试条件） | 写“超过 930 / 930+”并标明是厂商宣称算对。把它说成 SPEC 官网已发布成绩，或说成 SPEC CPU2017 分数，算错。 | [来源](https://www.hisilicon.com/en/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) · [第二来源](https://www.hisilicon.com/cn/products/kunpeng/huawei-kunpeng/huawei-kunpeng-920) | 10 / 10 |

## 认证与安全可靠测评（10 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G76 | 安全可靠测评：鲲鹏 920 的等级和所在公告 | Ⅰ 级；2023 年第 1 号（2023-12-26） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 把鲲鹏 920 V200 的 Ⅱ 级写成鲲鹏 920 的等级算错。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202312/t20231226_162074.html) | 6 / 3（待核验 3：D1-K1-r1、D1-K4-r1、D1-K8-r1） |
| G77 | 安全可靠测评：鲲鹏 920 V200 的等级和所在公告 | Ⅱ 级；2024 年第 1 号（2024-05-20） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202405/t20240520_172866.html) | 5 / 5 |
| G78 | 安全可靠测评：海光 2 号 C86（含 7285 / 7280 / 7260 / 7250）的等级和所在公告 | Ⅰ 级；2023 年第 1 号（2023-12-26） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202312/t20231226_162074.html) | 7 / 4（待核验 3：D1-K1-r1、D1-K4-r1、D1-K8-r1） |
| G79 | 安全可靠测评：海光 C86-3G 的等级和所在公告 | Ⅰ 级；2023 年第 1 号（2023-12-26） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202312/t20231226_162074.html) | 7 / 4（待核验 3：D1-K1-r1、D1-K4-r1、D1-K8-r1） |
| G80 | 安全可靠测评：海光 C86-4G 的等级和所在公告 | Ⅱ 级；2024 年第 1 号（2024-05-20） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202405/t20240520_172866.html) | 7 / 5（待核验 2：D1-K4-r1、D1-K8-r1） |
| G81 | 安全可靠测评：海光 C86-4G-L 的等级和所在公告 | Ⅰ 级；2024 年第 1 号（2024-05-20） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202405/t20240520_172866.html) | 5 / 5 |
| G82 | 安全可靠测评：飞腾腾云 S5000C 的等级和所在公告 | Ⅱ 级；2024 年第 1 号（2024-05-20） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202405/t20240520_172866.html) | 7 / 6（待核验 1：D1-K8-r1） |
| G83 | 安全可靠测评：飞腾腾云 S5000C-E 的等级和所在公告 | Ⅱ 级；2025 年第 1 号（2025-03-14） | 等级必须对。写了公告批次或日期的，也要对；没写批次不扣。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202503/t20250314_216512.html) | 6 / 6 |
| G84 | 安全可靠测评结果的有效期 | 自发布之日起三年 | 必须是三年。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202312/t20231226_162074.html) | 4 / 4 |
| G85 | 安全可靠测评 2026 年第 3 号（2026-09-20）里华为、海光的服务器 CPU 及其等级 | 鲲鹏 950：Ⅲ 级；海光 C86-4G/H：Ⅱ 级 | 写到的每一项都要对；只写其中一项也算对。 | [来源](https://www.itsec.gov.cn/aqkkcp/cpgg/202609/t20260920_275291.html) | 2 / 2 |

## 生态与兼容（11 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G86 | Microsoft SQL Server 对处理器架构的要求（鲲鹏、飞腾能不能装）（旧键 B6） | 只支持 x64；ARM 平台（鲲鹏、飞腾）不受支持 | 写“仅 x64 / x86-64，ARM 上没有官方版本”算对。说 SQL Server 有鲲鹏或飞腾可用的官方版本算错。 | [来源](https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup) · [第二来源](https://learn.microsoft.com/en-us/sql/sql-server/install/hardware-and-software-requirements-for-installing-sql-server-2022) | 12 / 11（待核验 1：D1-K4-r1） |
| G87 | Oracle Database 19c 有没有官方的 Linux for Arm（aarch64）版本，从哪个版本起、最低什么操作系统（旧键 B6） | 有；自 19c Release 19.19 起；最低 Oracle Linux 8.6 + UEK7 | 写“有官方 ARM 版”算对；写了起始版本的必须是 19.19；写了操作系统的必须是 Oracle Linux 8（8.6 + UEK7）。说 Oracle 官方不支持 ARM Linux 算错。 样本里的错法：Oracle 本地部署版未官方支持 ARM Linux（D1-K8-r1）。 | [来源](https://docs.oracle.com/en/database/oracle/oracle-database/19/ladbi/oracle-linux-8-distributions-for-arm.html) | 12 / 11（写错 1：D1-K8-r1） |
| G88 | Oracle Database 19c Linux for Arm 版对 CPU 的要求 | 要求具备 Neoverse N1 能力的 CPU；Oracle 推荐 Ampere Altra / Altra Max | 写出 Neoverse N1 算对。由此推出“鲲鹏 920、飞腾不在 Oracle 推荐/认证范围”也算对。 | [来源](https://docs.oracle.com/en/database/oracle/oracle-database/19/ladbi/server-hardware-checklist-for-oracle-database-installation.html) | 8 / 8 |
| G89 | 达梦 DM8 支持哪些国产 CPU 平台（三家在不在内）（旧键 B6） | 飞腾、海光、鲲鹏都在支持之列（另有龙芯、申威、兆芯等） | 写三家都支持算对。引用达梦别的官方材料（样本里有引英文白皮书的）说三家都支持，也算对。只确认了其中一两家、其余写待核验的，按“待核验”记。 | [来源](https://eco.dameng.com/community/training/3ff249fe15626e207849672201c9aeb1) | 12 / 7（待核验 5：D1-K4-r1、D1-K8-r2、D2-K8-r1、D2-K8-r2、D3-K8-r2） |
| G90 | OceanBase 官方文档列出的服务器架构（三家在不在内）（旧键 B6） | x86_64（包括海光）；ARM_64（鲲鹏、飞腾） | 写三家都在官方支持矩阵里算对。只确认了其中一两家、其余写待核验的，按“待核验”记。 | [来源](https://www.oceanbase.com/docs/enterprise-oceanbase-database-cn-10000000000371523) · [第二来源](https://www.oceanbase.com/docs/common-oceanbase-database-cn-10000000001576706) | 12 / 3（待核验 9：D0-r1、D1-K1-r1、D1-K1-r2、D1-K4-r1、D1-K8-r1、D1-K8-r2、D2-K8-r1、D3-K8-r1、D3-K8-r2） |
| G91 | openGauss 官方对鲲鹏、飞腾、海光的说法 | 支持鲲鹏服务器和通用 x86 服务器；在飞腾 / 海光等服务器上安装需要重新适配编译 | 写出“飞腾 / 海光需要重新适配编译”算对。只写“openGauss 支持鲲鹏”的，不算提到这一条。说 openGauss 官方明确支持飞腾（不需适配）算错。 | [来源](https://docs.opengauss.org/zh/docs/common/faq/faq.html) · [第二来源](https://docs.opengauss.org/zh/docs/2.0.0/docs/Description/%E8%BF%90%E8%A1%8C%E7%8E%AF%E5%A2%83.html) | 9 / 4（待核验 5：D0-r1、D1-K4-r1、D1-K8-r2、D2-K8-r1、D3-K8-r2） |
| G92 | 银河麒麟高级服务器操作系统 V10 SP3（2403）发布说明列出的三家处理器型号 | 飞腾：FT-2000+/64、腾云 S2500、腾云 S5000C；鲲鹏：920、920 V200；海光：海光 1 号、海光 2 号、C86-3G、C86-4G | 写到的型号都要在这个清单里。只说“麒麟 V10 SP3 支持飞腾 / 鲲鹏 / 海光”（家族级）也算对。说 2403 这一版的发布说明列了 S5000C-E 才算错（S5000C-E 在 V11 的发布说明里，见下一条）；笼统地说“麒麟 V10 SP3 / V11 支持 S5000C-E”不算错。 | [来源](https://www.kylinos.cn/issueNote/serverNote/2068954413609967617.html) | 12 / 10（待核验 2：D1-K1-r2、D3-K8-r2） |
| G93 | 银河麒麟高级服务器操作系统 V11 支不支持飞腾 S5000C-E | 支持（V11 2503 的架构支持里列了 S5000C、S5000C-E） | 写 V11 支持 S5000C-E 算对。 | [来源](https://www.kylinos.cn/issueNote/serverNote/2066705970141257729.html) · [第二来源](https://www.phytium.com.cn/os_system/view/?category=4) | 7 / 7 |
| G94 | VMware ESXi 正式版支持什么处理器（鲲鹏、飞腾能不能装） | ESXi 8.0 的硬件要求只列 64 位 x86 处理器；鲲鹏、飞腾（ARM）不在其中 | 写“ESXi 仅支持 x86 / ARM 不受正式支持”算对。提到实验性的 ESXi-Arm Fling 不扣分（Fling 的现状这次没有核对）。说 ESXi 正式支持鲲鹏或飞腾算错。 | [来源](https://techdocs.broadcom.com/cn/zh-cn/vmware-cis/vsphere/vsphere/8-0/esx-upgrade/upgrading-esxi-hosts-upgrade/esxi-requirements-upgrade/esxi-hardware-requirements-upgrade.html) | 12 / 8（待核验 4：D0-r1、D1-K4-r1、D2-K8-r1、D3-K8-r2） |
| G95 | 微软 Windows Server 对海光处理器的官方支持情况 | 只有 Windows Server 2019 的处理器要求里列了 Hygon C86 7xxx，并注明仅限中国市场；2012 R2、2016、2022、2025 都是 N/A | 写“仅 Windows Server 2019 列了海光”算对。引用海光问询回复“2018 年 10 月获 Windows Server 2019 认证”也算对。说微软的支持列表里完全没有海光算错。 | [来源](https://learn.microsoft.com/en-us/windows-hardware/design/minimum/windows-processor-requirements) · [第二来源](http://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220304_5PQP.pdf) | 12 / 4（待核验 8：D0-r1、D0-r2、D1-K1-r1、D1-K1-r2、D1-K4-r2、D1-K8-r2、D2-K8-r1、D3-K8-r2） |
| G96 | 飞腾官网“软件适配认证”列表里，适配飞腾腾云 S5000C 的认证记录有多少条 | 541 条（全库 7063 条；S5000C-E 为 0 条） | 写 541 算对。报告注明了查询日期且数字相差不到 10，也算对。 | [来源](https://www.phytium.com.cn/product/) | 3 / 3 |

## 其他（3 条）

| 编号 | 问题 | 标准答案 | 怎么算对 | 来源 | 样本：提到 / 写对 |
|---|---|---|---|---|---|
| G97 | 鲲鹏 920 是哪一年发布的 | 2019 年（新华社通稿的日期是 2019-01-07） | 年份必须是 2019。写 2019 年 1 月或 2019-01-07 也算对。写了别的月份、日子的不判（厂商来源只到年份）。 | [来源](https://www-file.huawei.com/-/media/corporate/pdf/annual-report/annual_report_2019_cn.pdf) · [第二来源](https://en.people.cn/n3/2019/0107/c90000-9535298.html) | 8 / 8 |
| G98 | 海光被列入美国实体清单的时间 | 2019 年 6 月（2019-06-24 生效） | 写 2019 年 6 月或 2019-06-24 算对。 | [来源](https://www.federalregister.gov/documents/full_text/text/2019/06/24/2019-13245.txt) · [第二来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 5 / 5 |
| G99 | 海光 CPU 的技术来源 | 基于 AMD 授权技术（2016 年 3 月启动海光一号设计）；被列入实体清单后 AMD 不再提供技术服务，后续自行迭代 | 写“AMD 授权 / 源自 AMD Zen”算对。 | [来源](https://static.sse.com.cn/stock/disclosure/announcement/c/202203/001043_20220307_T2KW.pdf) | 10 / 9（待核验 1：D2-K8-r1） |
