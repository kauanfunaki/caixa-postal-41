"""Envio de e-mail via SMTP para notificações de novas mensagens."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

_ROOT   = Path(__file__).parent.parent
_STATIC = Path(__file__).parent / "static" / "logo.png"

# ── Paleta ──────────────────────────────────────────────────────────────────
_NAVY     = "#0D1117"
_NAVY_2   = "#161D2A"
_BLUE     = "#3A7BD5"
_BLUE_D   = "#2E63AC"
_BLUE_L   = "#EBF2FF"
_BLUE_LT  = "#F0F5FF"
_WHITE    = "#FFFFFF"
_BODY_BG  = "#F4F6FA"
_TEXT_1   = "#0D1117"
_TEXT_2   = "#374151"
_TEXT_3   = "#6B7280"
_TEXT_4   = "#9CA3AF"
_BORDER   = "#E2E8F0"
_ROW_ALT  = "#F8FAFC"
_GREEN    = "#059669"
_GREEN_L  = "#D1FAE5"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _plural(n: int, s: str, p: str) -> str:
    return s if n == 1 else p


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


def _logo_b64() -> str:
    """Retorna a logo em base64 para embutir no e-mail."""
    try:
        import base64
        return base64.b64encode(_STATIC.read_bytes()).decode()
    except Exception:
        return ""


# ── Tabelas ──────────────────────────────────────────────────────────────────

def _th(label: str, width: str = "") -> str:
    w = f'width="{width}" ' if width else ""
    return (
        f'<th {w}style="padding:8px 16px;text-align:left;font-family:\'Trebuchet MS\',Arial,sans-serif;'
        f'font-size:9px;font-weight:700;color:{_TEXT_3};text-transform:uppercase;'
        f'letter-spacing:.1em;background:{_ROW_ALT};border-bottom:1px solid {_BORDER};">'
        f'{label}</th>'
    )


def _td_val(content: str, mono: bool = False, muted: bool = False, wrap: bool = False) -> str:
    color  = _TEXT_3 if muted else _TEXT_2
    family = "'Courier New',monospace" if mono else "'Trebuchet MS',Arial,sans-serif"
    size   = "11px" if mono else "13px"
    ws     = "" if wrap else "white-space:nowrap;"
    return (
        f'<td style="padding:11px 16px;font-family:{family};font-size:{size};'
        f'color:{color};border-bottom:1px solid {_BORDER};vertical-align:top;{ws}">'
        f'{content}</td>'
    )


def _section_header(icon: str, title: str, count: int) -> str:
    label = _plural(count, "nova", "novas")
    return f"""
    <tr>
      <td colspan="10" style="padding:28px 32px 0;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding-bottom:10px;border-bottom:2px solid {_BLUE};">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-family:Georgia,serif;font-size:14px;font-weight:700;
                             color:{_TEXT_1};letter-spacing:-.01em;vertical-align:middle;">
                    {icon}&nbsp; {title}
                  </td>
                  <td style="padding-left:10px;vertical-align:middle;">
                    <span style="display:inline-block;background:{_BLUE_L};color:{_BLUE};
                                 font-family:'Trebuchet MS',Arial,sans-serif;
                                 font-size:10px;font-weight:700;letter-spacing:.04em;
                                 padding:3px 9px;border-radius:20px;text-transform:uppercase;">
                      {count} {label}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def _tabela_ecac(msgs: List[Dict]) -> str:
    if not msgs:
        return ""
    linhas = ""
    for i, m in enumerate(msgs):
        data = m["data_envio"].strftime("%d/%m/%Y") if m.get("data_envio") else "—"
        bg = f'background:{_ROW_ALT};' if i % 2 else ""
        linhas += (
            f'<tr style="{bg}">'
            + _td_val(m["cnpj_fmt"], mono=True)
            + _td_val(m.get("razao_social") or "—")
            + _td_val(m.get("remetente") or "—", muted=True)
            + _td_val(m.get("assunto") or "—", wrap=True)
            + _td_val(data, muted=True)
            + "</tr>"
        )
    return f"""
    {_section_header("✉", "e-CAC — Caixa Postal", len(msgs))}
    <tr><td style="padding:10px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:1px solid {_BORDER};border-radius:4px;overflow:hidden;">
        <thead>
          <tr>{_th("CNPJ","140")}{_th("Empresa")}{_th("Remetente","120")}{_th("Assunto")}{_th("Data","88")}</tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
    </td></tr>"""


