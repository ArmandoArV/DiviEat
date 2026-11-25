import logging
from database import db, test_database_connection
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # 1. Import HTMLResponse
from routes.payment import v1_router


app = FastAPI()

database = db

test_database_connection(database)
app.include_router(v1_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def read_root():
  return """
    <html>
        <body>
            <h1>No hay nada que ver aqui</h1>
            <img src="https://media1.tenor.com/m/_dwxwkNKrFUAAAAC/minecraft-fox-spinning.gif" />
        </body>
    </html>
    """


@app.get("/api/user/1",)
def get_user_1():
    return {"id": 1, "name": "User 1", "email": "user1@example.com", "age": 30}

