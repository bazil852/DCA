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

def pvsra_indicator(overridesym, pvsra_volume, volume, pvsra_high, pvsra_low, high,open_prices, low, pvsra_close, close):
    print (len(pvsra_volume))
    print (len(volume))
    print (len(pvsra_high))
    sum_1 = 0
    for i in pvsra_volume:
        sum_1+=i;
    sum_2 = 0
    for i in volume:
        sum_2+=i;
    av = sum_1 / 10 if overridesym else sum_2 / 10
    value2 = pvsra_volume[8] * (pvsra_high[8] - pvsra_low[8]) if overridesym else volume[8] * (high[8] - low[8])
    hivalue2 = max(value2, max(pvsra_volume[-10:]) * (max(pvsra_high[-10:]) - min(pvsra_low[-10:])) if overridesym else max(volume[-10:]) * (max(high[-10:]) - min(low[-10:])))
    va='unidentified'
    if (pvsra_close[8] > open_prices[8]):
        va='RC'
        if (pvsra_volume[8] <= (av*2) and pvsra_volume[8] >= (av*1.5)):
            va='BVC'
        elif (pvsra_volume[8] > (av*2 ) ) :
            va ='GVC'
    else:
        va='GC'
        if (pvsra_volume[8] <= (av*2) and pvsra_volume[8] >= (av*1.5)):
            va='PVC'
        elif (pvsra_volume[8] > (av*2 )):
            va ='RVC'
    return va,av



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


def find_exchange_by_id(user_data, exchange_id):
    # user_data = db.users.find_one({"_id": user_id})

    exchanges=user_data['exchanges']
    
    for exchange in exchanges:
        if exchange['_id'] == ObjectId(exchange_id):
            return exchange
    return None


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

