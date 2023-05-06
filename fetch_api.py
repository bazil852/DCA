# import pymongo library
import pymongo
import ccxt
import time
import datetime
from bson.objectid import ObjectId
import re



def remove_extra_br(s):
    return re.sub(r'(<br />){3,}', '<br /><br />', s)


def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period



def fetch_with_retry(exchange, symbol, timeframe,numb, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, limit=numb)
        except ccxt.RequestTimeout as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e


def pvsra_indicator(overridesym, pvsra_volume, volume, pvsra_high, pvsra_low, high,open_prices, low, pvsra_close, close):
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
        print(e)
        multiplier=1
    try:
        buyOn= float(buyOn)
    except Exception as e:
        print(e)
        buyOn=1
    if (buyOn<=0):
        buyOn=1
    try:
        ignore= float(ignore)
    except Exception as e:
        print(e)
        ignore=0
    try:
        if (safety_order<=0):
            safety_order=order_size
    except Exception as e:
        print(e)
        safety_order=order_size
    
    try:
        max_buy_orders=int(max_buy_orders)
        if (max_buy_orders<=0):
            max_buy_orders=100000
    except Exception as e:
        print(e)
        max_buy_orders=100000000
    try:
        order_size=float(order_size)
    except Exception as e:
        print(e)
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
    print (do['userId'])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print (userObj['exchanges'][0])
    users=collection['users']
    userObj=users.find_one(ObjectId(do['userId']))
    print ()
    APIKEY=userObj['exchanges'][0]['apiKey']
    APISECRET=userObj['exchanges'][0]['apiSecret']
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
    
    print ( "Validating Data")
    print (order_size, type(order_size))
    print (safety_order, type(safety_order))
    print (multiplier, type(multiplier))
    print (max_buy_orders, type(max_buy_orders))
    print (timeframe, type(timeframe))
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
        except Exception as e:
            print("Error")
            print (e)
        ohlcv = psvra_candles[-2]
        timestamp, open_prices, high, low, close, volume = ohlcv


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
                utc_time = datetime.datetime.utcfromtimestamp(timestamp / 1000.0)
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
                                        order_counter += 1
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
                                    order_counter += 1
                                    if action == 'buy':
                                        buy_orders.append(order)
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
                
# 644f90f5b40d77067c660398
# client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')

# lambda_function( client, '6454267fbb456701757d9089')