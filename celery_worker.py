# celery.py
from celery import Celery
import pymongo
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Celery("FAST", broker="pyamqp://guest@localhost//")

# amqps://ouifibyf:V541bgbpT1dP6dQnOhHRy1yWJ97vdqmO@stingray.rmq.cloudamqp.com/ouifibyf
# amqps://ouifibyf:V541bgbpT1dP6dQnOhHRy1yWJ97vdqmO@stingray.rmq.cloudamqp.com/ouifibyf


# app = Celery("FAST", broker=os.environ['CLOUDAMQP_URL'])

@app.task
def run_bot_instance( strategy_id):
    import fetch_api
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
    fetch_api.lambda_function( client, strategy_id)

@app.task
def run_backtest( strategy_id):
    import fetch_api
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
    fetch_api.backtesting( client, strategy_id)
