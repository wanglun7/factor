# Crypto Multi-Factor Framework — MVP 方案 & 总体路线规划

---

## 一、对 meta.md 方案的问题分析

### 整体评价

meta.md 的框架在概念层面非常完整，6 层架构（数据 → 因子 → Regime → 组合 → 执行 → 风控）逻辑自洽。但在落地层面有以下值得注意的问题：

### 1. 数据可获取性与成本被低估

- **链上数据**：不同链的数据 schema 差异巨大（EVM vs Solana vs Cosmos），统一抽象成本高。Glassnode / Dune 等数据源价格不菲，且更新延迟从几分钟到几小时不等
- **Options 数据**：crypto options 流动性集中在 BTC/ETH（Deribit 为主），alt options 几乎不可用，Phase 2 提到 options vol/skew 实际上只对 BTC/ETH 有意义
- **Whale movements / holder concentration**：噪声极大，地址归因困难，容易被刻意混淆
- **情绪数据（Twitter/X）**：需要大量 NLP 处理，信噪比低，且 X API 成本高

**建议**：MVP 阶段严格聚焦于免费或低成本可获取的高质量数据源

### 2. 因子数量控制问题

- 方案提到 6 大类各 3-8 个子因子，意味着起步就有 **18-48 个因子**
- 以 top 50 币种 × 48 因子的组合来看，过拟合风险很高
- 加密市场有效历史数据窗口短（2020 年前数据质量差，2021-2024 仅 4 年）
- 多重检验校正后很多因子显著性会消失

**建议**：MVP 阶段 **不超过 6 个核心因子**，每个因子必须有明确经济逻辑

### 3. Regime 模型的实际可用性

- 4 维度连续评分的思路是对的，比离散标签好
- 但 **实时性**是关键问题：很多指标（stablecoin issuance、ETF flow）更新频率低（日频甚至周频），做不到及时切换
- BTC 50/200 均线等传统指标在 crypto 的信号延迟大，趋势转折时反应慢
- 最大的坑：回测中 regime 看起来完美分类，但 live 中 regime 转换的 **过渡期** 才是最亏钱的地方

**建议**：MVP 的 regime 先用 2-3 个高频可更新的指标，不追求维度全面

### 4. 组合构建复杂度过高

- Sleeve 分法（momentum / mean-reversion / value / carry / defensive）概念上正确
- 但每个 sleeve 独立评估 + 跨 sleeve 组合优化，工程量巨大
- 初期资金量不大时，过度分散反而增加交易成本

**建议**：MVP 阶段用**单一 composite score 排序 → 简单权重分配**，不做 sleeve

### 5. 关键缺失项

meta.md 没有提到的但必须考虑的：

- **技术栈选型**：用什么语言/框架/数据库
- **数据存储与调度**：数据怎么存、怎么定时更新
- **回测引擎的防未来函数设计**：point-in-time data management
- **具体数据源选择与 API 对接**
- **资金量约束对策略选择的影响**
- **Survivorship bias 处理**：已退市币种的历史数据

---

## 二、MVP 方案（Phase 1）

### 目标

> 用最小工程量验证：横截面多因子选币 + BTC regime 风控的 long-bias 策略是否有扣成本后的 alpha

### 预计开发周期：6-8 周

---

### 2.1 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python | 生态最全，量化库丰富 |
| 数据库 | PostgreSQL + TimescaleDB | 时序数据高效查询 |
| 数据获取 | ccxt (交易所) + CoinGecko API (基础面) | 免费且覆盖广 |
| 回测 | 自建（基于 pandas/numpy） | 控制 point-in-time，避免未来函数 |
| 调度 | cron / APScheduler | MVP 够用 |
| 可视化 | matplotlib + streamlit | 快速搭建研究仪表板 |

### 2.2 投资 Universe

- **核心池**：Binance/OKX 永续合约 top 30 交易量币种
- **筛选条件**：
  - 30 日日均成交额 > $10M
  - 上线时间 > 90 天
  - 至少在 2 个主流交易所有永续合约
