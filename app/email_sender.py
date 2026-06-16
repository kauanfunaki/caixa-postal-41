"""Envio de e-mail via SMTP para notificações de novas mensagens."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

_ROOT = Path(__file__).parent.parent

# ── Paleta ──────────────────────────────────────────────────────────────────
_NAVY   = "#0D1117"
_BLUE   = "#3A7BD5"
_BLUE_L = "#EBF2FF"
_WHITE  = "#FFFFFF"
_GRAY_1 = "#111827"
_GRAY_2 = "#374151"
_GRAY_3 = "#6B7280"
_GRAY_4 = "#9CA3AF"
_BORDER = "#E5E7EB"
_ROW_ODD= "#F9FAFB"


def _cfg() -> dict:
    import os
    cfg_file = _ROOT / "config.yaml"
    cfg = (yaml.safe_load(cfg_file.read_text(encoding="utf-8")).get("email", {})
           if cfg_file.exists() else {})
    env_map = {
        "smtp_host": "SMTP_HOST", "smtp_port": "SMTP_PORT",
        "smtp_user": "SMTP_USER", "smtp_password": "SMTP_PASSWORD",
        "use_tls": "SMTP_TLS",
        "remetente_email": "SMTP_FROM_EMAIL", "remetente_nome": "SMTP_FROM_NAME",
    }
    for key, env in env_map.items():
        val = os.environ.get(env)
        if val:
            cfg[key] = val
    return cfg


def smtp_configurado() -> bool:
    cfg = _cfg()
    return bool(cfg.get("smtp_user") and cfg.get("smtp_password") and cfg.get("remetente_email"))


# ── Helpers ─────────────────────────────────────────────────────────────────

def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural

def _th(label: str) -> str:
    return (f'<th style="padding:9px 14px;text-align:left;font-family:Arial,sans-serif;'
            f'font-size:10px;font-weight:700;color:{_GRAY_3};text-transform:uppercase;'
            f'letter-spacing:.06em;background:{_ROW_ODD};border-bottom:1px solid {_BORDER};">'
            f'{label}</th>')

def _td(content: str, mono: bool = False, muted: bool = False) -> str:
    color  = _GRAY_3 if muted else _GRAY_1
    family = "Courier New, monospace" if mono else "Arial,sans-serif"
    size   = "11px" if mono else "13px"
    return (f'<td style="padding:10px 14px;font-family:{family};font-size:{size};'
            f'color:{color};border-bottom:1px solid {_BORDER};vertical-align:top;">'
            f'{content}</td>')


# ── Tabelas ──────────────────────────────────────────────────────────────────

def _tabela_ecac(msgs: List[Dict]) -> str:
    if not msgs:
        return ""
    n = len(msgs)
    linhas = ""
    for i, m in enumerate(msgs):
        data = m["data_envio"].strftime("%d/%m/%Y") if m.get("data_envio") else "—"
        bg = f' style="background:{_ROW_ODD};"' if i % 2 == 0 else ""
        linhas += (f"<tr{bg}>"
                   + _td(m["cnpj_fmt"], mono=True)
                   + _td(m.get("razao_social") or "—")
                   + _td(m.get("remetente") or "—", muted=True)
                   + _td(m.get("assunto") or "—")
                   + _td(data, muted=True)
                   + "</tr>")

    return f"""
    <!-- Seção e-CAC -->
    <tr><td style="padding:24px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding-bottom:12px;border-bottom:2px solid {_BLUE};">
            <span style="font-family:Arial,sans-serif;font-size:13px;font-weight:700;
                         color:{_GRAY_1};letter-spacing:-.01em;">
              &#9993;&nbsp; e-CAC — Caixa Postal
            </span>
            <span style="margin-left:8px;background:{_BLUE_L};color:{_BLUE};
                         font-family:Arial,sans-serif;font-size:11px;font-weight:700;
                         padding:2px 8px;border-radius:10px;">
              {n} {_plural(n, 'nova', 'novas')}
            </span>
          </td>
        </tr>
      </table>
    </td></tr>
    <tr><td style="padding:12px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:1px solid {_BORDER};">
        <thead>
          <tr>{_th("CNPJ")}{_th("Empresa")}{_th("Remetente")}{_th("Assunto")}{_th("Data")}</tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
    </td></tr>"""


def _tabela_regularize(msgs: List[Dict]) -> str:
    if not msgs:
        return ""
    n = len(msgs)
    linhas = ""
    for i, m in enumerate(msgs):
        data = m["data_mensagem"].strftime("%d/%m/%Y %H:%M") if m.get("data_mensagem") else "—"
        bg = f' style="background:{_ROW_ODD};"' if i % 2 == 0 else ""
        linhas += (f"<tr{bg}>"
                   + _td(m["cnpj_fmt"], mono=True)
                   + _td(m.get("razao_social") or "—")
                   + _td(data, muted=True)
                   + _td(m.get("assunto") or "—")
                   + "</tr>")

    return f"""
    <!-- Seção Regularize -->
    <tr><td style="padding:28px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding-bottom:12px;border-bottom:2px solid {_BLUE};">
            <span style="font-family:Arial,sans-serif;font-size:13px;font-weight:700;
                         color:{_GRAY_1};letter-spacing:-.01em;">
              &#10003;&nbsp; Regularize PGFN
            </span>
            <span style="margin-left:8px;background:{_BLUE_L};color:{_BLUE};
                         font-family:Arial,sans-serif;font-size:11px;font-weight:700;
                         padding:2px 8px;border-radius:10px;">
              {n} {_plural(n, 'nova', 'novas')}
            </span>
          </td>
        </tr>
      </table>
    </td></tr>
    <tr><td style="padding:12px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:1px solid {_BORDER};">
        <thead>
          <tr>{_th("CNPJ")}{_th("Empresa")}{_th("Data")}{_th("Assunto")}</tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
    </td></tr>"""


# ── Montagem do e-mail ───────────────────────────────────────────────────────

def montar_html(ecac: List[Dict], regularize: List[Dict]) -> str:
    total = len(ecac) + len(regularize)
    n_ecac, n_reg = len(ecac), len(regularize)

    stat_ecac = f"""
      <td width="50%" style="padding:0 6px 0 0;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:{_BLUE_L};border-radius:8px;">
          <tr>
            <td style="padding:14px 18px;">
              <div style="font-family:Arial,sans-serif;font-size:22px;font-weight:700;
                          color:{_BLUE};line-height:1;">{n_ecac}</div>
              <div style="font-family:Arial,sans-serif;font-size:11px;color:{_BLUE};
                          margin-top:3px;font-weight:600;">
                {_plural(n_ecac, 'mensagem', 'mensagens')} no e-CAC
              </div>
            </td>
          </tr>
        </table>
      </td>""" if n_ecac else ""

    stat_reg = f"""
      <td width="50%" style="padding:0 0 0 6px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:{_BLUE_L};border-radius:8px;">
          <tr>
            <td style="padding:14px 18px;">
              <div style="font-family:Arial,sans-serif;font-size:22px;font-weight:700;
                          color:{_BLUE};line-height:1;">{n_reg}</div>
              <div style="font-family:Arial,sans-serif;font-size:11px;color:{_BLUE};
                          margin-top:3px;font-weight:600;">
                {_plural(n_reg, 'mensagem', 'mensagens')} no Regularize
              </div>
            </td>
          </tr>
        </table>
      </td>""" if n_reg else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>Caixa Postal 41</title>
</head>
<body style="margin:0;padding:0;background:#F0F2F5;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation">
<tr><td style="padding:32px 16px;">

  <!-- Container -->
  <table width="620" cellpadding="0" cellspacing="0" role="presentation"
         style="margin:0 auto;max-width:620px;">

    <!-- ── Header ── -->
    <tr>
      <td style="background:{_NAVY};border-radius:12px 12px 0 0;padding:0;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>
            <td style="padding:24px 32px 20px;">
              <!-- Logo row -->
              <table cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="vertical-align:middle;">
                    <div style="width:36px;height:36px;background:{_BLUE};border-radius:8px;
                                display:inline-block;text-align:center;line-height:36px;
                                font-family:Arial,sans-serif;font-size:14px;font-weight:900;
                                color:#fff;letter-spacing:-.02em;">41</div>
                  </td>
                  <td style="padding-left:10px;vertical-align:middle;">
                    <div style="font-family:Arial,sans-serif;font-size:15px;font-weight:700;
                                color:#E8EAF0;letter-spacing:-.01em;line-height:1.2;">
                      Caixa Postal 41
                    </div>
                    <div style="font-family:Arial,sans-serif;font-size:11px;font-weight:600;
                                color:{_BLUE};letter-spacing:.04em;margin-top:1px;">
                      41 TECH CONTABILIDADE
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Linha divisória azul -->
          <tr>
            <td style="background:{_BLUE};height:3px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>
          <!-- Subtítulo no header -->
          <tr>
            <td style="padding:16px 32px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td>
                    <div style="font-family:Arial,sans-serif;font-size:18px;font-weight:700;
                                color:#FFFFFF;line-height:1.2;">
                      Novas mensagens detectadas
                    </div>
                    <div style="font-family:Arial,sans-serif;font-size:13px;color:#8892AA;
                                margin-top:4px;">
                      {total} {_plural(total, 'mensagem nova', 'mensagens novas')} encontrada{'s' if total != 1 else ''}
                    </div>
                  </td>
                  <td style="text-align:right;vertical-align:middle;">
                    <div style="display:inline-block;background:{_BLUE};color:#fff;
                                font-family:Arial,sans-serif;font-size:22px;font-weight:900;
                                padding:8px 18px;border-radius:10px;line-height:1;">
                      {total}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- ── Stats bar ── -->
    <tr>
      <td style="background:{_WHITE};padding:20px 32px;border-left:1px solid {_BORDER};
                 border-right:1px solid {_BORDER};">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>{stat_ecac}{stat_reg}</tr>
        </table>
      </td>
    </tr>

    <!-- ── Tabelas ── -->
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
           style="background:{_WHITE};border-left:1px solid {_BORDER};
                  border-right:1px solid {_BORDER};">
      {_tabela_ecac(ecac)}
      {_tabela_regularize(regularize)}
      <tr><td style="height:28px;font-size:0;">&nbsp;</td></tr>
    </table>

    <!-- ── Footer ── -->
    <tr>
      <td style="background:#F9FAFB;padding:18px 32px;border-radius:0 0 12px 12px;
                 border:1px solid {_BORDER};border-top:none;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>
            <td style="border-top:1px solid {_BORDER};padding-top:16px;">
              <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;
                        color:{_GRAY_4};text-align:center;line-height:1.6;">
                Enviado automaticamente pelo <strong style="color:{_GRAY_3};">Caixa Postal 41</strong>
                &nbsp;&mdash;&nbsp; 41 Tech Contabilidade<br>
                Para cancelar notificações, acesse o painel e desative seu e-mail.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

  </table>
</td></tr>
</table>
</body>
</html>"""


