# import pymongo library
import pymongo
import ccxt
import time
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import re
import json
import os 
from urllib.parse import urlparse
from binance.client import Client
from pyti.average_true_range import average_true_range 
import numpy as np
import pytz



def remove_extra_br(s):
    return re.sub(r'(<br />){3,}', '<br /><br />', s)


def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def timeframe_to_milliseconds(timeframe):
    multiplier = int(timeframe[:-1])  # number part of timeframe
    if timeframe.endswith('m'):
        return multiplier * 60 * 1000
    elif timeframe.endswith('h'):
        return multiplier * 60 * 60 * 1000
    elif timeframe.endswith('d'):
        return multiplier * 24 * 60 * 60 * 1000
    else:
        raise ValueError("Invalid timeframe")

def fetch_with_retry(exchange, symbol, timeframe,numb, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, limit=numb)
        except ccxt.RequestTimeout as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e
def fetch_ohlcv_my(exchange, symbol, timeframe, limit=5000):
        # Calculate the start and end timestamps for the previous 3 months
    client = Client()
    timeframe_mapping = {
    '1m': Client.KLINE_INTERVAL_1MINUTE,
    '3m': Client.KLINE_INTERVAL_3MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '6h': Client.KLINE_INTERVAL_6HOUR,
    '8h': Client.KLINE_INTERVAL_8HOUR,
    '12h': Client.KLINE_INTERVAL_12HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '3d': Client.KLINE_INTERVAL_3DAY
    # '1w': Client.KLINE_INTERVAL_1WEEK,
    # '1M': Client.KLINE_INTERVAL_1MONTH
}
    symbol = symbol.replace('/','')
 
    # Get the corresponding Binance API constant for the timeframe
    interval = timeframe_mapping.get(timeframe)

    # Calculate the start and end timestamps for the previous 3 months
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=210)
    

    # Convert timestamps to string format required by get_historical_klines
    start_time_str = start_time.strftime('%d %b, %Y')
    end_time_str = end_time.strftime('%d %b, %Y')

    # Fetch candles using Binance API
    candles = client.get_historical_klines(symbol, interval, start_time_str, end_time_str)

    # Extract relevant data from candles and create a list
    ohlcv_list = []
    unique_timestamps = set()
    for candle in candles:
        timestamp = candle[0]  # Get the timestamp value from the candle
        if timestamp not in unique_timestamps:
            unique_timestamps.add(timestamp)
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            volume = float(candle[5])

            ohlcv_list.append([timestamp, open_price, high_price, low_price, close_price, volume])
    

    ohlcv_list = sorted(ohlcv_list, key=lambda x: x[0])

    return ohlcv_list

def pvsra_indicator(overridesym, pvsra_volume, volume, pvsra_high, pvsra_low, high, open_prices, low, pvsra_close, close):
    av = sum(pvsra_volume[:-1]) / 10 if overridesym else sum(volume[:-1]) / 10  # Exclude the current unclosed candle for average volume
    
    # Calculate spread x volume product for the current candle
    current_product = (pvsra_high[9] - pvsra_low[9]) * pvsra_volume[9]
    
    # Calculate spread x volume product for the last 10 candles (excluding the unclosed one)
    last_10_products = [(pvsra_high[i] - pvsra_low[i]) * pvsra_volume[i] for i in range(9-10, 9)]
    
    # Determine if the current product is a climax based on the last 10 products
    is_climax_by_product = current_product >= max(last_10_products)
    print("Close:", pvsra_close[9], "| Open", open_prices[9],)
    if pvsra_close[9] >= open_prices[9]:  # Bullish candle
        if av * 1.5 <= pvsra_volume[9] < av * 2 and not is_climax_by_product:
            va = 'BVC'  # Blue Vector Climax
        elif pvsra_volume[9] >= av * 2 or is_climax_by_product:
            va = 'GVC'  # Green Vector Climax
        else:
            va = 'RVC'  # Regular Green Candle
    else:  # Bearish candle
        if av * 1.5 <= pvsra_volume[9] < av * 2 and not is_climax_by_product:
            va = 'PVC'  # Purple Vector Climax
        elif pvsra_volume[9] >= av * 2 or is_climax_by_product:
            va = 'RVC'  # Red Vector Climax
        else:
            va = 'RVC'  # Regular Red Candle
    
    return va, av







def tom_demark_sequence(pricedata, sequence_number):
    """
    Determines if the current TD price corresponds to the specified sequence and returns the string descriptor.
    
    :param pricedata: List of closing price data
    :param sequence_number: TD sequence number like 9, 10, etc.
    :return: String indicating the type of sequence, e.g., "9 buy" or "9 sell"
    """
    n = sequence_number
    if len(pricedata) < n + 4:  
        raise ValueError(f"Price data should have at least {n + 4} elements")

    if all([pricedata[-i] < pricedata[-i - 4] for i in range(1, n + 1)]):
        return f"{n} buy"
    elif all([pricedata[-i] > pricedata[-i - 4] for i in range(1, n + 1)]):
        return f"{n} sell"
    else:
        return "No valid TD sequence"


def bollinger_bands(price_data, periods=20, num_std=2):
    # Calculate the SMA
    sma = np.mean(price_data[-periods:])

    # Calculate the standard deviation
    std = np.std(price_data[-periods:])

    # Calculate the upper Bollinger Band
    upper_band = sma + num_std * std

    # Calculate the lower Bollinger Band
    lower_band = sma - num_std * std

    return upper_band, sma, lower_band

def is_purple_candle(va):
    if (va == 'PVC'):
        return True
    else:
        return False

def is_red_candle(va):
    if (va == 'RVC'):
        return True
    else:
        return False

def is_blue_candle(va):
    if (va == 'BVC'):
        return True
    else:
        return False

def is_green_candle(va):
    if (va == 'GVC'):
        return True
    else:
        return False

#utility Functions
def price_check(orders,price):
    for order in orders:
        if (order['price']<price):
            return True

    return False

def calculate_ema(price_data):
    # The number of periods is the length of the price data
    periods = len(price_data)

    # Start with the first price as the initial EMA
    ema = price_data[0]

    # The weight given to the most recent price
    multiplier = 2 / (periods + 1)

    # Calculate the EMA for each price
    for price in price_data[1:]:
        ema = (price - ema) * multiplier + ema

    return ema

def ema(prices, period):
    multiplier = 2.0 / (period + 1)
    ema_values = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema_values.append(((price - ema_values[-1]) * multiplier) + ema_values[-1])
    return ema_values[-1]

def true_range(current_candle, previous_candle):
    """Calculate True Range for a single candle."""
    high = current_candle[2]
    low = current_candle[3]
    prev_close = previous_candle[4]
    
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    
    return tr

def average_true_range(ohlcv, periods):
    """Calculate Average True Range up to the ith candle."""
    
    true_ranges = [true_range(ohlcv[j], ohlcv[j-1]) for j in range(periods+1)]
    
    atr = sum(true_ranges) / periods
    
    return atr

