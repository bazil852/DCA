import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

# Initialize CCXT Binance client
exchange = ccxt.binance()
symbol = 'BTC/USDT'  # replace with your desired symbol

# Fetch OHLCV data
ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=1000)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Compute TD Setup
df['TD_setup'] = 0
for i in range(4, len(df)):
    if df['close'].iloc[i] > df['close'].iloc[i-4]:
        df['TD_setup'].iloc[i] = df['TD_setup'].iloc[i-1] + 1 if df['TD_setup'].iloc[i-1] > 0 else 1
    elif df['close'].iloc[i] < df['close'].iloc[i-4]:
        df['TD_setup'].iloc[i] = df['TD_setup'].iloc[i-1] - 1 if df['TD_setup'].iloc[i-1] < 0 else -1

# Compute buy and sell signals
df['buy_signal'] = ((df['TD_setup'] == -9) & (df['TD_setup'].shift(-1) > df['TD_setup']))
df['sell_signal'] = ((df['TD_setup'] == 9) & (df['TD_setup'].shift(-1) < df['TD_setup']))

# Plot the candlestick chart
fig, ax = plt.subplots()

# Convert timestamp to a format that matplotlib recognizes
df['timestamp'] = df['timestamp'].map(mdates.date2num)
candlestick_ohlc(ax, df[['timestamp', 'open', 'high', 'low', 'close']].values, width=0.5, colorup='g', colordown='r')

# Plot buy and sell signals
ax.plot(df.loc[df['buy_signal'], 'timestamp'], df.loc[df['buy_signal'], 'low'], '^', markersize=10, color='g')
ax.plot(df.loc[df['sell_signal'], 'timestamp'], df.loc[df['sell_signal'], 'high'], 'v', markersize=10, color='r')

# Formatting date
ax.xaxis_date()
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

plt.show()


 # # Monitor orders and check for 3% profit

    #     total_price = 0
    #     total_filled = 0
    #     total_tickers_bought = 0
    #     profit_condition_met = False  # Initialize flag variable

    #     for order in buy_orders:
    #         order_id = order['id']
    #         try:
    #             order_data = exchange.fetch_order(order_id, symbol)
    #         except Exception as e:
    #             print (e)
    #             continue

    #         if order_data['status'] == 'closed':
    #             total_price += order_data['average'] * order_data['filled']
    #             total_filled += order_data['filled']
    #             total_tickers_bought += order_data['filled']
    #             try:
    #                 current_price = exchange.fetch_ticker(symbol)['last']
    #             except Exception as e:
    #                 print (e)
    #                 continue
                
    #             if total_filled > 0:
    #                 avg_price = total_price / total_filled
    #             else:
    #                 avg_price = 0

    #             if ProfitType == 'Fixed':
    #                 profit = (current_price - avg_price) / avg_price
    #                 take_profit = profit >= take_profit_percentage
    #             elif ProfitType == 'At Candle body':
    #                 profit = (current_price - first_order_candle_body_price) / first_order_candle_body_price
    #                 take_profit = current_price >= first_order_candle_body_price
    #                 # print ("Profit Comparison: ",current_price, first_order_candle_body_price)
    #             elif ProfitType == 'At Candle wick':
    #                 take_profit = current_price >= first_order_candle_wick_price
    #                 profit = (current_price - first_order_candle_wick_price) / first_order_candle_wick_price
    #             else:
    #                 take_profit = False

    #             if take_profit:
    #                 profit_condition_met = True  # Set flag to True if profit condition is met for any order


    #     # After loop, check if profit condition was met for any order
    #     if profit_condition_met:
    #         # Take profit
    #         tickerAmount = total_tickers_bought
    #         try:
    #             sell_order = exchange.create_order(symbol, orderType, 'sell', tickerAmount)
    #             sell_orders.append(sell_order)
    #             print(f"Taking profit: {sell_order}")
    #             logs += "Taking profit: " + str(sell_order)
    #             # Rest of your sell order code...
    #         except Exception as e:
    #             print ("Error in Taking profit: ", e)