- **更新频率**：每周一次重新筛选
- **历史数据**：从 2021-01-01 开始（保证数据质量的最早时间点）

### 2.3 数据层（仅 MVP 必需）

| 数据类别 | 具体字段 | 来源 | 频率 |
|----------|----------|------|------|
| 现货价格 | OHLCV, VWAP | ccxt (Binance) | 1h / 4h / 1d |
| 永续合约 | funding rate, OI | ccxt (Binance) | 8h / 1d |
| 基础信息 | market cap, 流通量 | CoinGecko | 1d |
| 链上基础 | TVL (仅 DeFi 链) | DeFiLlama (免费) | 1d |
| 宏观基准 | BTC 价格, DXY | ccxt / Yahoo Finance | 1d |

**不做的数据**：options、order book depth、whale tracking、Twitter 情绪、token unlock calendar

### 2.4 Alpha 因子（6 个）

#### Factor 1: Risk-Adjusted Momentum (20d)
```
公式：ret_20d / realized_vol_20d
逻辑：风险调整后的中期动量，过滤高波动假突破
频率：日频更新
```

#### Factor 2: Short-Term Reversal (3d)
```
公式：-ret_3d（取反）
逻辑：crypto 短期过度反应后的均值回复
频率：日频更新
注意：需配合流动性过滤，低流动性币种不适用
```

#### Factor 3: Funding Rate Crowding
```
公式：-zscore(avg_funding_8h, lookback=14d)
逻辑：极端 funding 意味着方向拥挤，逆向有预测力
频率：每 8h 更新
```

#### Factor 4: OI-Price Divergence
```
公式：zscore(OI_change_7d) - zscore(price_change_7d)
逻辑：OI 涨但价格不涨 → 空头积累；反之 → 多头积累
频率：日频更新
```

#### Factor 5: Market Cap / TVL (仅 DeFi 币)
```
公式：-log(MC / TVL)
逻辑：TVL 相对市值高的币"便宜"
频率：日频更新
适用范围：仅限有 TVL 的 DeFi 协议
```

#### Factor 6: Liquidity Quality
```
公式：-amihud_illiquidity = -avg(|ret| / volume, 20d)
逻辑：既是风险过滤器，也有 alpha（流动性改善的币种后续表现好）
频率：日频更新
```

#### 因子合成

```
composite_alpha = Σ(w_k × zscore(factor_k))
```

初始等权，运行 3 个月后根据 IC 表现调整权重。每个因子在合成前：
1. Winsorize (±3σ)
2. 横截面 z-score
3. 缺失值填 0（即中性处理）

### 2.5 Regime 模型（3 个指标）

| 指标 | 计算方式 | 更新频率 |
|------|----------|----------|
| BTC Trend Score | BTC 收盘价 vs 20d/60d EMA 的位置 | 日频 |
| Volatility Stress | BTC 30d realized vol 的 zscore | 日频 |
| Alt Breadth | top30 币种中跑赢 BTC 的比例 | 日频 |

```
regime_score = 0.4 × trend + 0.3 × (-stress) + 0.3 × breadth
```

- regime_score > 0.5 → **Risk-On**：正常运行因子模型
- regime_score ∈ [-0.5, 0.5] → **Neutral**：减仓 30%，偏向大币
- regime_score < -0.5 → **Risk-Off**：仅保留 BTC/ETH，gross 降至最低

### 2.6 组合构建（极简版）

- **形式**：Long-bias（不做空）
- **标的数**：持仓 8-15 个币
- **权重方式**：
  1. 按 composite_alpha 排序
  2. Top N 入选
  3. 权重 = alpha_score 的 softmax，上限 15% 单币
  4. BTC/ETH 保底各 5% 权重（防止极端情况全是小币）
- **再平衡频率**：每周一次（周一 UTC 00:00）
- **Turnover 约束**：单次调仓换手率 < 40%

