# ----------------------------
# 数据字段定义
# ----------------------------
DATETIME = 'datetime' # 交易日期, yyyy-mm-dd hh:mm:ss,如果是日线，则hh:mm:ss为00:00:00
CODE = 'code' # 股票代码或者指数代码
NAME = 'name' # 股票名称或者指数名称
OPEN = 'open' # 开盘价
HIGH = 'high' # 最高价
LOW = 'low' # 最低价
CLOSE = 'close' # 收盘价
VOLUME = 'volume' # 成交量
AMOUNT = 'amount' # 成交额
PRECLOSE = 'preclose' # 昨日收盘价
PRICE_CHG = 'price_chg' # 涨跌幅
PE_TTM = 'pe_ttm' # 动态市盈率
PB_TTM = 'pb_ttm' # 市净率
TURN = 'turn' # 市净率

# ----------------------------
# 数据列定义
# ----------------------------
# 分时数据列
TICK_COLUMNS = [DATETIME,CODE,NAME,OPEN,HIGH,LOW,CLOSE,VOLUME,AMOUNT]
# 日线数据列
COLUMNS = [DATETIME,CODE,NAME,OPEN,HIGH,LOW,CLOSE,PRECLOSE,VOLUME,AMOUNT,TURN,PRICE_CHG,PE_TTM,PB_TTM]
COLUMNS_TYPE = {'code': 'str','name':'str','open':'float', 'high':'float','low':'float','close':'float','preclose':'float','volume':'float','amount':'float','turn':'float','price_chg':'float','pe_ttm':'float','pb_ttm':'float'}
TICK_COLUMNS_TYPE = {'code': 'str','name':'str','open':'float', 'high':'float','low':'float','close':'float','volume':'float','amount':'float'}