# A股数据源测试结果

**测试时间**: 2026-06-22
**网络环境**: 中国移动宽带
**Python环境**: 项目 .venv

---

## 测试结果汇总

| 数据源 | 状态 | 说明 | 推荐度 |
|--------|------|------|--------|
| **akshare** | ✅ 可用 | 免费、无需注册、数据全面 | ⭐⭐⭐⭐⭐ |
| **tushare** | ✅ 可用 | API规范、数据质量高、有频率限制 | ⭐⭐⭐⭐ |
| **baostock** | ✅ 可用 | 免费、数据更新较慢 | ⭐⭐⭐ |
| **efinance** | ❌ 不可用 | 连接被拒绝(移动宽带限制) | - |

---

## 各数据源详情

### 1. akshare (推荐)

```python
import akshare as ak

# 获取股票历史数据
df = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20240101",
    end_date="20241231",
    adjust="qfq"  # 前复权
)

# 获取指数数据
df = ak.stock_zh_index_daily(symbol="sh000001")
```

**特点**:
- 免费，无需注册
- 数据源全面（股票、指数、期货、外汇等）
- 中文文档友好
- API持续更新

**返回列名示例**:
```
['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额',
 '振幅', '涨跌幅', '涨跌额', '换手率']
```

---

### 2. tushare

```python
import tushare as ts
import os

ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 获取日线数据
df = pro.daily(
    ts_code='000001.SZ',
    start_date='20240101',
    end_date='20241231'
)

# 获取股票列表
df = pro.stock_basic(exchange='', list_status='L')
```

**特点**:
- Token认证，有积分等级
- API规范，返回格式统一
- 有频率限制（免费版约120次/分钟）
- 数据质量高，社区活跃

**返回列名示例**:
```
['ts_code', 'trade_date', 'open', 'high', 'low', 'close',
 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
```

---

### 3. baostock

```python
import baostock as bs

# 登录
lg = bs.login()

# 获取数据
rs = bs.query_history_k_data_plus(
    "sz.000001",
    "date,code,open,high,low,close,volume,amount",
    start_date='2024-01-01',
    end_date='2024-12-31',
    frequency="d",
    adjustflag="2"  # 前复权
)

# 登出
bs.logout()
```

**特点**:
- 免费，需注册
- 数据更新较慢
- 接口较老，但稳定

---

### 4. efinance

**状态**: 当前网络环境不可用（连接被拒绝）

如需使用，可能需要:
1. 更换网络环境
2. 配置代理
3. 使用 TickFlow 服务

---

## 后续课程数据源选择

**主要数据源**: akshare
- 示例代码优先使用
- 无需注册即可获取大部分数据

**备选数据源**: tushare
- 用于补充数据
- API更加规范

**数据存储方案**:
- 初期：CSV 文件
- 进阶：SQLite / PostgreSQL
- 大规模：HDF5 / Parquet

---

## 安装命令

```bash
.venv/bin/pip install akshare tushare baostock
```

## 环境变量设置

```bash
export TUSHARE_TOKEN="your_token_here"
```