def lambda_function(client,strategy_id):
    collection = client['test']
    strats=collection['strategies']
    strategyID=strategy_id
    do = strats.find_one(ObjectId(strategyID))
    order_size = do['orderSize']
    safety_order = do['safetyOrderSize']
    max_buy_orders = int(do['maxOrders'])
    # symbol = do['strategyPair']+'/USDT'
    symbol = do['strategyPair']
    timeframe = '1h'
    multiplier = do['candleSizeAndVol']
    stratType= do['strategyType']
    orderType=do['orderType']
    profitC='USDT'
    sandbox='True'
    buyOn=do['buyOnCondition']
    ignore=do['ignoreCondition']
    
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

    print(do['indicators'][0]['chooseIndicatorValue'])
    for indicators in do['indicators']:
        if (indicators['chooseIndicatorValue']=='Vector Candle'):
            enabledvector='True'
            timeframe_vector=indicators['timeFrameValue']
            for candle in indicators['candleValue']:
                if candle == 'red':
                    if (stratType=='Long'):
                        red_action='buy'
                    elif (stratType=='Short'):
                        red_action='sell'
                if candle == 'purple':
                    if (stratType=='Long'):
                        purple_action='buy'
                    elif (stratType=='Short'):
                        purple_action='sell'
                if candle == 'blue':
                    if (stratType=='Long'):
                        blue_action='buy'
                    elif (stratType=='Short'):
                        blue_action='sell'
                if candle == 'green':
                    if (stratType=='Long'):
                        green_action='buy'
                    elif (stratType=='Short'):
                        green_action='sell'
        elif (indicators['chooseIndicatorValue']=='Moving Averages'):
            enableMA='True'
            timeframe_MA.append( indicators['timeFrameValue'])
            MA_val.append(int(indicators['masValue']))
            MA_cond.append(indicators['masCondition'])




    


    ProfitType=do['takeProfit']
    take_profit_percentage=0
    try:
        if (do['takeProfit']=='Fixed'):
            take_profit_percentage = float(do['takeProfitPercent'])/100
    except:
        print("No Tp set")
    print (do['userId'])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print (userObj['exchanges'][0])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print ()
    db_exchange = do['exchange']
    exchange_to = find_exchange_by_id(userObj, db_exchange)
    print ("Exchangee ",exchange_to)
    ex_type = exchange_to['exchangeName']
    APIKEY= exchange_to['apiKey']
    APISECRET= exchange_to['apiSecret']
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


    logs= str(order_size)+'<br />'+str(safety_order)+'<br />'+str(multiplier)+'<br />'+str(max_buy_orders)+'<br />'+str(timeframe)+'<br />'+str(orderType)+'<br />'+str(red_action)+'<br />'+str(purple_action)+'<br />'+str(blue_action)+'<br />'+str(green_action)+'<br />'
    
    update_operation = {"$set": {"logs":logs}}
    result = strats.update_one({"_id":ObjectId(strategyID)}, update_operation)

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
    while True:
        logs = ''
        try:
            if (do['state']=='off'):
                print ("State is off check db. Waiting for 3 seconds")
                time.sleep(6)
                collection = client['test']
                strats=collection['strategies']
                strategyID=strategy_id
                do = strats.find_one(ObjectId(strategyID))
                if (do['state']=='off'):
                    print ("State still not changed exiting.....")
                    return
                print("State changed :)")
        except Exception as e:
            print("Error")
            print (e)
        try:
            psvra_candles=fetch_with_retry(exchange, symbol, timeframe_vector,10)
            ohlcv = psvra_candles[-2]
            timestamp, open_prices, high, low, close, volume = ohlcv
        except Exception as e:
            print("Error")
            print (e)
        
        


        # Calculate the 50-period SMA

        if enabledvector == 'True':
            # Fetch the latest candlestick data
            # print ("time",last_candle_timestamp, timestamp)
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
                # print ("============================")
                # print("Timestamp",utc_time.strftime('%Y-%m-%d %H:%M:%S'),"  \nOpen:",open_prices,"  High:",high,"  Low:",low,"  Close:",close,"  \nCandle Type: ",candle_type,"  \nAvg. Vol:",round(av,3),"  Cur. Vol:",pvsra_volume)
                logs += "============================\n"
                logs+="Timestamp"+str(utc_time.strftime('%Y-%m-%d %H:%M:%S'))+"  \nOpen:"+str(open_prices)+"  High:"+str(high)+"  Low:"+str(low)+"  Close:"+str(close)+"  \nCandle Type: "+candle_type+"  \nAvg. Vol:"+str(round(av,3))+"  Cur. Vol:"+str(pvsra_volume)+"\n"
                # Check if the candle type matches any of the conditions
                action = None
                if candle_type == 'RVC' and red_action != 'none':
                    action = red_action
                elif candle_type == 'GVC' and green_action != 'none':
                    action = green_action
                elif candle_type == 'BVC' and blue_action != 'none':
                    action = blue_action
                elif candle_type == 'PVC' and purple_action != 'none':
                    action = purple_action
                # Add other candle types if required
                
                if action is not None:
                    conditions_hit += 1
                    if conditions_ignored < int(ignore) and int(ignore)>0:
                        conditions_ignored += 1
                        print(f"Ignored condition {conditions_ignored}")
                        logs += "Ignored condition " + str(conditions_ignored) + '\n'
                    elif conditions_hit % int(buyOn) == 0 and price_check(buy_orders, close)==False and order_counter<max_buy_orders:
                    # Place the order using ccxt
                        if action == 'buy' or action == 'sell':
                            if len(buy_orders) == 0:
                                first_order_candle_body_price = open_prices
                                first_order_candle_wick_price = high
                            # Place a custom order
                            order_placed = False
                            retries = 5
                            if enableMA == 'True':
                                all_conditions_met = True
                                sma_values = []

                                for cond, val, tf in zip(MA_cond, MA_val, timeframe_MA):
                                    print (tf, val)
                                    ohlcv_MA = fetch_with_retry(exchange, symbol, tf, val)
                                    closing_prices = [x[4] for x in ohlcv_MA]

                                    sma = calculate_sma(closing_prices, val)
                                    sma_values.append(sma)

                                    if cond == 'Above' and close <= sma:
                                        all_conditions_met = False
                                        break
                                    elif cond == 'Below' and close >= sma:
                                        all_conditions_met = False
                                        break

                                if all_conditions_met:
                                    for _ in range(retries):
                                        try:
                                            order = exchange.create_order(
                                                symbol,
                                                orderType,
                                                action,
                                                str(round((float(current_order_size) / close), 3))
                                            )
                                            order_placed = True
                                            if len(buy_orders) == 1:
                                                current_order_size = safety_order
                                            elif len(buy_orders) > 1:
                                                current_order_size *= multiplier
                                            break
                                        except Exception as e:
                                            print(f"Error placing order (attempt {_ + 1}): {e}")
                                            logs += "Error Placing order Retrying"
                                            time.sleep(1)

                                    if order_placed:
                                        print (order)
                                        order_counter += 1
                                        collection = client['test']
                                        if (ex_type == "Binance Spot"):
                                            mongo_doc = map_order_to_mongo_doc(order, strategy_id, do['userId'])
                                        else:
                                            mongo_doc = {
                                            "_id": order["info"]["orderId"],
                                            "symbol": order["info"]["symbol"],
                                            "status": order["info"]["status"],
                                            "avgPrice": {"$numberInt": order["info"]["avgPrice"]},
                                            "executedQty": {"$numberDouble": order["info"]["executedQty"]},
                                            "cumQuote": {"$numberDouble": order["info"]["cumQuote"]},
                                            "timeInForce": order["info"]["timeInForce"],
                                            "type": order["info"]["type"],
                                            "side": order["info"]["side"],
                                            "price": {"$numberInt": order["price"]},
                                            "cost": {"$numberDouble": order["cost"]},
                                            "average": {"$numberInt": order["average"]},
                                            "filled": {"$numberDouble": order["filled"]},
                                            "remaining": {"$numberInt": order["remaining"]},
                                            "totalProfit": {"$numberDouble": 0.0},  # Assuming 0.0 for this example
                                            "runDateTime": {"$date": {"$numberLong": order["info"]["updateTime"]}},
                                            "strategyId": {"$oid": strategy_id},  # assuming a static value for this example
                                            "created": {"$date": {"$numberLong": str(int(datetime.now().timestamp() * 1000))}},
                                            "__v": {"$numberInt": "0"},
                                            "userId": {"$oid": do['userId']}, }
                                        
                                        orders=collection['orders']
                                        orders.insert_one(mongo_doc)
                                        if action == 'buy':
                                            buy_orders.append(order)
                                        elif action == 'sell':
                                            sell_orders.append(order)
                                        logs += str(action.capitalize()) + " order placed: " + str(close) + " for " + str(current_order_size) + '\n'
                                        logs += "Order Filled for " + str(order['price']) + "\n"
                                    else:
                                        print(f"Failed to place {action} order after {retries} attempts")
                                else:
                                    logs += "Moving average conditions not met for all MAs: " + ', '.join([f"{cond} MA {sma}" for cond, sma in zip(MA_cond, sma_values)]) + '\n'
                            else:
                                for _ in range(retries):
                                    try:
                                        order = exchange.create_order(
                                            symbol,
                                            orderType,
                                            action,
                                            str(round((float(current_order_size) / close), 3))
                                        )
                                        order_placed = True
                                        if len(buy_orders) == 1:
                                            current_order_size = safety_order
                                        elif len(buy_orders) >1:
                                            current_order_size *= multiplier
                                        break
                                    except Exception as e:
                                        print(f"Error placing order (attempt {_ + 1}): {e}")
                                        logs+="Error Placing order Retrying"
                                        time.sleep(1)  # Optional: Add a short delay between attempts

                                if order_placed:
                                    print (order)
                                    order_counter += 1
                                    collection = client['test']
                                    if (ex_type == "Binance Spot"):
                                            mongo_doc = map_order_to_mongo_doc(order, strategy_id, do['userId'])
                                    else:
                                        mongo_doc = {
                                        "_id": order["info"]["orderId"],
                                        "symbol": order["info"]["symbol"],
                                        "status": order["info"]["status"],
                                        "avgPrice": {"$numberInt": order["info"]["avgPrice"]},
                                        "executedQty": {"$numberDouble": order["info"]["executedQty"]},
                                        "cumQuote": {"$numberDouble": order["info"]["cumQuote"]},
                                        "timeInForce": order["info"]["timeInForce"],
                                        "type": order["info"]["type"],
                                        "side": order["info"]["side"],
                                        "price": {"$numberInt": order["price"]},
                                        "cost": {"$numberDouble": order["cost"]},
                                        "average": {"$numberInt": order["average"]},
                                        "filled": {"$numberDouble": order["filled"]},
                                        "remaining": {"$numberInt": order["remaining"]},
                                        "totalProfit": {"$numberDouble": 0.0},  # Assuming 0.0 for this example
                                        "runDateTime": {"$date": {"$numberLong": order["info"]["updateTime"]}},
                                        "strategyId": {"$oid": strategy_id},  # assuming a static value for this example
                                        "created": {"$date": {"$numberLong": str(int(datetime.now().timestamp() * 1000))}},
                                        "__v": {"$numberInt": "0"},
                                        "userId": {"$oid": do['userId']}, }
                                    
                                    orders=collection['orders']
                                    orders.insert_one(mongo_doc)
                                    if action == 'buy':
                                        buy_orders.append(order)
                                        print (order)
                                    elif action == 'sell':
                                        sell_orders.append(order)
                                    logs += str(action.capitalize()) + " order placed: " + str(close) + " for " + str(current_order_size) + '\n'
                                    logs += "Order Filled for " + str(order['price'])+"\n"
                                else:
                                        print(f"Failed to place {action} order after {retries} attempts")

                    elif conditions_hit% int (buyOn) !=0 or price_check(buy_orders, close)!=False:
                        # print ("buy on condition ignore : ",conditions_hit,"%",buyOn,"=",conditions_hit% int (buyOn))
                        # print ("price returned by Price check ",price_check(buy_orders,close))
                        logs += "buy on condition ignore : " + str(conditions_hit)+"%"+str(buyOn)+"="+str((conditions_hit)% int (buyOn)) + '\n'
                        logs += "price returned by Price check " + str(price_check(buy_orders,close))+'\n'



        # Monitor orders and check for 3% profit
        total_price = 0
        total_filled = 0
        total_tickers_bought = 0
        for order in buy_orders:
            order_id = order['id']
            try:
                order_data = exchange.fetch_order(order_id, symbol)
            except Exception as e:
                print (e)
                # logs += str (e)+'\n'
                continue
            if order_data['status'] == 'closed':
                total_price += order_data['average'] * order_data['filled']
                total_filled += order_data['filled']
                total_tickers_bought += order_data['filled']
                try:
                    current_price = exchange.fetch_ticker(symbol)['last']
                except Exception as e:
                    print (e)
                    # logs += str (e)+'\n'
                    continue
                
                if total_filled > 0:
                    avg_price = total_price / total_filled
                else:
                    avg_price = 0
                if ProfitType == 'Fixed':
                    profit = (current_price - avg_price) / avg_price
                    take_profit = profit >= take_profit_percentage
                elif ProfitType == 'Candle body':
                    take_profit = current_price >= first_order_candle_body_price
                elif ProfitType == 'Candle wick':
                    take_profit = current_price >= first_order_candle_wick_price
                else:
                    take_profit = False

                if take_profit:
                    # Take profit
                    tickerAmount = total_tickers_bought
                    try:
                        sell_order = exchange.create_order(symbol, orderType, 'sell', tickerAmount)
                        sell_orders.append(sell_order)
                        print(f"Taking profit: {sell_order}")
                        logs += "Taking profit: " +str(sell_order)
                        buy_orders.remove(order)
                        collection = client['test']
                        if (ex_type == "Binance Spot"):
                                            mongo_doc = map_order_to_mongo_doc(order, strategy_id, do['userId'])
                        else:
                            mongo_doc = {
                            "_id": order["info"]["orderId"],
                            "symbol": order["info"]["symbol"],
                            "status": order["info"]["status"],
                            "avgPrice": {"$numberInt": order["info"]["avgPrice"]},
                            "executedQty": {"$numberDouble": order["info"]["executedQty"]},
                            "cumQuote": {"$numberDouble": order["info"]["cumQuote"]},
                            "timeInForce": order["info"]["timeInForce"],
                            "type": order["info"]["type"],
                            "side": order["info"]["side"],
                            "price": {"$numberInt": order["price"]},
                            "cost": {"$numberDouble": order["cost"]},
                            "average": {"$numberInt": order["average"]},
                            "filled": {"$numberDouble": order["filled"]},
                            "remaining": {"$numberInt": order["remaining"]},
                            "totalProfit": {"$numberDouble": 0.0},  # Assuming 0.0 for this example
                            "runDateTime": {"$date": {"$numberLong": order["info"]["updateTime"]}},
                            "strategyId": {"$oid": strategy_id},  # assuming a static value for this example
                            "created": {"$date": {"$numberLong": str(int(datetime.now().timestamp() * 1000))}},
                            "__v": {"$numberInt": "0"},
                            "userId": {"$oid": do['userId']}, }
                                        
                        orders=collection['orders']
                        orders.insert_one(mongo_doc)
                    except Exception as e:
                        print ("Error in Taking profit: ",e)
                        # log += str(e) +'\n'
        if (len(logs)>2):
            print (logs)
            collection = client['test']
            strats=collection['strategies']
            strategyID=strategy_id
            do = strats.find_one(ObjectId(strategyID))
            logs=logs.replace('\n','<br />')
            logs = remove_extra_br(logs)
            update_operation = {"$set": {"logs": do['logs']+'<br />'+logs}}
            result = strats.update_one({"_id":ObjectId(strategyID)}, update_operation)
                
