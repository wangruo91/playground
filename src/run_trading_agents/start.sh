cd /home/wangruo/workspace/playground/third_party/TradingAgents

# 安装后修改源码立即生效
python -m pip install -e .

# 方法 1：使用安装的命令
tradingagents

# 方法 2：直接运行源码
python -m cli.main


# ## 沪市股票 (上海证券交易所)
# 格式： 股票代码.SH

# - 600519.SH - 贵州茅台
# - 601318.SH - 中国平安
# - 600036.SH - 招商银行
# - 600900.SH - 长江电力
# - 601888.SH - 中国中免
# ## 深市股票 (深圳证券交易所)
# 格式： 股票代码.SZ

# - 000858.SZ - 五粮液
# - 000001.SZ - 平安银行
# - 000333.SZ - 美的集团
# - 002594.SZ - 比亚迪
# - 300750.SZ - 宁德时代
# ## 北交所股票 (北京证券交易所)
# 格式： 股票代码.BJ （代码支持但未完全测试）

# - 430001.BJ - 等等