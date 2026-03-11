# Rule Horizon Mapping for Crypto 4h

Date: 2026-03-10
Category: alpha-models

## 研究问题

rule / grammar generator 的 classic windows 应该怎么映射到 crypto 4h。哪些映射是资料直接支持的，哪些只能算项目推断。

## 核心结论

1. 公开资料支持两种合法思路：
   - **native intraday windows**
   - **classic daily windows**
2. 公开资料**不支持**“存在一个统一、唯一正确的 4h 映射”。
3. 对当前项目，最严谨的做法不是直接拍定唯一映射，而是把 rule horizons 分成两组并行：
   - intraday-native group
   - daily-classic group
4. 因此，rule / grammar generator v1 的 horizon 设计应是：
   - 不是单网格
   - 而是两组 whitelist

## Source-Backed

### 1. 公开 crypto 研究直接支持 native intraday windows

Resta, Pagnottoni, De Giuli (2020) 在 Bitcoin 技术分析研究里，明确把 intraday 与 daily 分开定义：

- `SMA12`, `EMA12`
- `SMA24`, `EMA24`
- `SMA72`, `EMA72`

而且文中直接解释：

- 在 5-minute 数据下，12 表示 12 个 time units
- 72 表示 72 个 time units
- 在 daily 数据下，24 表示 24 天

这说明对 intraday 频率，研究里常直接使用 **native time-unit windows**，而不是强行把 daily 窗口线性映射成分钟数。

来源：

- Technical Analysis on the Bitcoin Market: Trading Opportunities or Investors’ Pitfall?
  - https://www.mdpi.com/2227-9091/8/2/44
  - 文中说明 `SMA12/SMA24/SMA72`、`EMA12/EMA24/EMA72` 在 5-minute 和 daily 下分别按 time units / days 定义。

### 2. 公开资料也支持 classic daily windows 作为另一组 technical-rule horizons

早期和后续技术交易规则文献长期反复使用：

- `20`
- `50`
- `60`
- `150`
- `200`

这些属于 classic daily technical-rule windows。

来源：

- The profitability of simple moving averages and trading range breakout in the Asian stock markets
  - 20 / 60 等典型窗口
- 其他技术规则研究与我们先前的 formula-level 调研
  - 150 / 200 也反复出现

### 3. 2024 Bitcoin 技术规则大样本研究支持“多频率并行 + 多类规则并行”

Deprez & Frömmel (2024) 的研究明确：

- 同时使用 daily 和 intraday frequencies
- 同时使用多类 technical trading rules
- 最终不是先验决定唯一频率，而是做大范围规则池筛选

来源：

- Are simple technical trading rules profitable in bitcoin markets?
  - https://doi.org/10.1016/j.iref.2024.05.003

这说明：

- “单一 horizon 预设唯一正确”并不是公开研究更支持的路线
- “分组并行，再筛选”更接近研究现实

## 当前能直接得出的结构

### A. Native Intraday Group

source-backed 例子：

- `12`
- `24`
- `72`

它们的含义是：

- 用当前数据频率本身的 time units 定义规则尺度

如果映射到 4h：

- `12 bars`
- `24 bars`
- `72 bars`

这是**从 intraday-native 定义延伸到 4h 的直接形式**，属于合理延伸。

### B. Classic Daily Group

source-backed 例子：

- `20`
- `50`
- `60`
- `150`
- `200`

它们的含义是：

- classic daily technical-rule windows

如果映射到 4h：

- 需要额外决定：
  - 是否按 calendar-equivalent 转成 bars
  - 还是保留 daily frequency 独立实现

这里公开资料没有给出唯一答案。

## What Is Source-Backed vs Inference

### Source-backed

- intraday 规则可以直接用 native time-unit windows
- daily 规则可以直接用 classic daily windows
- 多频率并行筛选是合理路径

### Project-specific inference

下面这些都不是知识库直接定稿：

- `20d -> 120 bars`
- `50d -> 300 bars`
- `150d -> 900 bars`
- `200d -> 1200 bars`

这些属于 **calendar-equivalent mapping**，逻辑上合理，但不是当前知识库里被论文直接定死的答案。

## 对当前项目的直接含义

如果我们现在要做 rule / grammar generator v1，最严谨的 horizon 设计不该是：

- 直接选一套单独的 4h 窗口

而应该是：

### Group 1: native intraday horizons

- `12`
- `24`
- `72`

### Group 2: classic daily horizons

- `20`
- `50`
- `60`
- `150`
- `200`

然后再决定两种实现路线中的一种：

1. 直接在 4h bar 上实现这两组窗口
2. 对 daily-classic group 单独做 calendar-equivalent bar mapping

其中：

- Group 1 更靠近 source-backed intraday 文献
- Group 2 更靠近 source-backed classic technical-rule 文献

## 最稳的 v1 结论

知识库当前最支持的，不是“唯一映射”，而是：

- **双组 horizon whitelist**

即：

- `native intraday`: `12 / 24 / 72`
- `classic daily`: `20 / 50 / 60 / 150 / 200`

这样做的好处是：

- 不伪装成已经有唯一正确的 4h 映射
- 同时保留 intraday-native 和 classic-daily 两种研究路径

## 结论

对 rule / grammar generator 而言，当前真正可靠的知识库结论是：

1. 不存在单一已被研究定稿的 crypto 4h horizon 映射
2. 最合理的 v1 设计是并行保留两组 horizons：
   - intraday-native
   - classic-daily
3. 若后续需要进一步收口，应由实验来决定哪一组在我们的 BTC / crypto perpetual 场景里更有效，而不是先验拍板。
