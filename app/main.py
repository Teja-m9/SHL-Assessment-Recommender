from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.chat_controller import router as chat_router

app = FastAPI(title="SHL Assessment Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