def atr(ohlcv, period):
    tr_values = []
    for i in range(1, len(ohlcv)):
        high, low, close = ohlcv[i][1], ohlcv[i][2], ohlcv[i][3]
        previous_close = ohlcv[i-1][3]
        tr = max(high - low, abs(high - previous_close), abs(low - previous_close))
        tr_values.append(tr)
    return sum(tr_values[-period:]) / period


def keltner_channels(ohlcv, i,period=20, multiplier=2):
    prices = [candle[4] for candle in ohlcv]  # extracting closing prices
    
    basis = ema(prices, period)  # Implement calculate_ema
    atr = average_true_range(ohlcv, period)  # Implement average_true_range

    upper_envelope = basis + (multiplier * atr)
    lower_envelope = basis - (multiplier * atr)

    return basis, upper_envelope, lower_envelope


def keltner_channel_position(ohlcv, period=20, multiplier=2):
    prices = [candle[4] for candle in ohlcv]  # extracting closing prices
    basis, upper_envelope, lower_envelope = keltner_channels(ohlcv, period, multiplier)
    latest_price = prices[-1]
    if latest_price > upper_envelope:
        return "upper"
    elif latest_price < lower_envelope:
        return "lower"
    else:
        return "middle"


def extract_action_regex(s):
    match = re.search(r"(Buy|Sell)", s)
    if match:
        return match.group(1)
    return None

def bollinger_band_position(pricedata,band, period=20, multiplier=2):
    """
    Determine the position of the current price relative to Bollinger Bands.

    :param pricedata: List of price data
    :param period: Period for Simple Moving Average. Default is 20
    :param multiplier: Multiplier for standard deviation. Default is 2
    :return: "Lower", "Middle", "Upper" or "Outside" indicating the position of the current price
    """

    if len(pricedata) < period:
        raise ValueError(f"Price data should have at least {period} elements")

    # Calculate the Middle Band (20 Day SMA)
    sma = sum(pricedata[-period:]) / period

    # Calculate standard deviation of the last 'period' prices
    variance = sum([(price - sma) ** 2 for price in pricedata[-period:]]) / period
    std_dev = variance ** 0.5

    # Calculate the Upper and Lower Bands
    upper_band = sma + (std_dev * multiplier)
    lower_band = sma - (std_dev * multiplier)

    current_price = pricedata[-1]

    if band == "upper":
        return upper_band
    elif band == "lower":
        return lower_band
    elif band == "middle":
        return abs(current_price - sma) < 0.0001

    else:
        return -1

def evaluate_candlestick(candlestick_type, middleOne,psvra_candles,current_candle):
    # Assuming 'middleOne' is a description like 'Bearish Red (Vol > 200%) Close'
    
    # Parse the volume percentage from the description
    volume_percentage = int(middleOne.split(">")[-1].split("%")[0])

    # Retrieve the latest candlestick data from your data source (you need to implement this part)
    latest_candlestick = current_candle
    open_price = [opens[1] for opens in psvra_candles]
    high_array = [high[2] for high in psvra_candles]
    low_array = [low[3] for low in psvra_candles]
    close_array = [candle[4] for candle in psvra_candles]
    volume_array = [volume[5] for volume in psvra_candles]
    pvsra_high_array = [high[2] for high in psvra_candles]
    pvsra_low_array = [low[3] for low in psvra_candles]
    pvsra_volume_array = [volume[5] for volume in psvra_candles]
    close_prices_array = [candle[4] for candle in psvra_candles]

    # Check the volume
    # is_high_volume = latest_candlestick['volume'] > volume_percentage / 100 * latest_candlestick['average_volume']
    candle_type,av = pvsra_indicator(True, pvsra_volume_array, volume_array, pvsra_high_array, pvsra_low_array, high_array, open_price, low_array, close_prices_array, close_prices_array)
    # Evaluate based on the candlestick type
    
    if   "High Volume Candlestick" in candlestick_type:
        print ("Parameter color: ",middleOne, candle_type,candlestick_type)
        if "Red" in middleOne and candle_type=='RVC':
            return True
        elif "Purple" in middleOne and candle_type=='PVC':
            return True
        elif "Blue" in middleOne and candle_type=='BVC':
            return True
        elif "Green" in middleOne and candle_type=='GVC':
            return True
        # Add other conditions for Blue, Green etc.
    
    print ("Not a vector candle.")
    
    return False

def evaluate_indicator(indicator_type, middleTwo, operation,ohlcv,i,latest_price):
    # Parse the number of periods from the indicator type
    print ("Type: ",middleTwo)
    periods = (middleTwo.split()[-1])
    print ("Period: ",periods)
    # Calculate the indicator value
    if 'Simple Moving Average' in middleTwo:
        # print (price_data)
        price_data = [candle[4] for candle in ohlcv[i-int(periods):i]]
        indicator_value = sum(price_data) / int(periods)
    elif 'Exponential Moving Average' in middleTwo:
        price_data = [candle[4] for candle in ohlcv[i-int(periods):i]]
        indicator_value = calculate_ema(price_data)  # You need to implement calculate_ema
    # Calculate the indicator value
    elif 'Tom Demark' in middleTwo:
        price_data = [ohlcv[i] for i in range(i - 20 + 1, i + 1)]
        td_sequence = tom_demark_sequence(price_data, int(periods))
        if "buy" in td_sequence.lower():
            indicator_value = "buy"
        elif "sell" in td_sequence.lower():
            indicator_value = "sell"
        else:
            indicator_value = "neutral"
    elif 'Bollinger Bands' in middleTwo:
        price_data = [candle[4] for candle in ohlcv[i-20:i]]
        indicator_value = bollinger_band_position(price_data,periods)
    elif 'Price' in middleTwo:
        print ("Indicator Type")
        indicator_value=latest_price
    elif 'Keltner Channel' in middleTwo:
        price_data = [ohlcv[i] for i in range(i - int(periods) + 1, i + 1)]
        basis, upper, lower = keltner_channels(price_data,int(periods))

        if "Upper Band" in middleTwo:
            indicator_value = upper
        elif "Lower Band" in middleTwo:
            indicator_value = lower
        else:  # Assuming Middle Band is equivalent to the basis
            indicator_value = basis

    print ("Indicator Value: ",indicator_value)
    


    # Add other conditions for other types of indicators
    print ("Indicator Value: ", indicator_value)
    # Evaluate the operation
    if "Tom Demark" in middleTwo:
        if operation == 'EqualTo':
            return indicator_value == "buy" or indicator_value == "sell"
        else:
            print(f"Invalid operation {operation} for Tom Demark indicator")
            return False
    else:
        if operation == 'GreaterThan':
            return latest_price > indicator_value  # You need to implement latest_price
        elif operation == 'LessThan':
            return latest_price < indicator_value
        elif operation == 'EqualTo':
            return latest_price == indicator_value
        elif operation == 'GreaterOrEqual':
            return latest_price >= indicator_value
        print(f"Indicator Value {indicator_value} is not {operation} then curren price {latest_price}" )
        return False