def _tabela_regularize(msgs: List[Dict]) -> str:
    if not msgs:
        return ""
    linhas = ""
    for i, m in enumerate(msgs):
        data = m["data_mensagem"].strftime("%d/%m/%Y %H:%M") if m.get("data_mensagem") else "—"
        bg = f'background:{_ROW_ALT};' if i % 2 else ""
        linhas += (
            f'<tr style="{bg}">'
            + _td_val(m["cnpj_fmt"], mono=True)
            + _td_val(m.get("razao_social") or "—")
            + _td_val(data, muted=True)
            + _td_val(m.get("assunto") or "—", wrap=True)
            + "</tr>"
        )
    return f"""
    {_section_header("✓", "Regularize PGFN", len(msgs))}
    <tr><td style="padding:10px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:1px solid {_BORDER};border-radius:4px;overflow:hidden;">
        <thead>
          <tr>{_th("CNPJ","140")}{_th("Empresa")}{_th("Data","120")}{_th("Assunto")}</tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
    </td></tr>"""


# ── HTML principal ────────────────────────────────────────────────────────────

def montar_html(ecac: List[Dict], regularize: List[Dict]) -> str:
    total   = len(ecac) + len(regularize)
    n_ecac  = len(ecac)
    n_reg   = len(regularize)
    logo_b64 = _logo_b64()
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    # Cards de contagem
    def _stat_card(n: int, label: str) -> str:
        return f"""
        <td style="padding:0 6px;">
          <table cellpadding="0" cellspacing="0" width="100%"
                 style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;">
            <tr>
              <td style="padding:16px 20px;">
                <div style="font-family:Georgia,serif;font-size:32px;font-weight:700;
                            color:{_BLUE};line-height:1;letter-spacing:-.02em;">{n}</div>
                <div style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;
                            font-weight:600;color:{_TEXT_3};margin-top:5px;
                            text-transform:uppercase;letter-spacing:.06em;">{label}</div>
              </td>
            </tr>
          </table>
        </td>"""

    stats = ""
    if n_ecac:   stats += _stat_card(n_ecac, _plural(n_ecac, "mensagem", "mensagens") + " no e-CAC")
    if n_reg:    stats += _stat_card(n_reg,  _plural(n_reg,  "mensagem", "mensagens") + " no Regularize")

    logo_html = (
        f'<img src="{logo_src}" width="32" height="28" alt="41 Tech" '
        f'style="display:block;border:0;mix-blend-mode:screen;" />'
        if logo_src else
        f'<div style="font-family:Georgia,serif;font-size:14px;font-weight:900;'
        f'color:{_WHITE};">41</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="x-apple-disable-message-reformatting">
  <title>Caixa Postal 41</title>
</head>
<body style="margin:0;padding:0;background:{_BODY_BG};-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<!--[if mso]><table width="100%"><tr><td><![endif]-->
<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
       style="border-collapse:collapse;background:{_BODY_BG};">
<tr><td align="center" style="padding:32px 16px;">

  <table width="640" cellpadding="0" cellspacing="0" role="presentation"
         style="max-width:640px;width:100%;border-collapse:collapse;">

    <!-- ══ HEADER ══ -->
    <tr>
      <td style="background:{_NAVY};border-radius:12px 12px 0 0;padding:0;overflow:hidden;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">

          <!-- Logo bar -->
          <tr>
            <td style="padding:22px 32px 18px;">
              <table cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="vertical-align:middle;">
                    <table cellpadding="0" cellspacing="0" role="presentation">
                      <tr>
                        <td style="background:{_BLUE};border-radius:8px;
                                   width:40px;height:40px;text-align:center;
                                   vertical-align:middle;padding:4px;">
                          {logo_html}
                        </td>
                        <td style="padding-left:12px;vertical-align:middle;">
                          <div style="font-family:Georgia,serif;font-size:16px;
                                      font-weight:700;color:{_WHITE};
                                      letter-spacing:-.02em;line-height:1.1;">
                            Caixa Postal 41
                          </div>
                          <div style="font-family:'Trebuchet MS',Arial,sans-serif;
                                      font-size:10px;font-weight:700;color:{_BLUE};
                                      letter-spacing:.1em;margin-top:3px;
                                      text-transform:uppercase;">
                            41 Tech Contabilidade
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Divider -->
          <tr><td style="height:1px;background:rgba(58,123,213,.35);font-size:0;">&nbsp;</td></tr>

          <!-- Headline -->
          <tr>
            <td style="padding:20px 32px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="vertical-align:middle;">
                    <div style="font-family:Georgia,serif;font-size:22px;font-weight:700;
                                color:{_WHITE};line-height:1.2;letter-spacing:-.02em;">
                      Novas mensagens<br>detectadas
                    </div>
                    <div style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:12px;
                                color:rgba(255,255,255,.45);margin-top:6px;">
                      {total} {_plural(total, "mensagem nova encontrada", "mensagens novas encontradas")}
                    </div>
                  </td>
                  <td style="vertical-align:middle;text-align:right;padding-left:16px;">
                    <div style="display:inline-block;background:{_BLUE};border-radius:10px;
                                padding:10px 20px;text-align:center;">
                      <div style="font-family:Georgia,serif;font-size:40px;font-weight:700;
                                  color:{_WHITE};line-height:1;letter-spacing:-.03em;">{total}</div>
                      <div style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:9px;
                                  color:rgba(255,255,255,.7);text-transform:uppercase;
                                  letter-spacing:.1em;margin-top:4px;">
                        {_plural(total, "mensagem", "mensagens")}
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- ══ STATS CARDS ══ -->
    <tr>
      <td style="background:{_BODY_BG};padding:16px 26px;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>{stats}</tr>
        </table>
      </td>
    </tr>

    <!-- ══ BODY ══ -->
    <tr>
      <td style="background:{_WHITE};border:1px solid {_BORDER};border-top:none;padding-bottom:8px;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          {_tabela_ecac(ecac)}
          {_tabela_regularize(regularize)}
          <tr><td style="height:24px;font-size:0;">&nbsp;</td></tr>
        </table>
      </td>
    </tr>

    <!-- ══ FOOTER ══ -->
    <tr>
      <td style="background:{_NAVY_2};border-radius:0 0 12px 12px;padding:20px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>
            <td>
              <p style="margin:0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;
                        color:rgba(255,255,255,.3);line-height:1.7;">
                Enviado automaticamente pelo
                <span style="color:rgba(255,255,255,.55);font-weight:600;">Caixa Postal 41</span>
                &mdash; 41 Tech Contabilidade.<br>
                Para cancelar notificações, acesse o painel e desative seu e-mail na aba Notificações.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

  </table>
</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""


# ── Envio ────────────────────────────────────────────────────────────────────

def enviar_notificacao(
    destinatarios: List[Dict], ecac: List[Dict], regularize: List[Dict]
) -> Tuple[int, str]:
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
                 f"{_plural(total, 'nova mensagem', 'novas mensagens')} "
                 f"detectada{'s' if total != 1 else ''}")
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
            msg["To"]      = (
                f"{dest['nome']} <{dest['email']}>" if dest.get("nome") else dest["email"]
            )
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(cfg["remetente_email"], dest["email"], msg.as_string())
            enviados += 1

        server.quit()
        return enviados, ""
    except Exception as e:
        return 0, str(e)