### 2.7 风控（最小集）

| 规则 | 阈值 |
|------|------|
| 单币权重上限 | 15% |
| top3 币种合计上限 | 40% |
| 非 top10 市值币种合计上限 | 50% |
| 单次 turnover 上限 | 40% |
| 组合 30d 回撤触发减仓 | -15% → 减仓 50% |
| 组合 30d 回撤触发清仓 | -25% → 全部平仓 |

### 2.8 回测评估指标

- **Alpha 质量**：rank IC, ICIR, top quintile vs bottom quintile spread
- **组合表现**：年化收益, Sharpe, Sortino, 最大回撤, Calmar
- **风险检查**：BTC beta, 与 BTC 相关性, 行业集中度
- **交易实现**：假设 0.1% 单边交易成本（含滑点）
- **稳定性**：分年度 / 牛熊 / 高低波动率分段表现

### 2.9 MVP 工程结构

```
factor/
├── config/
│   ├── universe.yaml          # 币种池配置
│   └── settings.yaml          # 全局参数
├── data/
│   ├── fetcher.py             # 数据拉取（ccxt/API）
│   ├── storage.py             # 数据存储（DB 交互）
│   └── cleaner.py             # 数据清洗与校验
├── factors/
│   ├── base.py                # 因子基类
│   ├── momentum.py            # 动量因子
│   ├── reversal.py            # 反转因子
│   ├── funding.py             # 资金费率因子
│   ├── oi_divergence.py       # OI 背离因子
│   ├── valuation.py           # 估值因子
│   ├── liquidity.py           # 流动性因子
│   └── composite.py           # 因子合成
├── regime/
│   ├── indicators.py          # regime 指标计算
│   └── scorer.py              # regime 评分与状态判定
├── portfolio/
│   ├── constructor.py         # 组合构建
│   └── risk.py                # 风控约束
├── backtest/
│   ├── engine.py              # 回测引擎
│   ├── metrics.py             # 评估指标
│   └── report.py              # 回测报告
├── dashboard/
│   └── app.py                 # Streamlit 仪表板
└── main.py                    # 入口
```

---

## 三、总体路线规划

### Phase 1: MVP（第 1-8 周）— 验证 Alpha 是否存在

| 周次 | 里程碑 | 交付物 |
|------|--------|--------|
| W1-2 | 数据层搭建 | 数据拉取 + 存储 + 清洗 pipeline，覆盖 top30 币种 |
| W3-4 | 因子开发 | 6 个核心因子实现 + 单因子 IC 分析 |
| W5 | Regime + 合成 | Regime 评分系统 + 因子合成逻辑 |
| W6 | 组合 + 风控 | 组合构建 + 风控约束 + 回测引擎 |
| W7 | 回测验证 | 完整回测报告（2021-至今） |
| W8 | 评估决策 | 判断是否值得进入 Phase 2 |

**Phase 1 通过标准**：
- Composite alpha 的 rank IC > 0.03（扣成本前）
- 组合 Sharpe > 1.0（扣 0.1% 交易成本后）
- 非 BTC beta 驱动的收益占比 > 30%
- 牛熊市分段均有正收益或至少不大幅亏损

---

### Phase 2: 增强版（第 9-16 周）— 提升稳定性和覆盖面

前提：Phase 1 验证 alpha 存在

| 模块 | 内容 |
|------|------|
| 数据扩展 | + order book depth (top5 档) + long/short ratio + exchange netflow |
| 因子扩展 | + skip-momentum + funding change + volume surprise + fee growth |
| Regime 增强 | + stablecoin flow proxy + funding 极端度 + 横截面 dispersion |
| 组合优化 | 引入简单均值方差优化 + 约束求解器(cvxpy) |
| 风控升级 | + factor exposure 监控 + BTC beta 实时追踪 |
| Paper Trading | 接交易所 API，跑 paper trade，验证信号到执行的全链路 |