def get_past_candles(exchange, symbol, timeframe, period):
    """
    Retrieves past candles for a specified period.

    Parameters:
    - exchange: The ccxt exchange instance.
    - symbol: Trading pair symbol (e.g., 'BTC/USDT').
    - timeframe: The timeframe for the candles (e.g., '1m' for 1 minute candles).
    - period: The number of past candles to retrieve.

    Returns:
    - A list of past candles.
    """
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=period)
    return ohlcv

def evaluate_indicator_realtime(indicator_type, middleTwo, operation, latest_price, latest_candle, exchange,symbol,timeframe):
    # Parse the number of periods from the indicator type
    print ("Type: ",middleTwo)
    periods = (middleTwo.split()[-1])
    print ("Period: ",periods)
    # Calculate the indicator value
    if 'Simple Moving Average' in middleTwo:
        past_candles = get_past_candles(exchange, symbol, timeframe, int(periods))
        price_data = [candle[4] for candle in past_candles]
        indicator_value = sum(price_data) / int(periods)
    elif 'Exponential Moving Average' in middleTwo:
        past_candles = get_past_candles(exchange, symbol, timeframe, int(periods))
        price_data = [candle[4] for candle in past_candles]
        indicator_value = calculate_ema(price_data) 
        indicator_value = calculate_ema(price_data)  # You need to implement calculate_ema
    # Calculate the indicator value
    elif 'Tom Demark' in middleTwo:
        price_data = get_past_candles(exchange, symbol, timeframe, 20)  # Assuming 20 is the max candles you want
        td_sequence = tom_demark_sequence(price_data, int(periods))
        if "buy" in td_sequence.lower():
            indicator_value = "buy"
        elif "sell" in td_sequence.lower():
            indicator_value = "sell"
        else:
            indicator_value = "neutral"
    elif 'Bollinger Bands' in middleTwo:
        price_data = get_past_candles(exchange, symbol, timeframe, 20)
        indicator_value = bollinger_band_position(price_data, periods)
    elif 'Price' in middleTwo:
        print ("Indicator Type")
        indicator_value=latest_price
    elif 'Keltner Channel' in middleTwo:
        price_data = get_past_candles(exchange, symbol, timeframe, 20)
        basis, upper, lower = keltner_channels(price_data, int(periods))

        if "Upper Band" in middleTwo:
            indicator_value = upper
        elif "Lower Band" in middleTwo:
            indicator_value = lower
        else:  # Assuming Middle Band is equivalent to the basis
            indicator_value = basis

    print ("Indicator Value: ",indicator_value)
    


    # Add other conditions for other types of indicators
    print ("Indicator Value: ", indicator_value)
    # Evaluate the operation
    if "Tom Demark" in middleTwo:
        if operation == 'EqualTo':
            return indicator_value == "buy" or indicator_value == "sell"
        else:
            print(f"Invalid operation {operation} for Tom Demark indicator")
            return False
    else:
        if operation == 'GreaterThan':
            return latest_price > indicator_value  # You need to implement latest_price
        elif operation == 'LessThan':
            return latest_price < indicator_value
        elif operation == 'EqualTo':
            return latest_price == indicator_value
        elif operation == 'GreaterOrEqual':
            return latest_price >= indicator_value
        print(f"Indicator Value {indicator_value} is not {operation} then curren price {latest_price}" )
        return False


def find_exchange_by_id(user_data, exchange_id):
    # user_data = db.users.find_one({"_id": user_id})

    exchanges=user_data['exchanges']
    
    for exchange in exchanges:
        if exchange['_id'] == ObjectId(exchange_id):
            return exchange
    return None

def update_buffer(ohlcv_buffer, new_candle, max_buffer_length=200):  # For instance, 200
    if len(ohlcv_buffer) >= max_buffer_length:
        ohlcv_buffer.pop(0)  # Remove oldest candle
    ohlcv_buffer.append(new_candle)

def map_order_to_mongo_doc(order, strategy_id, user_id):
    mongo_doc = {
        "_id": order["info"]["orderId"],
        "symbol": order["info"]["symbol"],
        "status": order["info"]["status"],
        "avgPrice": {"$numberDouble": order["average"]},
        "executedQty": {"$numberDouble": order["info"]["executedQty"]},
        "cumQuote": {"$numberDouble": order["info"]["cummulativeQuoteQty"]},
        "timeInForce": order["info"]["timeInForce"],
        "type": order["info"]["type"],
        "side": order["info"]["side"],
        "price": {"$numberDouble": order["price"]},
        "cost": {"$numberDouble": order["cost"]},
        "average": {"$numberDouble": order["average"]},
        "filled": {"$numberDouble": order["filled"]},
        "remaining": {"$numberDouble": order["remaining"]},
        "totalProfit": {"$numberDouble": 0.0},
        "runDateTime": {"$date": {"$numberLong": order["info"]["transactTime"]}},
        "strategyId": {"$oid": strategy_id},
        "created": {"$date": {"$numberLong": str(int(datetime.now().timestamp() * 1000))}},
        "__v": {"$numberInt": "0"},
        "userId": {"$oid": user_id},
    }
    return mongo_doc


def place_order_with_retry(symbol, orderType, action, quantity,exchange,order_placed,sell_order_ids, retries=1,price=None,sell_amount=None,leverage=None,leverageValue=None):
    # for _ in range(retries):
    try:
        params = {}
        if leverage:
            # Assuming the exchange uses a 'leverage' parameter; you'll need to adjust this based on the actual API
            params['leverage'] = leverageValue  # This is just a placeholder; the actual param might differ
            print ("Leverage is ", leverageValue)
        if action == "BUY":
            order = exchange.create_order(
                symbol,
                orderType,
                action,
                str(quantity),
                params=params
            )
            order_placed==True
        
        if action == "SELL":
            print ("amounttt",str(sell_amount))
            if leverage:
                params['leverage'] = leverageValue
                params['positionSide'] = 'sell'
            order = exchange.create_order(
            symbol,
            "limit",
            action,
            str(round(sell_amount,3)),
            price,
            params=params
        )
            sell_order_ids.add(order['id'])
        
        return order,order_placed  # Return the order object if successful
    except Exception as e:
        print(f"Error placing order (attempt): ",e)
        # logs += "Error Placing order Retrying"
        time.sleep(1)  # Optional: Add a short delay between attempts
        return None,False  # Return None if all attempts failed

def calculate_take_profit_price(buy_price, take_profit_percentage):
    return buy_price * (1 + take_profit_percentage / 100)

def calculate_cover_price(sell_price, profit_percentage):
    return sell_price * (1 - (profit_percentage / 100))

def get_open_orders(symbol,exchange):
    try:
        return exchange.fetch_open_orders(symbol)
    except Exception as e:
        print(f"Error fetching open orders: {e}")
        return []

def cancel_order(symbol, order_id,exchange):
    try:
        exchange.cancel_order(order_id, symbol)
    except Exception as e:
        print(f"Error cancelling order {order_id}: {e}")

def cancel_bot_sell_orders(symbol,exchange,sell_order_ids):
    open_orders = get_open_orders(symbol,exchange)
    for order in open_orders:
        if order['side'] == 'sell' and order['id'] in sell_order_ids:
            cancel_order(symbol, order['id'],exchange)
            sell_order_ids.remove(order['id'])

