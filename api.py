from fastapi import FastAPI
# import pymongo
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery import Celery
from celery_worker import run_bot_instance  # Import the Celery task

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





class StrategyIdPayload(BaseModel):
    strategyId: str




@app.post("/start")
async def start_bot(payload: StrategyIdPayload):
    strategy_id = payload.strategyId
    print(strategy_id)

    # Replace the background_tasks.add_task() call with the new Celery task
    run_bot_instance.delay(  strategy_id)

    return {"status": "success", "message": "Bot started"}

@app.post("/stop")
async def stop_bot():
    # Add your logic to stop the trading bot here
    print('Trying to end')
    return {"status": "success", "message": "Bot stopped"}





