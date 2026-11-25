import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # 1. Import HTMLResponse
from routes.payment import v1_router



@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Arrancar no debe depender de que Mongo este vivo: si no esta, la API
    # sube igual y `/salud` lo dice. Caerse al importar solo oculta la causa.
    if test_database_connection(db):
        RepositorioDeCobros(db).asegurar_indices()

test_database_connection(database)
app.include_router(v1_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registrar_manejadores(app)
app.include_router(codi.router)
app.include_router(webhooks.router)


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