def check_and_replace_sell_orders(symbol, exchange, sell_order_ids, buy_orders):
    print ("checking")
    open_orders = exchange.fetch_open_orders(symbol)  # Fetch the open orders for the symbol
    open_positions = exchange.fetch_balance()['info']['positions']
    open_positions = [p for p in open_positions if p['symbol'] == "ETHUSDT"]
    
    open_sell_order_ids = [order['id'] for order in open_orders if order['side'] == 'sell']
    print (open_positions)
    print (open_sell_order_ids)
    # Check if any buy orders from buy_orders list match with open positions
    if any(buy_order['id'] in [position['id'] for position in open_positions] for buy_order in buy_orders):
        # Check if the latest sell order is open
        latest_sell_order_id = max(sell_order_ids)
        if latest_sell_order_id not in open_sell_order_ids:
            # If not, place the latest sell order again
            latest_sell_order = next((order for order in open_orders if order['id'] == latest_sell_order_id), None)
            if latest_sell_order:  # Make sure the order was found in our list
                params = {
                    'price': latest_sell_order['price'],
                    'amount': latest_sell_order['amount']
                    # Add any other necessary parameters
                }
                exchange.create_limit_sell_order(symbol, **params)
            return False
    
    # If no open sell orders are found based on the input lists, return True
    if not open_sell_order_ids and not open_positions:
        return True
    
    return False  # Return False otherwise


