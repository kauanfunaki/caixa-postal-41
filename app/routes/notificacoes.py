from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db, email_sender

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/notificacoes")
def notificacoes(request: Request, msg: str = "", erro: str = ""):
    return templates.TemplateResponse(request, "notificacoes.html", {
        "destinatarios": db.listar_destinatarios(),
        "ultima_verificacao": db.ultima_verificacao(),
        "pendentes": db.contagem_pendentes(),
        "smtp_ok": email_sender.smtp_configurado(),
        "msg": msg,
        "erro": erro,
    })


@router.post("/notificacoes/adicionar")
def adicionar(nome: str = Form(""), email: str = Form(...)):
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return RedirectResponse("/notificacoes?erro=E-mail+inválido", status_code=303)
    try:
        db.criar_destinatario(nome, email)
        return RedirectResponse("/notificacoes?msg=Destinatário+adicionado", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/notificacoes?erro={str(e)}", status_code=303)


@router.post("/notificacoes/{dest_id}/toggle")
def toggle(dest_id: int, ativo: str = Form(...)):
    db.toggle_destinatario(dest_id, ativo == "1")
    return RedirectResponse("/notificacoes", status_code=303)


@router.post("/notificacoes/{dest_id}/deletar")
def deletar(dest_id: int):
    db.deletar_destinatario(dest_id)
    return RedirectResponse("/notificacoes?msg=Destinatário+removido", status_code=303)


@router.post("/notificacoes/verificar")
def verificar():
    """Verifica novidades e envia e-mails. Retorna JSON para o frontend."""
    ecac = db.buscar_mensagens_novas_ecac()
    regularize = db.buscar_mensagens_novas_regularize()
    total_novas = len(ecac) + len(regularize)

    if total_novas == 0:
        return JSONResponse({"ok": True, "enviados": 0, "total_novas": 0,
                             "msg": "Nenhuma novidade desde a última verificação."})

    destinatarios = db.listar_destinatarios()
    enviados, erro = email_sender.enviar_notificacao(destinatarios, ecac, regularize)

    if erro:
        return JSONResponse({"ok": False, "erro": erro, "total_novas": total_novas})

    # Registrar no log somente após envio bem-sucedido
    db.registrar_notificacoes([r["id"] for r in ecac], [r["id"] for r in regularize])

    msg = f"{total_novas} mensagem{'ns' if total_novas != 1 else ''} nova{'s' if total_novas != 1 else ''} — e-mail enviado para {enviados} destinatário{'s' if enviados != 1 else ''}."
    return JSONResponse({"ok": True, "enviados": enviados, "total_novas": total_novas, "msg": msg})
