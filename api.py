from fastapi import FastAPI
# import pymongo
import fetch_api
import pymongo
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery_worker import run_bot_instance  # Import the Celery task
from celery_worker import run_backtest
from typing import Dict, Any

app = FastAPI()





app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='https?://.*',  # Allow any domain, but restrict to HTTP and HTTPS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)






class StrategyIdPayload(BaseModel):
    strategyId: str




@app.post("/start")
async def start_bot(payload: StrategyIdPayload):
    strategy_id = payload.strategyId
    print(strategy_id)

    # Replace the background_tasks.add_task() call with the new Celery task
    run_bot_instance.delay(  strategy_id)

    return {"status": "success", "message": "Bot started"}

@app.post("/backtest")
async def run_backtest(payload: Dict[Any, Any]):
    strategy_id = payload
    # set up connection to MongoDB Cloud
    client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')

    result = fetch_api.backtesting(client, strategy_id)
    
    return result

@app.post("/stop")
async def stop_bot():
    # Add your logic to stop the trading bot here
    print('Trying to end')
    return {"status": "success", "message": "Bot stopped"}