def lambda_function(client,bot_id, bot_name, bot_type, description, 
        exchange_id, exchange_name, exchange_type, api_key, secret_key, user_id,
        strategy_ids, time_frame, user_email, user_first_name, user_last_name, 
        account_verified, state):
    collection = client['test']
    strats=collection['strategies']
    strategyID=strategy_ids
    ohlcv_buffer = []
    do = strats.find_one(ObjectId(strategyID))
    print ("Strategy is: ",do)
    
    order_size = do['orders']['firstOrderSize']
    safety_order = do['orders']['extraOrderSize']
    max_buy_orders = int(do['dca']['maxExtraOrders'])
    # symbol = do['strategyPair']+'/USDT'
    volumeMultiplier= do['dca']['volumeMultiplier']
    minDistBetweenOrders=do['dca']['minDistBetweenOrders']
    startExtraOrder=do['dca']['startExtraOrder']

    symbol = do['orders']['pairs']
    position = 'long'
    timeframe = time_frame
    multiplier = do['dca']['volumeMultiplier']
    stratType= bot_type
    orderType=do['orders']['orderType']
    profitC='USDT'
    sandbox='True'
    try:
        leverage=do['orders']['leverage']
        if (leverage):
            leverageValue=do['orders']['leverageValue']
        else:
            leverageValue=0
    except Exception as e:
        leverage=None
        leverageValue=0

    # buyOn=do['buyOnCondition']
    # ignore=do['ignoreCondition']
    
    try:
        multiplier= float(multiplier)
    except Exception as e:

        print("multiplier ",e)
        multiplier=1
    try:
        buyOn= float(buyOn)
    except Exception as e:
        print("Buy on  ",e)
        buyOn=1
    if (buyOn<=0):
        buyOn=1
    try:
        ignore= float(ignore)
    except Exception as e:
        print("Ignore ",e)
        ignore=0
    try:
        if (safety_order<=0):
            safety_order=order_size
    except Exception as e:
        print("SO ",e)
        safety_order=order_size
    
    try:
        max_buy_orders=int(max_buy_orders)
        if (max_buy_orders<=0):
            max_buy_orders=100000
    except Exception as e:
        print("MAX BO ",e)
        max_buy_orders=100000000
    try:
        order_size=float(order_size)
    except Exception as e:
        print("Order Size ",e)
        order_size = 0




    print(int(buyOn),int(ignore))

    # Temp Variables
    buy_orders = []
    buy_candles=[]
    sell_orders=[]
    overridesym = True
    stop_ordering=False
    total=0
    
    conditions_hit = 0
    conditions_ignored = 0
    enabledvector= 'False'
    enableMA='False'
    red_action="None"
    green_action="None"
    blue_action="None"
    purple_action="None"
    MA_val=[]
    MA_cond=[]
    timeframe_vector='1h'
    timeframe_MA=[]

    parameters = do['parameters']
    
    if (position == 'long'):
        action = 'buy'
    else:
        action = 'sell'

    


    ProfitType=do['takeProfit']['takeProfit']
    take_profit_percentage=0
    print("TAKEEE PROFIITT: ",do['takeProfit']['minTakeProfit'])
    try:
        if (do['takeProfit']['takeProfit']=='Fixed'):
            print("TAKEEE PROFIITT: ",do['takeProfit']['minTakeProfit'])
            take_profit_percentage = float(do['takeProfit']['minTakeProfit'])
    except:
        print("No Tp set")
 
    ex_type = exchange_type
    APIKEY= api_key
    APISECRET= secret_key
    print (ex_type)
    print (APIKEY)
    print (APISECRET)
    quotaguard_url = os.environ.get("QUOTAGUARDSTATIC_URL")
    proxy_parsed = urlparse(quotaguard_url)
    exchange = ccxt.binance()
    # exchange.set_sandbox_mode(True)

    if (ex_type == "Binance Futures Test"):
        exchange = ccxt.binance({
            'apiKey': APIKEY,
            'secret': APISECRET,
            'enableRateLimit': True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
            'options': {
                'defaultType': 'future',
            },
            'timeout': 15000,  # Set the timeout value in milliseconds
            
        })
        exchange.set_sandbox_mode(True)
    elif (ex_type == "Binance Futures"):
        exchange = ccxt.binance({
            'apiKey': APIKEY,
            'secret': APISECRET,
            'enableRateLimit': True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
            'options': {
                'defaultType': 'future',
            },
            'timeout': 15000,  # Set the timeout value in milliseconds
            

        })
    elif (ex_type == "Binance Spot"):
        print ("YALLAAHHH")
        exchange = ccxt.binance({
            'apiKey': APIKEY,
            'secret': APISECRET,
            'enableRateLimit': True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
            'timeout': 15000,  # Set the timeout value in milliseconds
            

        })
    #     print ("HABIBI",fetch_with_retry(exchange, symbol, timeframe_vector,10))
    elif (ex_type == "Bybit Spot"):
        print ("Bybit Spot")
        exchange = ccxt.bybit({
            'apiKey': APIKEY,
            'secret': APISECRET,
            'enableRateLimit': True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
            'timeout': 15000,  # Set the timeout value in milliseconds
            

        })
    elif (ex_type == "Okx Spot"):
        print ("Okx Spot")
        exchange = ccxt.okx({
            'apiKey': APIKEY,
            'secret': APISECRET,
            'enableRateLimit': True,  # https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
            'timeout': 15000,  # Set the timeout value in milliseconds
            

        })
    
    print ( "Validating Data")
    print (order_size, type(order_size))
    print (safety_order, type(safety_order))
    print (multiplier, type(multiplier))
    print (max_buy_orders, type(max_buy_orders))
    # print (timeframe, type(timeframe))
    print (orderType, type(orderType))
    print (stratType)
    trade_direction = "long"
    print (red_action, type(red_action))
    print (purple_action, type(purple_action))
    print (blue_action, type(blue_action))
    print (green_action, type(green_action))
    print (symbol.replace('/',''))
    print (MA_cond)
    print (MA_val,type(MA_val))
    print (timeframe_MA)
    print (timeframe_vector)
    print(buyOn, type(buyOn))

    sell_order_ids = set()
    logs= str(order_size)+'<br />'+str(safety_order)+'<br />'+str(multiplier)+'<br />'+str(max_buy_orders)+'<br />'+str(timeframe)+'<br />'+str(orderType)+'<br />'+str(red_action)+'<br />'+str(purple_action)+'<br />'+str(blue_action)+'<br />'+str(green_action)+'<br />'
    bots_collection = collection['bots']
    update_operation = {"$set": {"logs": logs}}
    bot_id_as_object = ObjectId(bot_id)
    result = bots_collection.update_one({"_id": bot_id_as_object}, update_operation)
    if result.modified_count > 0:
        print("Document updated successfully.")
    else:
        print("No document matched the filter, or the document was already updated.")
    
    current_order_size = order_size
    last_candle_timestamp = None
    first_order_candle_body_price = None
    first_order_candle_wick_price = None
    order_counter= 0
    
    timestamp, open_prices, high, low, close, volume=0,0,0,0,0,0
    psvra_candles=[]
    collection = client['test']
    bots_collection = collection['bots']
    bot_id_as_object = ObjectId(bot_id)        
    bot_document = bots_collection.find_one({"_id": bot_id_as_object})
    state = bot_document.get('state', '')
    
    while True:
        logs = ''
        try:
            if (state=='off'):
                print ("State is off check db. Waiting for 3 seconds")
                time.sleep(6)
                collection = client['test']
                bots_collection = collection['bots']
                bot_id_as_object = ObjectId(bot_id)        
                bot_document = bots_collection.find_one({"_id": bot_id_as_object})
                state = bot_document.get('state', '')
                if (state=='off'):
                    print ("State still not changed exiting.....")
                return
                print("State changed :)")
        except Exception as e:
            print("Error")
            print (e)
        try:
            psvra_candles=fetch_with_retry(exchange, symbol, timeframe,11)
            ohlcv = psvra_candles[-2]
            timestamp, open_prices, high, low, close, volume = ohlcv
            update_buffer(ohlcv_buffer, ohlcv)
        except Exception as e:
            print("Error")
            print (e)
        
        
        

        

        # Calculate the 50-period SMA

        if True:
            if last_candle_timestamp != timestamp:
                last_candle_timestamp = timestamp
                open_price = [opens[1] for opens in psvra_candles]
                high_array = [high[2] for high in psvra_candles]
                low_array = [low[3] for low in psvra_candles]
                close_array = [candle[4] for candle in psvra_candles]
                volume_array = [volume[5] for volume in psvra_candles]
                pvsra_high_array = [high[2] for high in psvra_candles]
                pvsra_low_array = [low[3] for low in psvra_candles]
                pvsra_volume_array = [volume[5] for volume in psvra_candles]
                close_prices_array = [candle[4] for candle in psvra_candles]
                pvsra_volume=volume

                # Call the pvsra_indicator function to determine the type of candle
                candle_type,av = pvsra_indicator(overridesym, pvsra_volume_array, volume_array, pvsra_high_array, pvsra_low_array, high_array, open_price, low_array, close_prices_array, close_prices_array)
                utc_time = datetime.utcfromtimestamp(timestamp / 1000.0)
                utc_time = utc_time.replace(tzinfo=pytz.utc)
                utc_plus_one_time = utc_time.astimezone(pytz.timezone('Etc/GMT-1'))
                logs += "============================\n"
                logs+="Timestamp"+str(utc_plus_one_time.strftime('%Y-%m-%d %H:%M:%S'))+"  \nOpen:"+str(open_prices)+"  High:"+str(high)+"  Low:"+str(low)+"  Close:"+str(close)+"  \nCandle Type: "+candle_type+"  \nAvg. Vol:"+str(round(av,3))+"  Cur. Vol:"+str(pvsra_volume)+"\n"
                # Check if the candle type matches any of the conditions
                parameters = do['parameters']
                should_buy = False
                trueConditions= []
                
                for j, param in enumerate(parameters):
                    # Assume the keys are '1', '3', '5', etc., for candlesticks, and '2', '4', '6', etc., for indicators
                    if ("(Vol >" in param['middleOne']):
                        candle_condition = evaluate_candlestick(param[str(j*2+1)], param['middleOne'],psvra_candles,ohlcv)
                    else:
                        candle_condition = evaluate_indicator_realtime(param[str(j*2+1)], param['middleOne'], param['operation'],close,psvra_candles[8],exchange,symbol,timeframe)
                    indicator_condition = evaluate_indicator_realtime(param[str(j*2+2)], param['middleTwo'], param['operation'],close,psvra_candles[8],exchange,symbol,timeframe)

                    # current_condition = candle_condition and indicator_condition
                    if (candle_condition and indicator_condition):
                        trueConditions.append(True)
                    else:
                        trueConditions.append(False)
                print(trueConditions)
                should_buy = trueConditions[0]

                for j in range(1, len(trueConditions)):
                    if parameters[j]['relation'] == 'AND':
                        should_buy = should_buy and trueConditions[j]
                    elif parameters[j]['relation'] == 'OR':
                        should_buy = should_buy or trueConditions[j]
                
                if should_buy:
                    conditions_hit += 1
                    if conditions_ignored < int(ignore) and int(ignore)>0:
                        conditions_ignored += 1
                        print(f"Ignored condition {conditions_ignored}")
                        logs += "Ignored condition " + str(conditions_ignored) + '\n'
                    elif  price_check(buy_orders, close)==False and order_counter<max_buy_orders:
                    # Place the order using ccxt
                        if action == 'buy' or action == 'sell':
                            if len(buy_orders) == 0:
                                first_order_candle_body_price = open_prices
                                first_order_candle_wick_price = high
                            # Place a custom order
                            if (len(buy_orders) >0):
                                cancel_bot_sell_orders(symbol,exchange,sell_order_ids) 
                            order_placed = False
                            retries = 1
                            # Main logic
                            buy_order_quantity = (float(current_order_size) / close)
                            buy_order_quantity = buy_order_quantity * (1+0.001)
                            # Place the buy order
                            print("placing order for amount: ",buy_order_quantity)
                            if trade_direction == "long":
                                order_action = "BUY"
                            else:
                                order_action = "SELL"

                            
                            # Apply leverage if enabled

                            buy_order,order_placed = place_order_with_retry(symbol, orderType, order_action, buy_order_quantity,exchange,order_placed,sell_order_ids,leverage=leverage,leverageValue=leverageValue)

                            if buy_order!= None:
                                print (buy_order)
                                buy_orders.append(buy_order)
                                total_price = 0
                                total_filled = 0
                                total_tickers_bought = 0
                                total_sell_price = 0
                                total_sell_filled = 0
                                total_tickers_sold = 0
                                if trade_direction == 'long':
                                    
                                    # print ("Chaecking profit")
                                    for order in buy_orders:
                                        order_id = order['id']
                                        try:
                                            order_data = exchange.fetch_order(order_id, symbol)
                                        except Exception as e:
                                            print(e)
                                            continue

                                        if order_data['status'] == 'closed':
                                            total_price += order_data['average'] * order_data['filled']
                                            total_filled += order_data['filled']
                                            total_tickers_bought += order_data['filled']

                                    if total_filled > 0:
                                        avg_price = total_price / total_filled
                                    else:
                                        avg_price = 0
                                    # print ("Total filled: ", total_filled)
                                    # print ("Average price: ", avg_price)
                                    try:
                                        current_price = exchange.fetch_ticker(symbol)['last']
                                    except Exception as e:
                                        print(e)
                                    average_buy_price = avg_price  # Assuming 'close' is your buy price
                                else:
                                    for order in sell_orders:  # Assuming sell_orders is the list tracking your sell orders
                                        order_id = order['id']
                                        try:
                                            order_data = exchange.fetch_order(order_id, symbol)
                                        except Exception as e:
                                            print(e)
                                            continue

                                        if order_data['status'] == 'closed':
                                            total_sell_price += order_data['average'] * order_data['filled']
                                            total_sell_filled += order_data['filled']
                                            total_tickers_sold += order_data['filled']

                                    if total_sell_filled > 0:
                                        average_sell_price = total_sell_price / total_sell_filled
                                    else:
                                        average_sell_price = 0
                                # Calculate sell price for take profit
                                adjusted_sell_amount = total_filled * (1 - 0.05)
                                # adjusted_sell_amount = adjusted_sell_amount * (1 - 0.001)
                                if ProfitType == "At Candle Body":
                                    sell_price = first_order_candle_body_price
                                elif ProfitType == "At Candle Wick":
                                    sell_price = first_order_candle_wick_price
                                elif ProfitType == "Fixed":
                                    # sell_price = calculate_take_profit_price(average_buy_price, float(take_profit_percentage))
                                    if trade_direction == "long":
                                        sell_price = calculate_take_profit_price(average_buy_price, float(take_profit_percentage))
                                    else:  # for short
                                        sell_price = calculate_cover_price(average_sell_price, float(take_profit_percentage))
                                print("Sell order placed at avg price of: ",average_buy_price," At ",sell_price," ",take_profit_percentage," Amount: ",adjusted_sell_amount)
                                # Place new take profit sell order
                                
                                if trade_direction == "long":
                                    sell_order = place_order_with_retry(symbol, orderType, "SELL", buy_order_quantity, exchange, order_placed, sell_order_ids, price=sell_price, sell_amount=adjusted_sell_amount)
                                else:
                                    cover_order = place_order_with_retry(symbol, orderType, "BUY", buy_order_quantity, exchange, order_placed, sell_order_ids, price=sell_price, sell_amount=adjusted_sell_amount)
                                order_counter += 1
                                collection = client['test']
                                
                                if len(buy_orders) == 1:
                                    current_order_size = safety_order
                                elif len(buy_orders) >1:
                                    current_order_size *= multiplier
                                logs += str(action.capitalize()) + " order placed: " + str(close) + " for " + str(current_order_size) + '\n'
                                logs += "Order Filled for " + str(buy_order['price'])+"\n"
                            else:
                                    print(f"Failed to place {action} order after {retries} attempts")

                    elif price_check(buy_orders, close)!=False:
                        logs += "buy on condition ignore : " + str(conditions_hit)+"%"+str(buyOn)+"="+str((conditions_hit)% int (buyOn)) + '\n'
                        logs += "price returned by Price check " + str(price_check(buy_orders,close))+'\n'
        

        order_check=check_and_replace_sell_orders(symbol,exchange,sell_order_ids,buy_orders)
        if (order_check==False):
            max_buy_orders=0
        if (len(logs)>2):
            print (logs)
            collection = client['test']
            bots_collection = collection['bots']
            bot_id_as_object = ObjectId(bot_id)        
            logs=logs.replace('\n','<br />')
            logs = remove_extra_br(logs)
            bot_document = bots_collection.find_one({"_id": bot_id_as_object})
            current_logs = bot_document.get('logs', '')
            update_operation = {"$set": {"logs": current_logs + '<br />' + logs}}
            result = bots_collection.update_one({"_id": bot_id_as_object}, update_operation)
                

