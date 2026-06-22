"""
数据源连通性测试脚本

测试国内网络环境下常见的免费A股数据源：
1. akshare - 推荐，免费无需注册
2. baostock - 免费，需注册
3. tushare - 免费版有限额，需注册
4. efinance - 东方财富，免费
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

# 使用项目 .venv
print(f"Python 路径: {sys.executable}")
print(f"工作目录: {os.getcwd()}")


class DataSourceTester:
    """数据源测试器"""

    def __init__(self):
        self.results = {}

    def test_source(self, name: str) -> Dict[str, Any]:
        """测试单个数据源"""
        print(f"\n{'='*60}")
        print(f"测试数据源: {name}")
        print(f"{'='*60}")

        result = {
            'name': name,
            'available': False,
            'error': None,
            'latency': None,
            'data_sample': None
        }

        try:
            start = time.time()

            if name == 'akshare':
                result = self._test_akshare(result, start)
            elif name == 'baostock':
                result = self._test_baostock(result, start)
            elif name == 'tushare':
                result = self._test_tushare(result, start)
            elif name == 'efinance':
                result = self._test_efinance(result, start)

        except Exception as e:
            result['error'] = str(e)
            print(f"❌ 错误: {e}")

        return result

    def _test_akshare(self, result: Dict, start: float) -> Dict:
        """测试 akshare"""
        import akshare as ak

        # 测试获取历史数据（更稳定的接口）
        print("  → 测试: 获取上证指数历史数据...")
        df = ak.stock_zh_index_daily(symbol="sh000001")
        print(f"  ✓ 获取到 {len(df)} 条指数数据")
        print(f"  列名: {list(df.columns)}")

        print("  → 测试: 获取平安银行历史日线...")
        df = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20240101",
            end_date="20241231",
            adjust="qfq"
        )
        print(f"  ✓ 获取到 {len(df)} 条日线数据")
        print(f"  列名: {list(df.columns)}")

        result['available'] = True
        result['latency'] = round(time.time() - start, 2)
        result['data_sample'] = df.head(2).to_dict()

        return result

    def _test_baostock(self, result: Dict, start: float) -> Dict:
        """测试 baostock"""
        import baostock as bs

        # 登录
        print("  → 测试: 连接 baostock...")
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"登录失败: {lg.error_msg}")

        print("  ✓ 登录成功")

        # 获取数据
        print("  → 测试: 获取平安银行历史日线...")
        rs = bs.query_history_k_data_plus(
            "sz.000001",
            "date,code,open,high,low,close,volume,amount",
            start_date='2024-01-01',
            end_date='2024-12-31',
            frequency="d",
            adjustflag="2"  # 前复权
        )

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        print(f"  ✓ 获取到 {len(data_list)} 条数据")

        bs.logout()
        print("  ✓ 登出成功")

        result['available'] = True
        result['latency'] = round(time.time() - start, 2)

        return result

    def _test_tushare(self, result: Dict, start: float) -> Dict:
        """测试 tushare"""
        import tushare as ts

        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            raise Exception("TUSHARE_TOKEN 环境变量未设置")

        print(f"  → Token: {token[:10]}...")

        ts.set_token(token)
        pro = ts.pro_api()

        # 测试获取股票列表
        print("  → 测试: 获取股票列表...")
        df = pro.stock_basic(exchange='', list_status='L')
        print(f"  ✓ 获取到 {len(df)} 只股票")

        # 测试获取日线数据
        print("  → 测试: 获取平安银行日线...")
        df = pro.daily(
            ts_code='000001.SZ',
            start_date='20240101',
            end_date='20241231'
        )
        print(f"  ✓ 获取到 {len(df)} 条数据")
        print(f"  列名: {list(df.columns)}")

        # 检查积分额度
        print("  → 检查账户额度...")
        try:
            df_limit = pro.limit()
            if not df_limit.empty:
                print(f"  ✓ 每分钟调用: {df_limit.iloc[0]['ml_remaining']} 次")
                print(f"  ✓ 每日调用: {df_limit.iloc[0]['dl_remaining']} 次")
        except:
            print("  ⚠ 无法获取额度信息")

        result['available'] = True
        result['latency'] = round(time.time() - start, 2)
        result['data_sample'] = df.head(2).to_dict()

        return result

    def _test_efinance(self, result: Dict, start: float) -> Dict:
        """测试 efinance (东方财富)"""
        import efinance as ef

        print("  → 测试: 获取平安银行历史数据...")
        df = ef.stock.get_quote_history(
            stock_code='000001',
            beg='20240101',
            end='20241231'
        )
        print(f"  ✓ 获取到 {len(df)} 条数据")
        print(f"  列名: {list(df.columns)}")

        # 测试获取实时行情
        print("  → 测试: 获取实时行情...")
        quote = ef.stock.get_realtime_quotes()
        if quote is not None and len(quote) > 0:
            print(f"  ✓ 获取到 {len(quote)} 只股票实时数据")

        result['available'] = True
        result['latency'] = round(time.time() - start, 2)
        result['data_sample'] = df.head(2).to_dict()

        return result

    def run_all_tests(self):
        """运行所有测试"""
        sources = ['akshare', 'baostock', 'tushare', 'efinance']

        print("\n" + "="*60)
        print("数据源连通性测试开始")
        print("="*60)

        for source in sources:
            try:
                result = self.test_source(source)
                self.results[source] = result
            except ImportError as e:
                print(f"❌ 未安装库: {e}")
                self.results[source] = {
                    'name': source,
                    'available': False,
                    'error': '库未安装'
                }
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                self.results[source] = {
                    'name': source,
                    'available': False,
                    'error': str(e)
                }

            time.sleep(1)  # 避免请求过快

        self.print_summary()

    def print_summary(self):
        """打印测试汇总"""
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)

        print(f"\n{'数据源':<12} {'状态':<10} {'延迟':<8} {'说明'}")
        print("-" * 60)

        for name, result in self.results.items():
            status = "✓ 可用" if result['available'] else "✗ 不可用"
            latency = f"{result['latency']}s" if result['latency'] else "-"
            error = result.get('error')
            error_str = str(error)[:40] if error else ""

            print(f"{name:<12} {status:<10} {latency:<8} {error_str}")

        print("\n" + "="*60)
        print("推荐建议:")
        print("="*60)

        available = [k for k, v in self.results.items() if v['available']]

        if 'akshare' in available:
            print("  ✓ 推荐 akshare: 免费、无需注册、数据全面")
        if 'tushare' in available:
            print("  ✓ 推荐 tushare: 数据质量高、API规范")
        if 'efinance' in available:
            print("  ✓ 推荐 efinance: 东方财富官方、速度快")
        if 'baostock' in available:
            print("  • baostock: 可用，但数据更新较慢")


if __name__ == "__main__":
    tester = DataSourceTester()
    tester.run_all_tests()