**Phase 2 通过标准**：
- Paper trade 实际 IC 与回测 IC 偏差 < 50%
- 因子扩展后 composite IC 提升 > 15%
- Regime 加入后最大回撤改善 > 20%

---

### Phase 3: 实盘版（第 17-24 周）— 小资金实盘

前提：Phase 2 paper trade 结果可接受

| 模块 | 内容 |
|------|------|
| 执行引擎 | TWAP / maker-优先下单 + 滑点控制 |
| 成本模型 | 基于历史成交的 market impact model |
| 实盘风控 | 实时仓位监控 + 极端行情自动减仓 + 交易所 API 健康检测 |
| 归因系统 | 每日 PnL 归因（alpha / beta / cost / residual） |
| 监控告警 | IC 衰减 / 异常回撤 / 执行质量下降 → 告警 |
| 数据质量 | 多交易所交叉验证 + 异常数据自动标记 |

**初始实盘参数**：
- 资金量：总资金的 10-20% 试跑
- 最大杠杆：1x（不加杠杆）
- 回撤熔断：-10% 暂停策略

---

### Phase 4: 机构级（第 25-40 周）— 完整系统

前提：Phase 3 实盘 3 个月 Sharpe > 0.8

| 模块 | 内容 |
|------|------|
| 多 Horizon Alpha | 短期(日内) + 中期(周) + 长期(月) 信号分层 |
| Factor Lens | 10 因子风险模型 + 归因引擎 |
| ML 信号 | ridge/XGBoost/ranking model 替代等权合成 |
| 多交易所执行 | 多所比价 + 最优路由 + 交易所风险分散 |
| Capacity 模型 | 每个策略的容量上限估计 |
| 自动化治理 | 因子自动上/下线规则 + 模型漂移检测 |
| Sleeve 架构 | 拆分 momentum / carry / value / defensive 独立管理 |

---

## 四、关键风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| Alpha 不存在或不可交易 | 中 | 致命 | Phase 1 快速验证，8 周内做 go/no-go 决策 |
| 数据质量问题（缺失/错误） | 高 | 高 | 多源交叉验证 + 异常检测 + 保守处理缺失值 |
| 过拟合 | 高 | 高 | 严格 out-of-sample，因子数量克制，经济逻辑优先 |
| Regime 转换延迟 | 中 | 中 | 用高频可更新指标 + 渐进式仓位调整而非硬切换 |
| 交易成本吃掉 alpha | 中 | 高 | 控制 turnover + 低频调仓 + 优先大币 |
| 交易所风险 | 低 | 致命 | 多交易所分散 + collateral 上限 + 紧急退出机制 |
| 黑天鹅（LUNA 式崩盘） | 低 | 高 | 单币上限 + 回撤熔断 + universe 自动剔除异常币 |

---

## 五、MVP 优先级排序（如果时间不够）

如果 8 周做不完，按以下优先级砍：

1. **必须做** ✅：数据层 + 3 个因子（momentum, reversal, funding）+ 简单等权组合 + 基础回测
2. **应该做** 🟡：剩余 3 个因子 + regime 模型 + 风控约束
3. **可以后做** 🔵：Streamlit 仪表板 + 详细归因 + 优化器

最小最小版本（4 周）：**top30 币 × 3 因子 × 等权多头 × 周频调仓**，这就够验证核心假设了。

---

## 六、总结

meta.md 的方案框架是正确的，但**落地时必须大幅收敛**：

1. 数据源从"理想全覆盖"收敛到"免费可获取的核心数据"
2. 因子从"6 大类 48 个"收敛到"6 个有经济逻辑的核心因子"
3. Regime 从"4 维度多指标"收敛到"3 个高频指标的加权评分"
4. 组合从"sleeve + 优化器"收敛到"排序 + 简单权重 + 硬约束"
5. 执行从"多交易所智能路由"收敛到"单交易所 + 限价单"

先证明 alpha 存在，再慢慢补全系统。**过早追求完美框架是 crypto quant 项目失败的头号原因。**