def backtesting(client,strategy_id):
    collection = client['test']
    print (strategy_id)
    # {'generalSettings': {'strategyName': 'bazil', 'strategyFolder': '', 'strategyDescription': '', 
    # 'botLink': '', 'notes': ''}, 'orders': {'firstOrderSize': '50', 'extraOrderSize': '60', 
    # 'orderType': 'Market', 'pairs': 'BTC/USDT'}, 'dca': {'dcaType': 'Signal', 'volumeMultiplier': '1', 
    # 'maxExtraOrders': '10', 'minDistBetweenOrders': '', 'startExtraOrder': '', 'stepMultiplier': '1.1'},
    #  'takeProfit': {'takeProfit': 'Fixed', 'minTakeProfit': '3'}, 'stopLoss': {'stopLoss': ''}, 
    
    #  'parameters': [{'1': 'High Volume Candlestick', '2': 'Indicator', 'operation': 'GreaterThan', 
    #  'relation': '', 'middleOne': 'Bearish Red (Vol > 200%) Open',
    #  'middleTwo': 'Simple Moving Average 20'}], 
    
    
    # 'user': {'email': 'bazilsb7@gmail.com', 'id': 4, 
    #  'firstName': 'Bazil', 'lastName': 'Sajjad', 'accountVerified': True}}
