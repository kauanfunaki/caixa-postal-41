"""Envio de e-mail via SMTP para notificações de novas mensagens."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List

import yaml

_ROOT = Path(__file__).parent.parent


def _cfg() -> dict:
    import os
    cfg_file = _ROOT / "config.yaml"
    cfg = (yaml.safe_load(cfg_file.read_text(encoding="utf-8")).get("email", {})
           if cfg_file.exists() else {})
    # Env vars override config.yaml (útil no Docker/EasyPanel)
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


def _html_tabela_ecac(mensagens: List[Dict]) -> str:
    if not mensagens:
        return ""
    linhas = ""
    for m in mensagens:
        data = m["data_envio"].strftime("%d/%m/%Y") if m.get("data_envio") else "—"
        linhas += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-family:monospace;font-size:12px;color:#4B5563;">{m['cnpj_fmt']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#111827;">{m.get('razao_social') or '—'}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#374151;">{m.get('remetente') or '—'}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#111827;">{m.get('assunto') or '—'}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:12px;color:#6B7280;white-space:nowrap;">{data}</td>
        </tr>"""
    return f"""
    <h3 style="font-size:14px;font-weight:600;color:#1F2937;margin:24px 0 8px;padding-left:12px;border-left:3px solid #3A7BD5;">
      e-CAC — Caixa Postal ({len(mensagens)} nova{'s' if len(mensagens) != 1 else ''})
    </h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #E5E7EB;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#F9FAFB;">
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">CNPJ</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Empresa</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Remetente</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Assunto</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Data</th>
        </tr>
      </thead>
      <tbody>{linhas}</tbody>
    </table>"""


def _html_tabela_regularize(mensagens: List[Dict]) -> str:
    if not mensagens:
        return ""
    linhas = ""
    for m in mensagens:
        data = m["data_mensagem"].strftime("%d/%m/%Y %H:%M") if m.get("data_mensagem") else "—"
        linhas += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-family:monospace;font-size:12px;color:#4B5563;">{m['cnpj_fmt']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#111827;">{m.get('razao_social') or '—'}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:12px;color:#6B7280;white-space:nowrap;">{data}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#111827;">{m.get('assunto') or '—'}</td>
        </tr>"""
    return f"""
    <h3 style="font-size:14px;font-weight:600;color:#1F2937;margin:24px 0 8px;padding-left:12px;border-left:3px solid #3A7BD5;">
      Regularize PGFN ({len(mensagens)} nova{'s' if len(mensagens) != 1 else ''})
    </h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #E5E7EB;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#F9FAFB;">
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">CNPJ</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Empresa</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Data</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;">Assunto</th>
        </tr>
      </thead>
      <tbody>{linhas}</tbody>
    </table>"""


def montar_html(ecac: List[Dict], regularize: List[Dict]) -> str:
    total = len(ecac) + len(regularize)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="padding:32px 16px;">
      <table width="640" cellpadding="0" cellspacing="0" style="margin:0 auto;max-width:640px;">

        <!-- Header -->
        <tr>
          <td style="background:#0F172A;padding:24px 32px;border-radius:12px 12px 0 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="display:inline-flex;align-items:center;gap:10px;">
                    <div style="width:32px;height:32px;background:#3A7BD5;border-radius:6px;display:inline-block;text-align:center;line-height:32px;font-weight:800;font-size:13px;color:#fff;">41</div>
                    <span style="color:#F1F5F9;font-size:16px;font-weight:700;letter-spacing:-.01em;">Caixa Postal 41</span>
                  </div>
                </td>
                <td style="text-align:right;">
                  <span style="background:#3A7BD5;color:#fff;font-size:11px;font-weight:600;padding:4px 10px;border-radius:20px;">
                    {total} nova{'s' if total != 1 else ''} mensagem{'ns' if total != 1 else ''}
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#FFFFFF;padding:32px;border-left:1px solid #E5E7EB;border-right:1px solid #E5E7EB;">
            <p style="margin:0 0 4px;font-size:20px;font-weight:700;color:#111827;">
              Novas mensagens detectadas
            </p>
            <p style="margin:0 0 24px;font-size:14px;color:#6B7280;">
              {len(ecac)} mensagem{'ns' if len(ecac) != 1 else ''} no e-CAC
              &nbsp;·&nbsp;
              {len(regularize)} mensagem{'ns' if len(regularize) != 1 else ''} no Regularize
            </p>
            {_html_tabela_ecac(ecac)}
            {_html_tabela_regularize(regularize)}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F9FAFB;padding:20px 32px;border-radius:0 0 12px 12px;border:1px solid #E5E7EB;border-top:none;">
            <p style="margin:0;font-size:12px;color:#9CA3AF;text-align:center;">
              Enviado automaticamente pelo Caixa Postal 41 &mdash; 41 Tech Contabilidade
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def enviar_notificacao(destinatarios: List[Dict], ecac: List[Dict], regularize: List[Dict]) -> Tuple[int, str]:
    """Envia e-mail de notificação. Retorna (qtd_enviados, erro_msg)."""
    from typing import Tuple
    cfg = _cfg()
    if not cfg.get("smtp_user") or not cfg.get("remetente_email"):
        return 0, "SMTP não configurado. Preencha config.yaml."

    total = len(ecac) + len(regularize)
    if total == 0:
        return 0, ""

    ativos = [d for d in destinatarios if d.get("ativo")]
    if not ativos:
        return 0, "Nenhum destinatário ativo."

    remetente = f"{cfg['remetente_nome']} <{cfg['remetente_email']}>"
    assunto = f"Caixa Postal 41 — {total} nova{'s' if total != 1 else ''} mensagem{'ns' if total != 1 else ''} detectada{'s' if total != 1 else ''}"
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
            msg["From"] = remetente
            msg["To"] = f"{dest['nome']} <{dest['email']}>" if dest.get("nome") else dest["email"]
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(cfg["remetente_email"], dest["email"], msg.as_string())
            enviados += 1

        server.quit()
        return enviados, ""
    except Exception as e:
        return 0, str(e)
