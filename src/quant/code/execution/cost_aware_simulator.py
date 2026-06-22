"""
阶段零项目：成本感知的成交模拟器（Cost-Aware Fill Simulator）
================================================================

输入：目标持仓 + 当日行情
输出：考虑涨跌停限制、佣金、过户费、印花税、固定滑点后的真实成交净值

核心学习点
----------
1. A 股交易成本结构（佣金 / 过户费 / 印花税 / 滑点），以及它们如何蚕食收益
2. 涨跌停对成交的硬约束：一字涨停买不进、一字跌停卖不出
3. T+1 制度：当日买入的股票当日不可卖（账户区分「可卖」与「当日冻结」）
4. 资金守恒：用现金守恒方程自动核对账目，确保成本计算自洽

为什么用「合成行情」而非真实数据
--------------------------------
本项目目标是吃透「成本 + 涨跌停 + T+1」的机制，这些逻辑与具体股票无关。
合成行情可复现、无网络依赖，便于构造极端场景（一字板、现金不足）做验证。
后续阶段一再接真实行情。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 浮点价格相等比较的容差（价格已 round 到 0.01 元）
_EPS = 1e-6


# =========================================================================
# 一、成本与涨跌停规则
# =========================================================================

@dataclass
class CostConfig:
    """交易成本配置（2026 年 A 股现行费率）

    佣金：双向收取，单笔最低 5 元，可谈（万 0.85 ~ 万 2.5）
    过户费：双向收取，万 0.1（沪市；深市 2022 年起也收，这里统一处理）
    印花税：仅卖出收取，0.5‰（2023.8.28 起由 1‰ 减半）
    滑点：期望价与实际成交价之差，这里用固定比例（万 2）
    """
    commission_rate: float = 0.00025   # 佣金 万 2.5
    commission_min: float = 5.0        # 单笔最低 5 元
    stamp_duty_rate: float = 0.0005    # 印花税 万 5（卖出）
    transfer_fee_rate: float = 0.00001  # 过户费 万 0.1
    slippage_rate: float = 0.0002      # 固定滑点 万 2


def price_limit_ratio(code: str) -> float:
    """根据股票代码返回涨跌幅限制比例

    主板 ±10%，科创板(688)/创业板(300) ±20%，北交所(43/83/87/92/88) ±30%
    """
    code = str(code).zfill(6)
    if code.startswith("688") or code.startswith("300"):
        return 0.20
    if code.startswith(("43", "83", "87", "92", "88")):
        return 0.30
    return 0.10


def limit_prices(code: str, pre_close: float) -> Tuple[float, float]:
    """计算涨停价、跌停价（按 0.01 元四舍五入取整）"""
    ratio = price_limit_ratio(code)
    up = round(pre_close * (1 + ratio), 2)
    down = round(pre_close * (1 - ratio), 2)
    return up, down


# =========================================================================
# 二、行情
# =========================================================================

@dataclass
class Bar:
    """单只股票当日行情（OHLC + 前收盘）"""
    code: str
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    # 以下由 pre_close 推导
    limit_up: float = field(init=False)
    limit_down: float = field(init=False)

    def __post_init__(self) -> None:
        self.limit_up, self.limit_down = limit_prices(self.code, self.pre_close)

    def is_locked_up(self) -> bool:
        """一字涨停：开盘即涨停且全天未打开 → 买盘无法成交"""
        return (abs(self.open - self.limit_up) < _EPS
                and abs(self.high - self.limit_up) < _EPS
                and abs(self.low - self.limit_up) < _EPS
                and abs(self.close - self.limit_up) < _EPS)

    def is_locked_down(self) -> bool:
        """一字跌停：开盘即跌停且全天未打开 → 卖盘无法成交"""
        return (abs(self.open - self.limit_down) < _EPS
                and abs(self.high - self.limit_down) < _EPS
                and abs(self.low - self.limit_down) < _EPS
                and abs(self.close - self.limit_down) < _EPS)


# =========================================================================
# 三、成本计算
# =========================================================================

@dataclass
class CostBreakdown:
    """单笔成交的成本明细"""
    commission: float = 0.0   # 佣金
    transfer_fee: float = 0.0  # 过户费
    stamp_duty: float = 0.0   # 印花税（仅卖出）

    @property
    def total(self) -> float:
        return self.commission + self.transfer_fee + self.stamp_duty


def calc_cost(turnover: float, direction: str, cfg: CostConfig) -> CostBreakdown:
    """根据成交额与方向计算成本

    turnover: 成交额 = 成交价 × 股数
    direction: 'buy' 或 'sell'
    """
    cb = CostBreakdown()
    cb.commission = max(turnover * cfg.commission_rate, cfg.commission_min)
    cb.transfer_fee = turnover * cfg.transfer_fee_rate
    if direction == "sell":
        cb.stamp_duty = turnover * cfg.stamp_duty_rate
    return cb


# =========================================================================
# 四、账户
# =========================================================================

@dataclass
class Account:
    """交易账户：现金 + 持仓

    positions     : 可卖持仓（T+1 之前就持有的）
    frozen_today  : 当日买入冻结，不可卖，次日开盘前转入 positions
    """
    cash: float
    positions: Dict[str, int] = field(default_factory=dict)
    frozen_today: Dict[str, int] = field(default_factory=dict)

    def total_shares(self, code: str) -> int:
        return self.positions.get(code, 0) + self.frozen_today.get(code, 0)

    def market_value(self, prices: Dict[str, float]) -> float:
        """持仓市值（按给定价格，通常用收盘价）"""
        mv = 0.0
        for code, shares in self.positions.items():
            mv += shares * prices.get(code, 0.0)
        for code, shares in self.frozen_today.items():
            mv += shares * prices.get(code, 0.0)
        return mv

    def net_value(self, prices: Dict[str, float]) -> float:
        """账户净值 = 现金 + 持仓市值"""
        return self.cash + self.market_value(prices)

    def settle_new_day(self) -> None:
        """次日开盘：当日冻结仓转入可卖（T+1 解锁）"""
        for code, shares in self.frozen_today.items():
            self.positions[code] = self.positions.get(code, 0) + shares
        self.frozen_today.clear()


# =========================================================================
# 五、成交记录与模拟器
# =========================================================================

@dataclass
class Fill:
    """一笔成交"""
    code: str
    direction: str            # 'buy' / 'sell'
    shares: int               # 实际成交股数（被拒时为 0）
    price: float              # 实际成交价
    turnover: float           # 成交额
    cost: CostBreakdown       # 成本明细
    net_cash: float           # 对现金的净影响（买入为负，卖出为正）
    note: str = ""            # 说明（如一字板被拒、现金不足减量）


class CostAwareSimulator:
    """成本感知成交模拟器

    用法：
        sim = CostAwareSimulator(account, CostConfig())
        sim.rebalance(target_positions, bars)   # 调仓到目标
        sim.report(bars)                        # 打印净值与成本
    """

    def __init__(self, account: Account, cfg: CostConfig | None = None) -> None:
        self.account = account
        self.cfg = cfg or CostConfig()
        self.fills: List[Fill] = []
        # 最近一次 rebalance 前的现金，供 verify_cash_conservation 自动使用
        self._cash_before: float = account.cash

    # ---- 单笔卖出 ----
    def _exec_sell(self, code: str, want_shares: int, bar: Bar) -> Fill:
        # T+1：只能卖可卖持仓
        available = self.account.positions.get(code, 0)
        shares = min(want_shares, available)
        # 卖出允许零股（清仓），不强制 100 取整
        shares = max(shares, 0)

        if shares == 0:
            return self._record(Fill(code, "sell", 0, 0.0, 0.0,
                                     CostBreakdown(), 0.0, "无可卖持仓"))

        if bar.is_locked_down():
            return self._record(Fill(code, "sell", 0, 0.0, 0.0,
                                     CostBreakdown(), 0.0, "一字跌停，卖不出"))

        # 成交价：开盘价 - 滑点（对卖方不利方向），并 clip 到 [跌停, 最高] 与 [最低, 最高]
        price = bar.open - bar.open * self.cfg.slippage_rate
        price = max(price, bar.limit_down)   # 不低于跌停价
        price = max(price, bar.low)          # 不低于当日最低
        price = min(price, bar.high)         # 不高于当日最高

        turnover = price * shares
        cost = calc_cost(turnover, "sell", self.cfg)
        net_cash = turnover - cost.total     # 卖出：现金流入

        self.account.positions[code] -= shares
        if self.account.positions[code] == 0:
            del self.account.positions[code]
        self.account.cash += net_cash

        return self._record(Fill(code, "sell", shares, price, turnover, cost, net_cash))

    # ---- 单笔买入 ----
    def _exec_buy(self, code: str, want_shares: int, bar: Bar) -> Fill:
        # 买入须为 100 股整数倍（1 手）
        shares = (want_shares // 100) * 100

        if shares == 0:
            return self._record(Fill(code, "buy", 0, 0.0, 0.0,
                                     CostBreakdown(), 0.0, "不足 1 手"))

        if bar.is_locked_up():
            return self._record(Fill(code, "buy", 0, 0.0, 0.0,
                                     CostBreakdown(), 0.0, "一字涨停，买不进"))

        # 成交价：开盘价 + 滑点（对买方不利方向），clip 到 [跌停, 涨停] 与 [最低, 最高]
        price = bar.open + bar.open * self.cfg.slippage_rate
        price = min(price, bar.limit_up)
        price = min(price, bar.high)
        price = max(price, bar.low)

        # 现金不足：按可用现金反推可买手数（含成本），向下取整到 100 股
        shares, price, note = self._cap_by_cash(code, shares, price)
        if shares == 0:
            return self._record(Fill(code, "buy", 0, 0.0, 0.0,
                                     CostBreakdown(), 0.0, note))

        turnover = price * shares
        cost = calc_cost(turnover, "buy", self.cfg)
        net_cash = -(turnover + cost.total)  # 买入：现金流出

        # T+1：新买入进冻结仓
        self.account.frozen_today[code] = self.account.frozen_today.get(code, 0) + shares
        self.account.cash += net_cash

        return self._record(Fill(code, "buy", shares, price, turnover, cost, net_cash, note))

    def _cap_by_cash(self, code: str, shares: int, price: float) -> Tuple[int, float, str]:
        """若现金不足以买入全部目标，按可用现金反推可买手数"""
        # 每股实际占用资金 = 成交价 × (1 + 佣金率 + 过户费率)（保守按比率估，忽略最低 5 元）
        unit_cost = price * (1 + self.cfg.commission_rate + self.cfg.transfer_fee_rate)
        affordable = int(self.account.cash / unit_cost)
        affordable = (affordable // 100) * 100
        if affordable >= shares:
            return shares, price, ""
        if affordable <= 0:
            return 0, price, "现金不足，买不进"
        return affordable, price, f"现金不足，仅买入 {affordable} 股（目标 {shares}）"

    def _record(self, fill: Fill) -> Fill:
        self.fills.append(fill)
        return fill

    # ---- 调仓主流程 ----
    def rebalance(self, targets: Dict[str, int], bars: Dict[str, Bar]) -> None:
        """根据目标持仓调仓

        targets: code -> 目标持仓股数
        bars:    code -> 当日行情
        """
        # 记录调仓前现金，供守恒校验（必须在任何成交之前）
        self._cash_before = self.account.cash
        self.fills.clear()

        all_codes = set(targets) | set(self.account.positions) | set(self.account.frozen_today)

        # 第一阶段：先卖（目标 < 当前持仓）。先卖可释放现金供买入使用。
        for code in all_codes:
            if code not in bars:
                continue
            target = targets.get(code, 0)
            current = self.account.total_shares(code)
            if target < current:
                self._exec_sell(code, current - target, bars[code])

        # 第二阶段：后买（目标 > 当前持仓）
        for code in all_codes:
            if code not in bars:
                continue
            target = targets.get(code, 0)
            current = self.account.total_shares(code)
            if target > current:
                self._exec_buy(code, target - current, bars[code])

    # ---- 汇总 ----
    @property
    def total_cost(self) -> float:
        """本次调仓累计成本（佣金 + 过户费 + 印花税）"""
        return sum(f.cost.total for f in self.fills)

    def verify_cash_conservation(self) -> bool:
        """现金守恒校验（自动用本次 rebalance 前记录的现金）

        方程：final_cash == cash_before - Σ买入成交额 + Σ卖出成交额 - Σ成本
        这是硬性约束，必须成立，否则成本计算有 bug。
        """
        buy_turnover = sum(f.turnover for f in self.fills if f.direction == "buy")
        sell_turnover = sum(f.turnover for f in self.fills if f.direction == "sell")
        expected = self._cash_before - buy_turnover + sell_turnover - self.total_cost
        return abs(self.account.cash - expected) < 1e-4

    def report(self, bars: Dict[str, Bar]) -> None:
        """打印成交明细、净值、成本，并自动做现金守恒校验"""
        prices = {c: b.close for c, b in bars.items()}
        print(f"{'方向':<4}{'代码':<8}{'成交价':>9}{'股数':>8}{'成交额':>14}"
              f"{'佣金':>8}{'过户费':>8}{'印花税':>8}{'净现金流':>14}  说明")
        print("-" * 110)
        for f in self.fills:
            if f.shares == 0:
                print(f"{'--':<4}{f.code:<8}{'-':>9}{0:>8}{0:>14.2f}"
                      f"{0:>8.2f}{0:>8.2f}{0:>8.2f}{0:>14.2f}  {f.note}")
            else:
                print(f"{f.direction:<4}{f.code:<8}{f.price:>9.2f}{f.shares:>8}"
                      f"{f.turnover:>14.2f}{f.cost.commission:>8.2f}"
                      f"{f.cost.transfer_fee:>8.2f}{f.cost.stamp_duty:>8.2f}"
                      f"{f.net_cash:>+14.2f}  {f.note}")
        print("-" * 110)
        print(f"累计成本：{self.total_cost:.4f} 元")
        print(f"账户现金：{self.account.cash:.2f} 元")
        print(f"账户净值（按收盘价）：{self.account.net_value(prices):.2f} 元")
        ok = self.verify_cash_conservation()
        print(f"现金守恒校验：{'✓ 通过' if ok else '✗ 失败'}")


# =========================================================================
# 六、演示场景
# =========================================================================

def _demo_basic_rebalance() -> None:
    """场景一：基础调仓，展示成本明细与净值"""
    print("\n" + "=" * 60)
    print("场景一：基础调仓（卖出 A、买入 B、新建 C）")
    print("=" * 60)

    bars = {
        "600519": Bar("600519", 1700.00, 1720.00, 1690.00, 1710.00, 1700.00),  # 茅台 主板±10%
        "000001": Bar("000001", 11.00, 11.20, 10.90, 11.10, 11.00),            # 平安银行
        "300750": Bar("300750", 210.00, 213.00, 208.00, 212.00, 210.00),       # 宁德时代 创业±20%
    }

    # 初始：持有 100 股茅台，现金 50 万
    account = Account(cash=500_000.0, positions={"600519": 100})
    sim = CostAwareSimulator(account)
    # 目标：茅台减到 0（全卖），买入平安银行 10000 股、宁德时代 1000 股
    targets = {"600519": 0, "000001": 10_000, "300750": 1000}
    sim.rebalance(targets, bars)
    sim.report(bars)


def _demo_locked_limit() -> None:
    """场景二：一字涨停 / 一字跌停"""
    print("\n" + "=" * 60)
    print("场景二：一字板（涨停买不进 / 跌停卖不出）")
    print("=" * 60)

    # 一字涨停：开盘=最高=最低=收盘=涨停价（pre_close=10, 主板涨停=11.00）
    bar_locked_up = Bar("000002", 11.00, 11.00, 11.00, 11.00, 10.00)
    # 一字跌停：pre_close=10, 跌停=9.00
    bar_locked_down = Bar("000003", 9.00, 9.00, 9.00, 9.00, 10.00)

    account = Account(cash=1_000_000.0,
                      positions={"000003": 1000})  # 持有可跌停股 1000 股
    sim = CostAwareSimulator(account)
    targets = {"000002": 1000, "000003": 0}  # 想买涨停股、卖出跌停股
    bars = {"000002": bar_locked_up, "000003": bar_locked_down}
    sim.rebalance(targets, bars)
    sim.report(bars)
    print("→ 两个订单均被拒：买不进 + 卖不出，现金与持仓不变。")


def _demo_t_plus_1() -> None:
    """场景三：T+1，当日买入当日不可卖"""
    print("\n" + "=" * 60)
    print("场景三：T+1（当日买入的股票当日不可卖）")
    print("=" * 60)

    bar = Bar("600000", 10.00, 10.20, 9.95, 10.10, 10.00)  # 浦发银行

    # 第一天：买入 1000 股
    account = Account(cash=100_000.0)
    sim = CostAwareSimulator(account)
    sim.rebalance({"600000": 1000}, {"600000": bar})
    print("【第一天：买入】")
    sim.report({"600000": bar})
    print(f"  可卖持仓 positions    = {account.positions}")
    print(f"  当日冻结 frozen_today = {account.frozen_today}  ← T+1 当日不可卖")

    # 当天立刻想反向卖出（目标 0）→ 卖不出（冻结仓不可卖）
    sim.rebalance({"600000": 0}, {"600000": bar})
    print("\n【第一天当天：试图卖出（T+1 拦截）】")
    sim.report({"600000": bar})
    print("  → 当日买入部分不可卖，卖出被拒。")

    # 次日：冻结仓解锁
    account.settle_new_day()
    print(f"\n【次日开盘：settle_new_day 后】positions = {account.positions}")
    sim.rebalance({"600000": 0}, {"600000": bar})
    print("【次日：卖出】")
    sim.report({"600000": bar})
    print("  → 解锁后可正常卖出。")


def _demo_cash_insufficient() -> None:
    """场景四：现金不足自动减量"""
    print("\n" + "=" * 60)
    print("场景四：现金不足（按可用资金自动减量到 100 股整数倍）")
    print("=" * 60)

    bar = Bar("600519", 1700.00, 1720.00, 1690.00, 1710.00, 1700.00)
    # 只有 20 万，买不起 1000 股茅台（需 ~170 万）
    account = Account(cash=200_000.0)
    sim = CostAwareSimulator(account)
    sim.rebalance({"600519": 1000}, {"600519": bar})
    sim.report({"600519": bar})


if __name__ == "__main__":
    _demo_basic_rebalance()
    _demo_locked_limit()
    _demo_t_plus_1()
    _demo_cash_insufficient()

    print("\n" + "=" * 60)
    print("全部场景演示完成。现金守恒校验结果见各场景输出。")
    print("=" * 60)
