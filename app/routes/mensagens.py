from pathlib import Path
from fastapi import APIRouter, Request, Query
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from app import db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/caixa-postal")
def caixa_postal(
    request: Request,
    fonte: str = Query("ecac"),
    cnpj: str = Query(""),
    q: str = Query(""),
    data_ini: str = Query(""),
    data_fim: str = Query(""),
    page: int = Query(1),
):
    cnpjs_lista = db.listar_cnpjs()
    if fonte == "regularize":
        dados = db.listar_mensagens_regularize(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim, page=page)
    else:
        dados = db.listar_mensagens_ecac(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim, page=page)
    return templates.TemplateResponse(request, "caixa_postal.html", {
        "fonte": fonte, "cnpj_sel": cnpj, "q": q,
        "data_ini": data_ini, "data_fim": data_fim,
        "cnpjs_lista": cnpjs_lista, **dados,
    })


@router.get("/caixa-postal/export")
def exportar(
    fonte: str = Query("ecac"),
    cnpj: str = Query(""),
    q: str = Query(""),
    data_ini: str = Query(""),
    data_fim: str = Query(""),
):
    if fonte == "regularize":
        csv_data = db.exportar_regularize_csv(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim)
        filename = "regularize.csv"
    else:
        csv_data = db.exportar_ecac_csv(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim)
        filename = "ecac.csv"
    return Response(
        content=csv_data.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
