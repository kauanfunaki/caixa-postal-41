"""Caixa Postal 41 — web app de consulta e-CAC / Regularize."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes import cnpjs, mensagens, execucoes, notificacoes
from app.db import inicializar_tabelas_notificacao

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_tabelas_notificacao()
    yield


app = FastAPI(title="Caixa Postal 41", docs_url=None, redoc_url=None, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

app.include_router(cnpjs.router)
app.include_router(mensagens.router)
app.include_router(execucoes.router)
app.include_router(notificacoes.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/caixa-postal")
