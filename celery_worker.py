# celery.py
from celery import Celery
import pymongo
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Celery("FAST", broker="amqps://xtkvujcj:ce8VrWABVujkd9mRlQkVhVU2eaU7i1w1@whale.rmq.cloudamqp.com/xtkvujcj")

# amqps://ouifibyf:V541bgbpT1dP6dQnOhHRy1yWJ97vdqmO@stingray.rmq.cloudamqp.com/ouifibyf
# amqps://ouifibyf:V541bgbpT1dP6dQnOhHRy1yWJ97vdqmO@stingray.rmq.cloudamqp.com/ouifibyf


# app = Celery("FAST", broker=os.environ['CLOUDAMQP_URL'])

@app.task
def run_bot_instance( bot_id, bot_name, bot_type, description, 
        exchange_id, exchange_name, exchange_type, api_key, secret_key, user_id,
        strategy_ids, time_frame, user_email, user_first_name, user_last_name, 
        account_verified, state):
    import fetch_api
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
    fetch_api.lambda_function( client,bot_id, bot_name, bot_type, description, 
        exchange_id, exchange_name, exchange_type, api_key, secret_key, user_id,
        strategy_ids, time_frame, user_email, user_first_name, user_last_name, 
        account_verified, state)

@app.task
def run_backtest( strategy_id):
    import fetch_api
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
    fetch_api.backtesting( client, strategy_id)
