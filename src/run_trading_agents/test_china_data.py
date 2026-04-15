#!/usr/bin/env python3
"""
测试中国数据源集成
验证 TradingAgents 是否能够使用国内数据源获取 A 股数据
"""
import os
import sys

# 添加 TradingAgents 到 Python 路径
sys.path.insert(0, '/home/wangruo/workspace/playground/third_party/TradingAgents')

from tradingagents.dataflows.interface import route_to_vendor

def test_china_stock_data():
    """测试中国股票数据获取"""
    print("=== 测试中国股票数据获取 ===")
    
    # 测试 A 股股票
    test_symbols = ["600519.SH", "000858.SZ", "601318.SH"]  # 贵州茅台、五粮液、中国平安
    test_dates = {
        "start_date": "2026-03-01",
        "end_date": "2026-04-15"
    }
    
    for symbol in test_symbols:
        print(f"\n测试股票: {symbol}")
        print("-" * 50)
        try:
            result = route_to_vendor("get_stock_data", symbol, **test_dates)
            print("数据获取成功!")
            # 打印前几行数据
            lines = result.split('\n')[:10]
            for line in lines:
                print(line)
        except Exception as e:
            print(f"错误: {str(e)}")

def test_china_fundamentals():
    """测试中国股票基本面数据"""
    print("\n=== 测试中国股票基本面数据 ===")
    
    test_symbols = ["600519.SH", "000858.SZ"]
    
    for symbol in test_symbols:
        print(f"\n测试股票: {symbol}")
        print("-" * 50)
        try:
            result = route_to_vendor("get_fundamentals", symbol)
            print("基本面数据获取成功!")
            # 打印部分数据
            lines = result.split('\n')[:15]
            for line in lines:
                print(line)
        except Exception as e:
            print(f"错误: {str(e)}")

def test_china_indicators():
    """测试中国股票技术指标"""
    print("\n=== 测试中国股票技术指标 ===")
    
    test_symbol = "600519.SH"
    test_indicators = ["close_50_sma", "rsi"]
    
    for indicator in test_indicators:
        print(f"\n测试指标: {indicator}")
        print("-" * 50)
        try:
            result = route_to_vendor(
                "get_indicators", 
                test_symbol, 
                indicator, 
                "2026-04-15", 
                30
            )
            print("技术指标计算成功!")
            # 打印部分数据
            lines = result.split('\n')[:10]
            for line in lines:
                print(line)
        except Exception as e:
            print(f"错误: {str(e)}")

def test_data_vendor_fallback():
    """测试数据源 fallback 机制"""
    print("\n=== 测试数据源 fallback 机制 ===")
    
    # 测试美股股票，应该 fallback 到 yfinance
    test_symbol = "AAPL"
    print(f"\n测试美股股票: {test_symbol}")
    print("-" * 50)
    try:
        result = route_to_vendor(
            "get_stock_data", 
            test_symbol, 
            start_date="2026-04-01", 
            end_date="2026-04-15"
        )
        print("美股数据获取成功!")
        # 打印前几行数据
        lines = result.split('\n')[:10]
        for line in lines:
            print(line)
    except Exception as e:
        print(f"错误: {str(e)}")

def main():
    """主测试函数"""
    print("开始测试中国数据源集成...\n")
    
    # 测试中国股票数据
    test_china_stock_data()
    
    # 测试中国股票基本面
    test_china_fundamentals()
    
    # 测试中国股票技术指标
    test_china_indicators()
    
    # 测试数据源 fallback 机制
    test_data_vendor_fallback()
    
    print("\n=== 测试完成 ===")
    print("如果看到数据输出，说明中国数据源集成成功!")
    print("如果遇到错误，可能需要安装相关依赖库:")
    print("pip install akshare baostock tushare")
    print("对于 Tushare，还需要设置环境变量 TUSHARE_TOKEN")

if __name__ == "__main__":
    main()