# {
#   'generalSettings': {
#     'strategyName': 'bazil',
#     'strategyFolder': '',
#     'strategyDescription': '',
#     'botLink': '',
#     'notes': ''
#   },
#   'orders': {
#     'firstOrderSize': '50',
#     'extraOrderSize': '60',
#     'orderType': 'Market',
#     'pairs': 'BTC/USDT'
#   },
#   'dca': {
#     'dcaType': 'Signal',
#     'volumeMultiplier': '1',
#     'maxExtraOrders': '10',
#     'minDistBetweenOrders': '',
#     'startExtraOrder': '',
#     'stepMultiplier': '1.1'
#   },
#   'takeProfit': {
#     'takeProfit': 'Fixed',
#     'minTakeProfit': '3'
#   },
#   'stopLoss': {
#     'stopLoss': ''
#   },
#   'parameters': [
#     {
#       '1': 'High Volume Candlestick',
#       '2': 'Indicator',
#       'operation': 'GreaterThan',
#       'relation': '',
#       'middleOne': 'Bearish Red (Vol > 200%) Open',
#       'middleTwo': 'Simple Moving Average 20'
#     },
#     {
#       '3': 'High Volume Candlestick',
#       '4': 'Indicator',
#       'operation': 'LessThan',
#       'relation': 'AND',
#       'middleOne': 'Bullish Green (Vol > 200%) Open',
#       'middleTwo': 'Simple Moving Average 50'
#     }
#   ],
#   'user': {
#     'email': 'bazilsb7@gmail.com',
#     'id': 4,
#     'firstName': 'Bazil',
#     'lastName': 'Sajjad',
#     'accountVerified': True
#   }
# }

    
    
    do = strategy_id
    print ("This is the strategy")
    print(do)
 
    order_size = do['orders']['firstOrderSize']
    
    safety_order = do['orders']['extraOrderSize']
    max_buy_orders = int(do['dca']['maxExtraOrders'])
    volumeMultiplier= do['dca']['volumeMultiplier']
    minDistBetweenOrders=do['dca']['minDistBetweenOrders']
    startExtraOrder=do['dca']['startExtraOrder']
    # symbol = do['strategyPair']+'/USDT'
    symbol = do['dropdownValues']['symbol']
    position = do['dropdownValues']['position']
    timeframe = do['dropdownValues']['timeframe']
    multiplier = do['dca']['stepMultiplier']
    if (multiplier == ''):
        multiplier=1
    stratType= 'LONG'
    orderType=do['orders']['orderType']
    print("Order Size: ",order_size)
    
    profitC='USDT'
    sandbox='True'
    # buyOn=do['buyOnCondition']
    # ignore=do['ignoreCondition']

    try:
        multiplier= float(multiplier)
    except Exception as e:

        print("multiplier ",e)
        multiplier=1
    try:
        buyOn= float(buyOn)
    except Exception as e:
        print("Buy on  ",e)
        buyOn=1
    if (buyOn<=0):
        buyOn=1
    try:
        ignore= float(ignore)
    except Exception as e:
        print("Ignore ",e)
        ignore=0
    try:
        if (safety_order<=0):
            safety_order=order_size
    except Exception as e:
        print("SO ",e)
        safety_order=order_size
    
    try:
        max_buy_orders=int(max_buy_orders)
        if (max_buy_orders<=0):
            max_buy_orders=100000
    except Exception as e:
        print("MAX BO ",e)
        max_buy_orders=100000000
    try:
        order_size=float(order_size)
    except Exception as e:
        print("Order Size ",e)
        order_size = 0




    print(int(buyOn),int(ignore))

    # Temp Variables
    total_buy_orders=[]
    total_sell_orders=[]
    buy_orders = []
    buy_candles=[]
    sell_orders=[]
    overridesym = True
    stop_ordering=False
    total=0
    
    conditions_hit = 0
    conditions_ignored = 0
    enabledvector= 'False'
    enableMA='False'
    red_action="None"
    green_action="None"
    blue_action="None"
    purple_action="None"
    MA_val=[]
    MA_cond=[]
    timeframe_vector='1h'
    timeframe_MA=[]
    parameters = do['parameters']






    


    ProfitType=do['takeProfit']['takeProfit']
    take_profit_percentage=0
    try:
        if (do['takeProfit']['takeProfit']=='Fixed'):
            take_profit_percentage = float(do['takeProfit']['takeProfit']['minTakeProfit'])/100
    except:
        print("No Tp set")
    print ("Profit Required: ",take_profit_percentage)
   


    exchange = ccxt.binance()



    
    print ( "Validating Data")
    print (order_size, type(order_size))
    print (safety_order, type(safety_order))
    print (multiplier, type(multiplier))
    print (max_buy_orders, type(max_buy_orders))
    # print (timeframe, type(timeframe))
    print (orderType, type(orderType))
    print (stratType)
    print (red_action, type(red_action))
    print (purple_action, type(purple_action))
    print (blue_action, type(blue_action))
    print (green_action, type(green_action))
    print (symbol.replace('/',''))
    print (MA_cond)
    print (MA_val,type(MA_val))
    print (timeframe_MA)
    print (timeframe_vector)
    print(buyOn, type(buyOn))
    if (position == 'long'):
        action = 'buy'
    else:
        action = 'sell'

    
    current_order_size = float(order_size)
    last_candle_timestamp = None
    first_order_candle_body_price = None
    first_order_candle_wick_price = None
    order_counter= 0

    timestamp, open_prices, high, low, close, volume=0,0,0,0,0,0
    psvra_candles=[]
    profits = 0
    ohlcv = fetch_ohlcv_my(exchange, symbol, timeframe_vector, limit=5000)
    print (len(ohlcv))
    # return
    iterator_loop=0
    for i in range(50, len(ohlcv)):
        print(iterator_loop, "Candle")
        current_candle = ohlcv[i-1]
        psvra_candles=ohlcv[i-9:i+1]
        timestamp, open_prices, high, low, close, volume = current_candle
        print("Timestamp: "+(str(datetime.utcfromtimestamp(timestamp/1000)))+"  \nOpen:"+str(open_prices)+"  High:"+str(high)+"  Low:"+str(low)+"  Close:"+str(close)+"\n")
        # Calculate the 50-period SMA

        # if enabledvector == 'True':
        if True:
            # Fetch the latest candlestick data
            # print ("time",last_candle_timestamp, timestamp)
            open_price = [opens[1] for opens in psvra_candles]
            high_array = [high[2] for high in psvra_candles]
            low_array = [low[3] for low in psvra_candles]
            close_array = [candle[4] for candle in psvra_candles]
            volume_array = [volume[5] for volume in psvra_candles]
            pvsra_high_array = [high[2] for high in psvra_candles]
            pvsra_low_array = [low[3] for low in psvra_candles]
            pvsra_volume_array = [volume[5] for volume in psvra_candles]
            close_prices_array = [candle[4] for candle in psvra_candles]
            pvsra_volume=volume
            # Call the pvsra_indicator function to determine the type of candle
            candle_type,av = pvsra_indicator(overridesym, pvsra_volume_array, volume_array, pvsra_high_array, pvsra_low_array, high_array, open_price, low_array, close_prices_array, close_prices_array)
            utc_time = timestamp 
            print (utc_time)
            # print ("============================")
            # print("Timestamp",utc_time.strftime('%Y-%m-%d %H:%M:%S'),"  \nOpen:",open_prices,"  High:",high,"  Low:",low,"  Close:",close,"  \nCandle Type: ",candle_type,"  \nAvg. Vol:",round(av,3),"  Cur. Vol:",pvsra_volume)
            print ("============================\n")
            print("Timestamp: "+(str(datetime.utcfromtimestamp(utc_time/1000)))+"  \nOpen:"+str(open_prices)+"  High:"+str(high)+"  Low:"+str(low)+"  Close:"+str(close)+"  \nCandle Type: "+candle_type+"  \nAvg. Vol:"+str(round(av,3))+"  Cur. Vol:"+str(pvsra_volume)+"\n")
            # Check if the candle type matches any of the conditions
            parameters = do['parameters']
            should_buy = False
            trueConditions= []
            
            print ("==parameters==")
            for j, param in enumerate(parameters):
                # Assume the keys are '1', '3', '5', etc., for candlesticks, and '2', '4', '6', etc., for indicators
                if ("(Vol >" in param['middleOne']):
                    candle_condition = evaluate_candlestick(param[str(j*2+1)], param['middleOne'],psvra_candles,current_candle)
                else:
                    candle_condition = evaluate_indicator(param[str(j*2+1)], param['middleOne'], param['operation'],ohlcv,i,close)
                indicator_condition = evaluate_indicator(param[str(j*2+2)], param['middleTwo'], param['operation'],ohlcv,i,close)

                # current_condition = candle_condition and indicator_condition
                if (candle_condition and indicator_condition):
                    trueConditions.append(True)
                else:
                    trueConditions.append(False)
                # if i > 0 and param['relation'] == 'AND':
                #     should_buy = should_buy and current_condition
                # elif i > 0 and param['relation'] == 'OR':
                #     should_buy = should_buy or current_condition
                # else:
                #     should_buy = current_condition

            # return
            should_buy = trueConditions[0]

            for j in range(1, len(trueConditions)):
                if parameters[j]['relation'] == 'AND':
                    should_buy = should_buy and trueConditions[j]
                elif parameters[j]['relation'] == 'OR':
                    should_buy = should_buy or trueConditions[j]

            if should_buy:
                # place_buy_order(config['orders'])
                pass

            if should_buy:
                conditions_hit += 1
                if conditions_ignored < int(ignore) and int(ignore)>0:
                    conditions_ignored += 1
                    print(f"Ignored condition {conditions_ignored}")
                    print ("Ignored condition " + str(conditions_ignored) + '\n')
                elif conditions_hit % int(buyOn) == 0 and price_check(buy_orders, close)==False and order_counter<max_buy_orders:
                # Place the order using ccxt
                    if action == 'buy' or action == 'sell':
                        if len(buy_orders) == 0:
                            first_order_candle_body_price = open_prices
                            first_order_candle_wick_price = high
                        order = {
                                "symbol": symbol,
                                "side": action,
                                "price": close,
                                "amount": current_order_size,
                                "timestamp": timestamp
                            }
                        if len(buy_orders) == 1:
                            current_order_size = float(safety_order)
                        elif len(buy_orders) >1:
                            print(type(current_order_size))
                            print(type(multiplier))
                            current_order_size *= float(multiplier)

                        order_counter += 1
                        if action == 'buy':
                            buy_orders.append(order)
                            total_buy_orders.append(order)
                            print (order)
                        elif action == 'sell':
                            sell_orders.append(order)
                            total_sell_orders.append(order)
                        print(str(action.capitalize()) + " order placed: " + str(close) + " for " + str(current_order_size) + '\n')
                        print("Order Filled for " + str(order['price'])+"\n")


                elif conditions_hit% int (buyOn) !=0 or price_check(buy_orders, close)!=False:
                    # print ("buy on condition ignore : ",conditions_hit,"%",buyOn,"=",conditions_hit% int (buyOn))
                    # print ("price returned by Price check ",price_check(buy_orders,close))
                    print("buy on condition ignore : " + str(conditions_hit)+"%"+str(buyOn)+"="+str((conditions_hit)% int (buyOn)) + '\n')
                    print("price returned by Price check " + str(price_check(buy_orders,close))+'\n')



        # Monitor orders and check for 3% profit
        print ("Total Orders: ",len(buy_orders))
        if (len(buy_orders) > 0):
            total_price = 0
            total_filled = 0

            total_tickers_bought = 0.0

            for order in buy_orders:
                if order['side'] == 'buy':
                    total_price += order['price'] 
                    total_filled += 1
                    total_tickers_bought += order['amount']
                    
            current_price = close
            if total_filled > 0:
                avg_price = total_price / total_filled
            else:
                avg_price = 0
            print ("Average buy price: ",avg_price)
            
            profit=0
            if ProfitType == 'Fixed':
                profit = (current_price - avg_price) / avg_price
                print ("Profit at : ", avg_price +(avg_price * take_profit_percentage))
                take_profit = profit >= take_profit_percentage
            elif ProfitType == 'At candle body':
                take_profit = current_price >= first_order_candle_body_price
                profit = (current_price - first_order_candle_body_price) / first_order_candle_body_price
                print ("Profit at : ", first_order_candle_body_price)
            elif ProfitType == 'At candle wick':
                take_profit = current_price >= first_order_candle_wick_price
                profit = (current_price - first_order_candle_wick_price) / first_order_candle_wick_price
                print ("Profit at : ", first_order_candle_wick_price)
                
            else:
                take_profit = False
            print ("PNL: ",profit)
            if take_profit:
                # Take profit
                tickerAmount = total_tickers_bought
                sell_order = {
                            "symbol": symbol,
                            "side": "sell",
                            "price": close,
                            "amount": tickerAmount,
                            "profit": [],
                            "timestamp": timestamp
                        }
                sell_orders.append(sell_order)
                total_sell_orders.append(order)
                order_counter=0
                print(f"Taking profit: {sell_order}")
                print ("Taking profit: " +str(sell_order))
                buy_orders=[]
                profits+=profit
        iterator_loop+=1
    # return
    print ("Total Profit: ", profits)
    print (len(total_buy_orders))
    print (len(total_sell_orders))

    return {
        "candles": ohlcv,
        "profit" : profits,
        "buy_orders":total_buy_orders,
        "sell_orders":total_sell_orders,
        # "candlesMA":ohlcv_for_MA
    }


