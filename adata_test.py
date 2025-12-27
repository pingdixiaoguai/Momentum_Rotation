# import adata

# # res_df = adata.stock.info.all_code()
# # print(res_df)

# # k_type: k线类型：1.日；2.周；3.月 默认：1 日k
# res_df = adata.stock.market.get_market(stock_code='601919', k_type=1, start_date='2023-01-01')
# print(res_df) #etf类好像都没有



import akshare as ak
# stock_data = ak.stock_zh_a_spot()
# print(stock_data)


etf_code = list(ak.fund_etf_spot_em()["代码"])
print(etf_code)
# https://zhuanlan.zhihu.com/p/18102451465 eft外其他
# stock_data = ak.fund_etf_hist_em(symbol='601919', period="daily", start_date="20130101", adjust="hfq")[["日期", "开盘", "收盘"]]
# print(stock_data)

