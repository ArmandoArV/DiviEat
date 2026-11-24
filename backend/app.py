import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.config import obtener_ajustes  # noqa: E402
from backend.middleware.errors import registrar_manejadores  # noqa: E402
from backend.repositories.charges import RepositorioDeCobros  # noqa: E402
from backend.routes import codi, webhooks  # noqa: E402
from database import db, test_database_connection  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

ajustes = obtener_ajustes()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Arrancar no debe depender de que Mongo este vivo: si no esta, la API
    # sube igual y `/salud` lo dice. Caerse al importar solo oculta la causa.
    if test_database_connection(db):
        RepositorioDeCobros(db).asegurar_indices()

    if not ajustes.pey_configurado:
        log.warning("PEY_API_KEY vacia: los cobros CoDi responderan 503 hasta configurarla")
    if ajustes.pey_test_mode:
        log.warning(
            "Modo de prueba activo: se rechazan cobros por encima de %s MXN. "
            "Pey no tiene sandbox, los cobros son con dinero real.",
            ajustes.pey_test_max_amount_mxn,
        )
    yield


app = FastAPI(title="DiviEat API", lifespan=ciclo_de_vida)

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


@app.get("/salud", tags=["salud"])
def salud() -> dict[str, object]:
    return {
        "ok": True,
        "pey_configurado": ajustes.pey_configurado,
        "modo_prueba": ajustes.pey_test_mode,
    }
