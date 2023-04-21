# import pymongo library
import pymongo
import ccxt
import time
import datetime
from bson.objectid import ObjectId
from ccxt.base.errors import RequestTimeout







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
        va='GC'
        if (pvsra_volume[8] <= (av*2) and pvsra_volume[8] >= (av*1.5)):
            va='BVC'
        elif (pvsra_volume[8] > (av*2 ) ) :
            va ='GVC'
    else:
        va='RC'
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


def fetch_with_retry(exchange, symbol, timeframe, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, limit=10)
        except RequestTimeout as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e




def lambda_function(client,strategy_id):
    collection = client['test']
    strats=collection['strategies']
    strategyID=strategy_id
    do = strats.find_one(ObjectId(strategyID))
    order_size = do['orderSize']
    safety_order = do['safetyOrderSize']
    # max_buy_orders = int(do['maxOrders'])
    try:
        max_buy_orders_float = float(do['maxOrders'])
        max_buy_orders = int(max_buy_orders_float)
    except ValueError:
        max_buy_orders=0
        print("Invalid input: do['maxOrders'] must be a numeric value.")
    # symbol = do['strategyPair']+'/USDT'
    symbol = do['strategyPair']
    timeframe = '1m'
    multiplier = do['candleSizeAndVol']
    stratType= do['strategyType']
    orderType=do['orderType']
    profitC='USDT'
    sandbox='True'
    buyOn=do['buyOnCondition']
    ignore=do['ignoreCondition']

    if (str (multiplier) == ''):
        multiplier = 1
    else:
        multiplier = float(multiplier) 
    try:
        if (buyOn == None or len (buyOn)==0):
            buyOn=1
        if (ignore == None or len (buyOn)==0):
            ignore = 0
        print(int(buyOn),int(ignore))
    except Exception as e:
        buyOn=1
        ignore = 0


    # Temp Variables
    buy_orders = []
    buy_candles=[]
    sell_orders=[]
    overridesym = True
    stop_ordering=False
    total=0
    
    ignore_conditions=0
    buy_on_counter=0



    # Fetching Inicators
    try:
        if (do['indicator']=='Vector Candle'):
            enabledvector='True'
            red_action=do['indicatorValues']['redAction']
            blue_action=do['indicatorValues']['blueAction']
            green_action=do['indicatorValues']['greenAction']
            purple_action=do['indicatorValues']['purpleAction']
        else:
            enabledvector='False'
            red_action='none'
            blue_action='none'
            green_action='none'
            purple_action='none'
    except Exception as e:
        print("Error aa gya" , e)

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
        'rateLimit': 1200,  # Minimum time between requests in milliseconds
        'options': {
            'defaultType': 'future',
        },
        'timeout': 30000,  # Increase timeout to 30 seconds
    })
    exchange.set_sandbox_mode(True)
    
    print ( "Validating Data")
    print (order_size)
    print (safety_order)
    print (multiplier)
    print (max_buy_orders)
    print (timeframe)
    print (orderType)
    print (red_action)
    print (purple_action)
    print (blue_action)
    print (green_action)
    print (symbol.replace('/',''))

    logs= str(order_size)+'<br />'+str(safety_order)+'<br />'+str(multiplier)+'<br />'+str(max_buy_orders)+'<br />'+str(timeframe)+'<br />'+str(orderType)+'<br />'+str(red_action)+'<br />'+str(purple_action)+'<br />'+str(blue_action)+'<br />'+str(green_action)+'<br />'
    
    update_operation = {"$set": {"logs":logs}}
    result = strats.update_one({"_id":ObjectId(strategyID)}, update_operation)

    if result.modified_count > 0:
        print("Document updated successfully.")
    else:
        print("No document matched the filter, or the document was already updated.")
    while (True):
        logs=""
        # set up connection to MongoDB Cloud
        # client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority/')
        print ("Bot state is : ",do['state'])
        
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
        
        candles = fetch_with_retry(exchange, symbol, timeframe)
        latest_candle = candles[-1]
        timestamp = [timestamp[0] for timestamp in candles]
        open_price = [opens[1] for opens in candles]
        high = [high[2] for high in candles]
        low = [low[3] for low in candles]
        close = [candle[4] for candle in candles]
        volume = [volume[5] for volume in candles]
        pvsra_high = [high[2] for high in candles]
        pvsra_low = [low[3] for low in candles]
        pvsra_volume = [volume[5] for volume in candles]
        close_prices = [candle[4] for candle in candles]
        pvsra_close = close_prices
        # print(close_prices)
        # print ( "PREV VOLUME: ",pvsra_volume)
        # print ("====================",trading_control.should_stop,"============================")
        logs+="================================================"+"\n"
        va,av = pvsra_indicator(overridesym, pvsra_volume, volume, pvsra_high, pvsra_low, high,open_price, low, pvsra_close, close_prices)
        utc_time = datetime.datetime.utcfromtimestamp(timestamp[8] / 1000.0)
        # print("Timestamp",utc_time.strftime('%Y-%m-%d %H:%M:%S'),"  \nOpen:",open_price[8],"  High:",high[8],"  Low:",low[8],"  Close:",close[8],"  \nCandle Type: ",va,"  \nAvg. Vol:",round(av,3),"  Cur. Vol:",pvsra_volume[8])
        logs+="Timestamp"+str(utc_time.strftime('%Y-%m-%d %H:%M:%S'))+"  \nOpen:"+str(open_price[8])+"  High:"+str(high[8])+"  Low:"+str(low[8])+"  Close:"+str(close[8])+"  \nCandle Type: "+va+"  \nAvg. Vol:"+str(round(av,3))+"  Cur. Vol:"+str(pvsra_volume[8])+"\n"
        # print("Open:",open_price[8],"  High:",high[8],"  Low:",low[8],"Close: ",close[8],"Volume: ",pvsra_volume[8],"Color: ",va)
        if (stop_ordering==False):
            if is_purple_candle(va) or is_red_candle(va):
                if (enabledvector=='True' and purple_action!='None' and is_purple_candle(va) ):
                    buy_on_counter+=1
                    if ignore_conditions<int(ignore):
                        logs+="Condition ignored as asked: Count " + str(ignore_conditions)
                        ignore_conditions+=1
                        continue
                    if (len(buy_orders)==1):
                        total =float(safety_order)
                    elif (len(buy_orders)==0):
                        total =float(order_size)
                    else:
                        total =total * float(multiplier) 
                    if (purple_action=='buy' ):  
                        if (price_check(buy_orders,close[8])==False or buy_on_counter%int(buyOn)!=0):                   
                            if (len(buy_orders)==0):
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, purple_action, str(round((float(order_size)/close[8]),3)),params)
                                # print(orderType,purple_action," Order Placed at Price: ", close[8])
                                # print(orderType,purple_action," Order filled at Price: ", order['price'])
                                logs+=orderType+purple_action+" Order Placed at Price: "+ str(close[8])+"\n"
                                logs+=orderType+purple_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            
                            else:
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, purple_action, str(round((float(total)/close[8]),3)),params)
                                # print(orderType,purple_action,"Safety Order Placed at Price: ", close[8]," (",len(buy_orders)," of ",max_buy_orders,")")
                                # print(orderType,purple_action," Order filled at Price: ", order['price']) 
                                logs+=orderType+purple_action+"Safety Order Placed at Price: "+ str(close[8])+" ("+str(len(buy_orders))+" of "+str(max_buy_orders)+")"+"\n"
                                logs+=orderType+purple_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            if (str (multiplier) == ''):
                                safety_order = safety_order
                            else:
                                safety_order *= float(multiplier)
                            buy_orders.append(order)
                            buy_candles.append([high[8],low[8],close[8],open_price[8]])
                        else:
                            # print("Order not placed price is above last price")
                            logs+="Order not placed price is above last price"+"\n"
                    elif ((purple_action=='sell') and len(buy_orders)>1):
                        tickerAmount=''
                        for pos in orders['info']['positions']:
                            if pos['symbol']==symbol.replace('/',''):
                                tickerAmount= pos['positionAmt']
                                new_buy_price = float (pos['entryPrice'])
                                break
                        params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                        order = exchange.create_order(symbol, orderType, purple_action, float(round(tickerAmount,3)),params)
                        temp_price=order['price']            
                        sell_orders.append(order)
                        buy_orders=[]
                        total=0
                        stop_ordering=False
                        # print(orderType,purple_action," Order Placed at Price: ", temp_price)
                        # print(orderType,purple_action," Order filled at Price: ", order['price'])
                        logs+=orderType+purple_action+" Order Placed at Price: "+ str(temp_price)+"\n"
                        logs+=orderType+purple_action+" Order filled at Price: "+ str(order['price'])+"\n"
                    
                if (enabledvector=='True' and red_action!='None' and is_red_candle(va)):

                    buy_on_counter+=1
                    if ignore_conditions<int(ignore):
                        logs+="Condition ignored as asked: Count " + str(ignore_conditions)
                        ignore_conditions+=1
                        continue
                    if (len(buy_orders)==1):
                        total =float(safety_order)
                    elif (len(buy_orders)==0):
                        total =float(order_size)
                    else:
                        total =total * float(multiplier) 
                    if ((red_action=='buy') ):
                        if (price_check(buy_orders,close[8])==False or buy_on_counter%int(buyOn)!=0):
                            if (len(buy_orders)==0):
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, red_action, str(round((float(order_size)/close[8]),3)),params)
                                # print(orderType,red_action," Order Placed at Price: ", close[8])
                                # print(orderType,red_action," Order filled at Price: ", order['price']) 
                                logs+=orderType+red_action+" Order Placed at Price: "+ str(close[8])+"\n"
                                logs+=orderType+red_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            else:
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, red_action, str(round((float(total)/close[8]),3)),params)
                                # print(orderType,red_action,"Safety Order Placed at Price: ", close[8]," (",len(buy_orders)," of ",max_buy_orders,")") 
                                # print(orderType,red_action," Order filled at Price: ", order['price']) 
                                logs+=orderType+red_action+"Safety Order Placed at Price: "+ str(close[8])+" ("+str(len(buy_orders))+" of "+str(max_buy_orders)+")"+"\n"
                                logs+=orderType+red_action+" Order filled at Price: "+ str(order['price'])+"\n"


                            if (str (multiplier) == ''):
                                safety_order = safety_order
                            else:
                                safety_order *= float(multiplier)
                            buy_orders.append(order)
                            buy_candles.append([high[8],low[8],close[8],open_price[8]])

                        else:
                            # print("Order not placed price is above last price")
                            logs+="Order not placed price is above last pricec or condition was not met"+"\n"
                    elif (red_action=='sell' and len(buy_orders)>1):
                        tickerAmount=''
                        for pos in orders['info']['positions']:
                            if pos['symbol']==symbol.replace('/',''):
                                tickerAmount= pos['positionAmt']
                                new_buy_price = float (pos['entryPrice'])
                                break
                        params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                        order = exchange.create_order(symbol, orderType, red_action, tickerAmount,params)
                        temp_price=order['price']            
                        sell_orders.append(order)
                        buy_orders=[]
                        total=0
                        stop_ordering=False
                        # print(orderType,red_action," Order Placed at Price: ", temp_price)
                        # print(orderType,red_action," Order filled at Price: ", order['price']) 
                        logs+=orderType+red_action+" Order Placed at Price: "+ str(temp_price)+"\n"
                        logs+=orderType+red_action+" Order filled at Price: "+ str(order['price'])+"\n"
        
            
            elif (is_blue_candle(va) or is_green_candle(va)):
                if (enabledvector=='True' and blue_action!='None' and is_blue_candle(va)):
                    buy_on_counter+=1
                    if ignore_conditions<int(ignore):
                        logs+="Condition ignored as asked: Count " + str(ignore_conditions)
                        ignore_conditions+=1
                        continue
                    if (len(buy_orders)==1):
                        total =float(safety_order)
                    elif (len(buy_orders)==0):
                        total =float(order_size)
                    else:
                        total =total * float(multiplier) 
                    if (blue_action=='buy' ):
                        if (price_check(buy_orders,close[8])==False or buy_on_counter%int(buyOn)!=0):
                            if (len(buy_orders)==0):
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, blue_action, str(round((float(order_size)/close[8]),3)),params)
                                # print(orderType,blue_action," Order Placed at Price: ", close[8])
                                # print(orderType,blue_action," Order filled at Price: ", order['price']) 
                                logs+=orderType+blue_action+" Order Placed at Price: "+ str(close[8])+"\n"
                                logs+=orderType+blue_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            else:
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, blue_action, str(round((float(total)/close[8]),3)),params)
                                # print(orderType,blue_action,"Safety Order Placed at Price: ", close[8]," (",len(buy_orders)," of ",max_buy_orders,")")
                                # print(orderType,blue_action," Order filled at Price: ", order['price']) 
                                logs+=orderType+blue_action+"Safety Order Placed at Price: "+ str(close[8])+" ("+str(len(buy_orders))+" of "+str(max_buy_orders)+")"+"\n"
                                logs+=orderType+blue_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            if (str (multiplier) == ''):
                                safety_order = safety_order
                            else:
                                safety_order *= float(multiplier)
                            buy_orders.append(order)
                            buy_candles.append([high[8],low[8],close[8],open_price[8]])
                        else:
                            # print("Order not placed price is above last price")
                            logs+="Order not placed price is above last price"+"\n"
                        
                    elif (blue_action=='sell' and len(buy_orders)>1):
                        tickerAmount=''
                        for pos in orders['info']['positions']:
                            if pos['symbol']==symbol.replace('/',''):
                                tickerAmount= pos['positionAmt']
                                new_buy_price = float (pos['entryPrice'])
                                break
                        params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                        order = exchange.create_order(symbol, orderType, blue_action, tickerAmount,params)
                        temp_price=order['price']            
                        sell_orders.append(order)
                        buy_orders=[]
                        total=0
                        stop_ordering=False
                        # print(orderType,blue_action," Order Placed at Price: ", temp_price)
                        # print(orderType,blue_action," Order filled at Price: ", order['price'])   
                        logs+=orderType+blue_action+" Order Placed at Price: "+ str(temp_price)+"\n"
                        logs+=orderType+blue_action+" Order filled at Price: "+ str(order['price'])+"\n"
                    
                if (enabledvector=='True' and green_action!='None' and is_green_candle(va)):

                    buy_on_counter+=1

                    if ignore_conditions<int(ignore):
                        logs+="Condition ignored as asked: Count " + str(ignore_conditions)
                        ignore_conditions+=1
                        continue
                    if (len(buy_orders)==1):
                        total =float(safety_order)
                    elif (len(buy_orders)==0):
                        total =float(order_size)
                    else:
                        total =total * float(multiplier) 
                    if (green_action=='buy' ):
                        if (price_check(buy_orders,close[8])==False or buy_on_counter%int(buyOn)!=0):                     
                            if (len(buy_orders)==0):
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, green_action, str(round((float(order_size)/close[8]),3)),params)
                                # print(orderType,green_action," Order Placed at Price: ", close[8])
                                # print(orderType,green_action," Order filled at Price: ", order['price'])
                                logs+=orderType+green_action+" Order Placed at Price: "+ str(close[8])+"\n"
                                logs+=orderType+green_action+" Order filled at Price: "+ str(order['price'])+"\n"
                                
                            else:
                                params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                                order = exchange.create_order(symbol, orderType, green_action, str(round((float(total)/close[8]),3)),params)
                                # print(orderType,green_action,"Safety Order Placed at Price: ", close[8]," (",len(buy_orders)," of ",max_buy_orders,")")
                                # print(orderType,green_action," Order filled at Price: ", order['price'])                
                                logs+=orderType+green_action+"Safety Order Placed at Price: "+ str(close[8])+" ("+str(len(buy_orders))+" of "+str(max_buy_orders)+")"+"\n"
                                logs+=orderType+green_action+" Order filled at Price: "+ str(order['price'])+"\n"
                            
                            if (str (multiplier) == ''):
                                safety_order = safety_order
                            else:
                                safety_order *= float(multiplier)
                            buy_orders.append(order)
                            buy_candles.append([high[8],low[8],close[8],open_price[8]])
                        else:
                            # print("Order not placed price is above last price")
                            logs+="Order not placed price is above last price"+"\n"
                    elif (green_action=='sell' and len(buy_orders)>1):
                        tickerAmount=''
                        for pos in orders['info']['positions']:
                            if pos['symbol']==symbol.replace('/',''):
                                tickerAmount= pos['positionAmt']
                                new_buy_price = float (pos['entryPrice'])
                                break
                        params = {
                                    'timestamp': int(time.time() * 1000)
                                }
                        order = exchange.create_order(symbol, orderType, blue_action, tickerAmount,params)
                        temp_price=order['price']            
                        sell_orders.append(order)
                        buy_orders=[]
                        total=0
                        stop_ordering=False
                        # print(orderType,blue_action," Order Placed at Price: ", temp_price)
                        # print(orderType,blue_action," Order filled at Price: ", order['price'])
                        logs+=orderType+blue_action+" Order Placed at Price: "+ str(temp_price)+"\n"
                        logs+=orderType+blue_action+" Order filled at Price: "+ str(order['price'])+"\n"
        
        
        else:
            # print("Max Order Limit Reached.\n")
            logs+="Max Order Limit Reached.\n"+"\n"

        # Check for take profit
        start_time = time.time()
        check=True
        # print("Order",order)
        # exit()
        iterate=0
        while (time.time() - start_time < 50) :
            new_buy_price=0
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
            if (len(buy_orders)>0):
                for order in buy_orders:
                    order_price = order['price']
                    new_buy_price+=float(order_price)
                new_buy_price=new_buy_price/len(buy_orders)
                current_price = exchange.fetch_ticker(symbol)['last']
                orders = exchange.fetch_balance()
                tickerAmount=''
                for pos in orders['info']['positions']:
                    if pos['symbol']==symbol.replace('/',''):
                        tickerAmount= pos['positionAmt']
                        new_buy_price = float (pos['entryPrice'])
                        break
                
                if (iterate<1 and new_buy_price!=0):
                    if (ProfitType == 'Fixed'):
                        logs+="Take profit at "+str(round(float(new_buy_price)+(float(new_buy_price) * float(take_profit_percentage)),3))+"\n"
                        logs+="Take profit order at: "+str(round(float(take_profit_percentage)*100,3))+"\n"
                        logs+="Avg Price is : "+str(round(new_buy_price,3))+"\n"
                    else:
                        logs+="Take profit is set to : " + ProfitType+"\n"
                    
                    if (len(buy_orders)==1):
                        # print("Base Order Volume is : ",order_size,profitC)
                        logs+="Base Order Volume is : "+str(order_size)+str(profitC)+"\n"
                        
                    else:
                        # print("Safety Order Volume is : ",total,profitC)
                        logs+="Safety Order Volume is : "+str(total)+str(profitC)+"\n"
                    # print ("Total Volume for orders is ",round(float(tickerAmount)*float(current_price),3))
                    logs+="Total Volume for orders is "+str(round(float(tickerAmount)*float(current_price),3))+"\n"
                # print (current_price," ",new_buy_price," ",take_profit_percentage)
                if ((current_price - new_buy_price) / new_buy_price >= take_profit_percentage) and ProfitType=='Fixed':
                    exchange.create_order(symbol, orderType, 'sell', tickerAmount, {'price': None})
                    # print("Profit Taken at: ", current_price)
                    logs+="Profit Taken at: "+str(current_price)+"\n"
                    buy_orders=[]
                    total=0
                    stop_ordering=False
                elif (ProfitType=='At candle body'): 
                    check_price= buy_orders[0]['price']         
                    for i in range(len(buy_orders)):
                        # if (exchange.fetch_ticker(symbol)['last']>=((buy_candles[i][2] + buy_candles[i][3])/2)):
                        #     exchange.create_order(symbol, orderType, 'sell', buy_orders[i]['amount'], {'price': None})
                        #     logs+="Profit Taken at: "+str(order)+"\n"
                        if (exchange.fetch_ticker(symbol)['last']>=  buy_candles[i][2]):
                            exchange.create_order(symbol, orderType, 'sell', buy_orders[i]['amount'], {'price': None})
                            logs+="Profit Taken at: "+str(order)+"\n"

            iterate+=1
        print (logs)
        collection = client['test']
        strats=collection['strategies']
        strategyID=strategy_id
        do = strats.find_one(ObjectId(strategyID))
        logs=logs.replace('\n','<br />')
        update_operation = {"$set": {"logs": do['logs']+'<br />'+logs}}
        result = strats.update_one({"_id":ObjectId(strategyID)}, update_operation)
                
        

# lambda_function(buy_orders, sell_orders, stop_ordering, total, overridesym)