# ── Envio ────────────────────────────────────────────────────────────────────

def enviar_notificacao(destinatarios: List[Dict], ecac: List[Dict], regularize: List[Dict]) -> Tuple[int, str]:
    """Envia e-mail de notificação. Retorna (qtd_enviados, erro_msg)."""
    cfg = _cfg()
    if not cfg.get("smtp_user") or not cfg.get("remetente_email"):
        return 0, "SMTP não configurado. Preencha config.yaml."

    total = len(ecac) + len(regularize)
    if total == 0:
        return 0, ""

    ativos = [d for d in destinatarios if d.get("ativo")]
    if not ativos:
        return 0, "Nenhum destinatário ativo."

    remetente = f"{cfg.get('remetente_nome', 'Caixa Postal 41')} <{cfg['remetente_email']}>"
    assunto   = (f"Caixa Postal 41 — {total} "
                 f"{_plural(total, 'nova mensagem', 'novas mensagens')} detectada{'s' if total != 1 else ''}")
    html = montar_html(ecac, regularize)

    try:
        server = smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=15)
        if cfg.get("use_tls", True):
            server.starttls()
        server.login(cfg["smtp_user"], cfg["smtp_password"])

        enviados = 0
        for dest in ativos:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = assunto
            msg["From"]    = remetente
            msg["To"]      = (f"{dest['nome']} <{dest['email']}>"
                               if dest.get("nome") else dest["email"])
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(cfg["remetente_email"], dest["email"], msg.as_string())
            enviados += 1

        server.quit()
        return enviados, ""
    except Exception as e:
        return 0, str(e)
