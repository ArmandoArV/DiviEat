import logging
from database import db, test_database_connection
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # 1. Import HTMLResponse

app = FastAPI()

database = db

test_database_connection(database)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)  # 2. Add response_class=HTMLResponse
def read_root():
  return """
    <html>
        <body>
            <h1>No hay nada que ver aqui</h1>
            <img src="https://media1.tenor.com/m/_dwxwkNKrFUAAAAC/minecraft-fox-spinning.gif" />
        </body>
    </html>
    """
