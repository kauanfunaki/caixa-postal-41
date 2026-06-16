from pathlib import Path
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/configuracoes")
def configuracoes(request: Request, msg: str = "", erro: str = ""):
    return templates.TemplateResponse(request, "configuracoes.html", {
        "cnpjs": db.listar_cnpjs(), "msg": msg, "erro": erro,
    })


@router.post("/configuracoes/adicionar")
def adicionar(cnpj: str = Form(...), razao_social: str = Form("")):
    import re
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14:
        return RedirectResponse(f"/configuracoes?erro=CNPJ+inválido:+{cnpj}", status_code=303)
    try:
        db.criar_cnpj(digits, razao_social)
        return RedirectResponse(f"/configuracoes?msg=CNPJ+adicionado+com+sucesso", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/configuracoes?erro={str(e)}", status_code=303)


@router.post("/configuracoes/{cnpj}/editar")
def editar(cnpj: str, razao_social: str = Form(...)):
    db.atualizar_cnpj(cnpj, razao_social=razao_social)
    return RedirectResponse("/configuracoes?msg=Razão+social+atualizada", status_code=303)


@router.post("/configuracoes/{cnpj}/toggle")
def toggle(cnpj: str, ativo: str = Form(...)):
    db.atualizar_cnpj(cnpj, ativo=(ativo == "1"))
    return RedirectResponse("/configuracoes", status_code=303)


@router.post("/configuracoes/{cnpj}/deletar")
def deletar(cnpj: str):
    db.deletar_cnpj(cnpj)
    return RedirectResponse("/configuracoes?msg=CNPJ+removido", status_code=303)


@router.post("/configuracoes/importar")
async def importar(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    importados, erros = db.importar_cnpjs_excel(conteudo)
    if erros and importados == 0:
        return RedirectResponse(f"/configuracoes?erro={'%0A'.join(erros[:3])}", status_code=303)
    msg = f"{importados}+CNPJ(s)+importados"
    if erros:
        msg += f"+({len(erros)}+ignorados)"
    return RedirectResponse(f"/configuracoes?msg={msg}", status_code=303)
