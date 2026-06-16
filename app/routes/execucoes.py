from pathlib import Path
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from app import db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/execucoes")
def execucoes(request: Request, page: int = Query(1)):
    return templates.TemplateResponse(request, "execucoes.html", db.listar_execucoes(page=page))
