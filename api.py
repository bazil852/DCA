from fastapi import FastAPI, BackgroundTasks
import fetch
import pymongo
import ccxt

from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()


origins = [
    "https://funny-hamster-41a977.netlify.app",  # Replace this with your React app's origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# set up connection to MongoDB Cloud
client = pymongo.MongoClient('mongodb+srv://Prisoner479:DMCCODbo3456@testing.qsndjab.mongodb.net/?retryWrites=true&w=majority')


class TradingControl:
    def __init__(self):
        self.should_stop = False

class StrategyIdPayload(BaseModel):
    strategyId: str


trading_control = TradingControl()
@app.post("/start")
async def start_bot(background_tasks: BackgroundTasks,payload: StrategyIdPayload):
    # Add your logic to start the trading bot here
    trading_control.should_stop = False
    strategy_id = payload.strategyId
    print(strategy_id)
    background_tasks.add_task(fetch.lambda_function,trading_control,client,strategy_id)
    return {"status": "success", "message": "Bot started"}

@app.post("/stop")
async def stop_bot():
    # Add your logic to stop the trading bot here
    print('Trying to end')
    trading_control.should_stop = True
    return {"status": "success", "message": "Bot stopped"}





