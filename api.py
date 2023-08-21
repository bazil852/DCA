from fastapi import FastAPI
# import pymongo
import fetch_api
import pymongo
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from celery_worker import run_bot_instance  # Import the Celery task
from celery_worker import run_backtest
from typing import Dict, Any, List

app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





class StrategyIdPayload(BaseModel):
    strategyId: str

class Exchange(BaseModel):
    id: int
    exchange_name: str
    exchange_type: str
    api_key: str
    secret_key: str
    user_id: int

class User(BaseModel):
    email: str
    id: int
    firstName: str
    lastName: str
    accountVerified: bool

class BotStartPayload(BaseModel):
    id: str = Field(alias="_id")
    botName: str
    botType: str
    description: str
    exchange: Exchange
    strategyId: List[str]
    timeFrame: str
    user: User
    state: str



@app.post("/start")
async def start_bot(payload: BotStartPayload):
    # Extract data from the incoming payload
    bot_id = payload.id
    bot_name = payload.botName
    bot_type = payload.botType
    description = payload.description
    exchange_data = payload.exchange
    strategy_ids = payload.strategyId
    time_frame = payload.timeFrame
    user_data = payload.user
    state = payload.state


    # Parsing exchange details
    exchange_id = exchange_data.id
    exchange_name = exchange_data.exchange_name
    exchange_type = exchange_data.exchange_type
    api_key = exchange_data.api_key
    secret_key = exchange_data.secret_key
    user_id = exchange_data.user_id

    # Parsing user details
    user_email = user_data.email
    user_first_name = user_data.firstName
    user_last_name = user_data.lastName
    account_verified = user_data.accountVerified

    # Given the bot might use multiple strategies, we can iterate over strategy_ids
    
    # Passing all the parsed variables to run_bot_instance.delay
    run_bot_instance.delay(
        bot_id, bot_name, bot_type, description, 
        exchange_id, exchange_name, exchange_type, api_key, secret_key, user_id,
        strategy_ids[0], time_frame, user_email, user_first_name, user_last_name, 
        account_verified, state
    )

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