# 644f90f5b40d77067c660398
# client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
# data = {
#     "_id": {"$oid": "64e60bc341b837f7c4b20945"},
#     "botName": "1 min vector red",
#     "botType": "Long",
#     "description": "none",
#     "exchange": "79",
#     "strategyId": [{"$oid": "64e60b5f41b837f7c4b2093d"}],
#     "timeFrame": "1m",
#     "user": {
#         "email": "bazilsb7@gmail.com",
#         "id": {"$numberInt": "4"},
#         "firstName": "Bazil",
#         "lastName": "Sajjad",
#         "accountVerified": True
#     },
#     "state": "off",
#     "__v": {"$numberInt": "0"}
# }

# strategy_ids=[strategy['$oid'] for strategy in data['strategyId']]
# lambda_function(
#     client,  # dummy value, as it's not present in the object
#     bot_id=data['_id']['$oid'],
#     bot_name=data['botName'],
#     bot_type=data['botType'],
#     description=data['description'],
#     exchange_id=data['exchange'],  # Assuming exchange here is the exchange id
#     exchange_name='Binance Futures Test',  # dummy value, as it's not present in the object
#     exchange_type='Binance Futures Test',  # dummy value, as it's not present in the object
#     api_key='99768ccdd173118886404b103dbd24875ead769d651c3d0c1143c031e0fd9e2a',  # dummy value, as it's not present in the object
#     secret_key='f332768806f2aed54f85ec6b055516e8bf23f31cfef5ec874a3af7ee07daf4da',  # dummy value, as it's not present in the object
#     user_id=data['user']['id']['$numberInt'],
#     strategy_ids=strategy_ids[0],
#     time_frame=data['timeFrame'],
#     user_email=data['user']['email'],
#     user_first_name=data['user']['firstName'],
#     user_last_name=data['user']['lastName'],
#     account_verified=data['user']['accountVerified'],
#     state=data['state']
# )
# lambda_function( client, '647b2028b5fc7d7b9aa74359')