def backtesting(client,strategy_id):
    collection = client['test']
    strats=collection['strategies']
    print (strategy_id)
    strategyID=strategy_id
    do = strategy_id
    order_size = do['orderSize']
    safety_order = do['safetyOrderSize']
    max_buy_orders = int(do['maxOrders'])
    # symbol = do['strategyPair']+'/USDT'
    symbol = do['strategyPair']
    timeframe = '1h'
    multiplier = do['candleSizeAndVol']
    stratType= do['strategyType']
    orderType=do['orderType']
    profitC='USDT'
    sandbox='True'
    buyOn=do['buyOnCondition']
    ignore=do['ignoreCondition']
    
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

    print(do['indicators'][0]['chooseIndicatorValue'])
    for indicators in do['indicators']:
        if (indicators['chooseIndicatorValue']=='Vector Candle'):
            enabledvector='True'
            timeframe_vector=indicators['timeFrameValue']
            for candle in indicators['candleValue']:
                if candle == 'red':
                    if (stratType=='Long'):
                        red_action='buy'
                    elif (stratType=='Short'):
                        red_action='buy'
                if candle == 'purple':
                    if (stratType=='Long'):
                        purple_action='buy'
                    elif (stratType=='Short'):
                        purple_action='buy'
                if candle == 'blue':
                    if (stratType=='Long'):
                        blue_action='buy'
                    elif (stratType=='Short'):
                        blue_action='buy'
                if candle == 'green':
                    if (stratType=='Long'):
                        green_action='buy'
                    elif (stratType=='Short'):
                        green_action='buy'
        elif (indicators['chooseIndicatorValue']=='Moving Averages'):
            enableMA='True'
            timeframe_MA.append( indicators['timeFrameValue'])
            MA_val.append(int(indicators['masValue']))
            MA_cond.append(indicators['masCondition'])




    


    ProfitType=do['takeProfit']
    take_profit_percentage=0
    try:
        if (do['takeProfit']=='Fixed'):
            take_profit_percentage = float(do['takeProfitPercent'])/100
    except:
        print("No Tp set")
    print ("Profit Required: ",take_profit_percentage)
    print (do['userId'])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print (userObj['exchanges'][0])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print ()
    db_exchange = do['exchange']
    exchange_to = find_exchange_by_id(userObj, db_exchange)
    print ("Exchangee ",exchange_to)
    ex_type = exchange_to['exchangeName']

    print (ex_type)


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


    
    current_order_size = float(order_size)
    last_candle_timestamp = None
    first_order_candle_body_price = None
    first_order_candle_wick_price = None
    order_counter= 0

    timestamp, open_prices, high, low, close, volume=0,0,0,0,0,0
    psvra_candles=[]
    profits = 0
    ohlcv = fetch_ohlcv_my(exchange, symbol, timeframe, limit=5000)
    print (len(ohlcv))
    # return
    ohlcv_for_MA=[]
    for i in range(0, len(timeframe_MA)):
        if (timeframe_vector == timeframe_MA[i]):
            ohlcv_for_MA.append(ohlcv)
        else:
            ohlcv_for_MA.append(fetch_ohlcv_my(exchange, symbol, timeframe_MA[i], limit=5000))
            # ohlcv_for_MA[i] = ohlcv_for_MA[i][:-1]  
    # ohlcv = ohlcv[:-1]
    iterator_loop=0
    for i in range(50, len(ohlcv)):
        print(iterator_loop, "Candle")
        current_candle = ohlcv[i]
        psvra_candles=ohlcv[i-10:i]
        timestamp, open_prices, high, low, close, volume = current_candle

        # Calculate the 50-period SMA

        if enabledvector == 'True':
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
            # print ("============================")
            # print("Timestamp",utc_time.strftime('%Y-%m-%d %H:%M:%S'),"  \nOpen:",open_prices,"  High:",high,"  Low:",low,"  Close:",close,"  \nCandle Type: ",candle_type,"  \nAvg. Vol:",round(av,3),"  Cur. Vol:",pvsra_volume)
            print ("============================\n")
            print("Timestamp"+(str(utc_time))+"  \nOpen:"+str(open_prices)+"  High:"+str(high)+"  Low:"+str(low)+"  Close:"+str(close)+"  \nCandle Type: "+candle_type+"  \nAvg. Vol:"+str(round(av,3))+"  Cur. Vol:"+str(pvsra_volume)+"\n")
            # Check if the candle type matches any of the conditions
            action = None
            if candle_type == 'RVC' and red_action != 'none':
                action = red_action
            elif candle_type == 'GVC' and green_action != 'none':
                action = green_action
            elif candle_type == 'BVC' and blue_action != 'none':
                action = blue_action
            elif candle_type == 'PVC' and purple_action != 'none':
                action = purple_action
            # Add other candle types if required
            
            if action is not None:
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
                        # Place a custom order
                        if enableMA == 'True':
                            all_conditions_met = True
                            sma_values = []
                            counter_MA=0
                            for cond, val, tf in zip(MA_cond, MA_val, timeframe_MA):
                                print (tf, val)
                                # ohlcv_MA = fetch_with_retry(exchange, symbol, tf, val)
                                # [i-10:i]
                                ohlcv_MA =ohlcv_for_MA[counter_MA][i-val:i]
                                counter_MA+=1
                                closing_prices = [x[4] for x in ohlcv_MA]
                                print ("LEn: ",i,len(ohlcv_MA))
                                sma = calculate_sma(closing_prices, val)
                                sma_values.append(sma)
                                print ("SMA Values: ",sma_values)
                                if cond == 'Above' and close <= sma:
                                    all_conditions_met = False
                                    break
                                elif cond == 'Below' and close >= sma:
                                    all_conditions_met = False
                                    break

                            if all_conditions_met:
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
                                    
                                elif action == 'sell':
                                    sell_orders.append(order)
                                    total_sell_orders.append(order)
                                    
                                print(str(action.capitalize()) + " order placed: " + str(close) + " for " + str(current_order_size) + '\n')
                                print("Order Filled for " + str(order['price']) + "\n")
                                
                            else:
                                print("Moving average conditions not met for all MAs: " + ', '.join([f"{cond} MA {sma}" for cond, sma in zip(MA_cond, sma_values)]) + '\n')
                        else:
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
            elif ProfitType == 'Candle body':
                take_profit = current_price >= first_order_candle_body_price
            elif ProfitType == 'Candle wick':
                take_profit = current_price >= first_order_candle_wick_price
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
    print ("Total Profit: ", profits)
    print (len(total_buy_orders))
    print (len(total_sell_orders))

    return {
        "candles": ohlcv,
        "profit" : profits,
        "buy_orders":total_buy_orders,
        "sell_orders":total_sell_orders,
        "candlesMA":ohlcv_for_MA
    }


# 644f90f5b40d77067c660398
# client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')

# lambda_function( client, '647b1341b5fc7d7b9aa74348')
