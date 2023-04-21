# celery.py
from celery import Celery
import pymongo
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# app = Celery("FAST", broker="pyamqp://guest@localhost//")

app = Celery("FAST", broker=os.environ['CLOUDAMQP_URL'])

@app.task
def run_bot_instance( strategy_id):
    import fetch
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')
    fetch.lambda_function( client, strategy_id)
