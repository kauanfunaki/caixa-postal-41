"""Queries MySQL para o Caixa Postal 41."""

from __future__ import annotations

import csv
import io
import re
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
import yaml

_ROOT = Path(__file__).parent.parent


def _full_cfg() -> dict:
    cfg_file = _ROOT / "config.yaml"
    base = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) if cfg_file.exists() else {}
    return base

def _cfg() -> dict:
    cfg = _full_cfg().get("database", {})
    # Env vars override config.yaml (útil no Docker/EasyPanel)
    env_map = {"host": "DB_HOST", "port": "DB_PORT", "user": "DB_USER",
               "password": "DB_PASSWORD", "database": "DB_NAME"}
    for key, env in env_map.items():
        val = os.environ.get(env)
        if val:
            cfg[key] = val
    return cfg

def email_cfg() -> dict:
    return _full_cfg().get("email", {})


def get_conn():
    cfg = _cfg()
    return mysql.connector.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        autocommit=False,
        connection_timeout=10,
    )


def _fmt_cnpj(cnpj: str) -> str:
    c = cnpj.zfill(14)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def inicializar_tabelas_notificacao() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notif_destinatarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(200) NOT NULL DEFAULT '',
            email VARCHAR(300) NOT NULL,
            ativo TINYINT(1) DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notif_log (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            tipo VARCHAR(20) NOT NULL,
            mensagem_id BIGINT NOT NULL,
            enviado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_tipo_msg (tipo, mensagem_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    cur.close(); conn.close()


# ---------------------------------------------------------------------------
# CNPJs
# ---------------------------------------------------------------------------

def listar_cnpjs() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT cnpj, razao_social, ativo, atualizado_em FROM cnpjs ORDER BY razao_social, cnpj")
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        r["cnpj_fmt"] = _fmt_cnpj(r["cnpj"])
    return rows


def criar_cnpj(cnpj: str, razao_social: str) -> None:
    digits = re.sub(r"\D", "", cnpj).zfill(14)[:14]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO cnpjs (cnpj, razao_social, ativo) VALUES (%s, %s, 1)
           ON DUPLICATE KEY UPDATE
             razao_social = IF(%s != '', VALUES(razao_social), razao_social),
             ativo = 1""",
        (digits, razao_social.strip(), razao_social.strip()),
    )
    conn.commit(); cur.close(); conn.close()


def atualizar_cnpj(cnpj: str, razao_social: Optional[str] = None, ativo: Optional[bool] = None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if razao_social is not None:
        cur.execute("UPDATE cnpjs SET razao_social=%s WHERE cnpj=%s", (razao_social.strip(), cnpj))
    if ativo is not None:
        cur.execute("UPDATE cnpjs SET ativo=%s WHERE cnpj=%s", (1 if ativo else 0, cnpj))
    conn.commit(); cur.close(); conn.close()


def deletar_cnpj(cnpj: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM cnpjs WHERE cnpj=%s", (cnpj,))
    conn.commit(); cur.close(); conn.close()


def importar_cnpjs_excel(conteudo: bytes) -> Tuple[int, List[str]]:
    import pandas as pd
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(conteudo)
        tmp_path = tmp.name
    erros: List[str] = []
    importados = 0
    try:
        df = pd.read_excel(tmp_path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
        col_cnpj = next((c for c in df.columns if "cnpj" in c), None)
        if col_cnpj is None:
            return 0, ["Coluna 'cnpj' não encontrada na planilha."]
        col_rs = next((c for c in df.columns if any(k in c for k in ["razao", "empresa", "nome"])), None)
        for _, row in df.iterrows():
            raw = str(row[col_cnpj]) if not (isinstance(row[col_cnpj], float) and str(row[col_cnpj]) == 'nan') else ""
            digits = re.sub(r"\D", "", raw)
            if len(digits) != 14:
                erros.append(f"CNPJ inválido ignorado: '{raw}'")
                continue
            rs = str(row[col_rs]).strip() if col_rs and str(row.get(col_rs, "nan")) != "nan" else ""
            try:
                criar_cnpj(digits, rs)
                importados += 1
            except Exception as e:
                erros.append(f"Erro ao importar {digits}: {e}")
    finally:
        os.unlink(tmp_path)
    return importados, erros


# ---------------------------------------------------------------------------
# Caixa Postal — e-CAC
# ---------------------------------------------------------------------------

def listar_mensagens_ecac(
    cnpj: str = "", q: str = "", data_ini: str = "", data_fim: str = "",
    page: int = 1, per_page: int = 20,
) -> Dict:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    where = ["1=1"]
    params: List[Any] = []
    if cnpj:
        where.append("e.cnpj = %s"); params.append(cnpj)
    if q:
        where.append("(e.assunto LIKE %s OR e.remetente LIKE %s OR c.razao_social LIKE %s)")
        like = f"%{q}%"; params += [like, like, like]
    if data_ini:
        where.append("e.data_envio >= %s"); params.append(data_ini)
    if data_fim:
        where.append("e.data_envio <= %s"); params.append(data_fim)
    w = " AND ".join(where)
    offset = (page - 1) * per_page
    cur.execute(f"SELECT COUNT(*) AS total FROM ecac_mensagens e LEFT JOIN cnpjs c ON c.cnpj=e.cnpj WHERE {w}", params)
    total = cur.fetchone()["total"]
    cur.execute(
        f"""SELECT e.id, e.cnpj, c.razao_social, e.remetente, e.assunto,
                   e.data_envio, e.tipo_comunicacao, e.extraido_em
            FROM ecac_mensagens e LEFT JOIN cnpjs c ON c.cnpj=e.cnpj
            WHERE {w} ORDER BY e.data_envio DESC, e.id DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset],
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        r["cnpj_fmt"] = _fmt_cnpj(r["cnpj"])
    return {"rows": rows, "total": total, "page": page, "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page)}


def exportar_ecac_csv(cnpj="", q="", data_ini="", data_fim="") -> str:
    data = listar_mensagens_ecac(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim, page=1, per_page=99999)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["CNPJ", "Razão Social", "Remetente", "Assunto", "Data Envio", "Tipo"])
    for r in data["rows"]:
        w.writerow([r["cnpj_fmt"], r.get("razao_social",""), r["remetente"], r["assunto"], r["data_envio"], r["tipo_comunicacao"]])
    return out.getvalue()


# ---------------------------------------------------------------------------
# Caixa Postal — Regularize
# ---------------------------------------------------------------------------

def listar_mensagens_regularize(
    cnpj: str = "", q: str = "", data_ini: str = "", data_fim: str = "",
    page: int = 1, per_page: int = 20,
) -> Dict:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    where = ["1=1"]
    params: List[Any] = []
    if cnpj:
        where.append("p.cnpj = %s"); params.append(cnpj)
    if q:
        where.append("(p.assunto LIKE %s OR c.razao_social LIKE %s)")
        like = f"%{q}%"; params += [like, like]
    if data_ini:
        where.append("p.data_mensagem >= %s"); params.append(data_ini)
    if data_fim:
        where.append("DATE(p.data_mensagem) <= %s"); params.append(data_fim)
    w = " AND ".join(where)
    offset = (page - 1) * per_page
    cur.execute(f"SELECT COUNT(*) AS total FROM pgfn_mensagens p LEFT JOIN cnpjs c ON c.cnpj=p.cnpj WHERE {w}", params)
    total = cur.fetchone()["total"]
    cur.execute(
        f"""SELECT p.id, p.cnpj, c.razao_social, p.data_mensagem, p.assunto
            FROM pgfn_mensagens p LEFT JOIN cnpjs c ON c.cnpj=p.cnpj
            WHERE {w} ORDER BY p.data_mensagem DESC, p.id DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset],
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        r["cnpj_fmt"] = _fmt_cnpj(r["cnpj"])
    return {"rows": rows, "total": total, "page": page, "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page)}


def exportar_regularize_csv(cnpj="", q="", data_ini="", data_fim="") -> str:
    data = listar_mensagens_regularize(cnpj=cnpj, q=q, data_ini=data_ini, data_fim=data_fim, page=1, per_page=99999)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["CNPJ", "Razão Social", "Data Mensagem", "Assunto"])
    for r in data["rows"]:
        w.writerow([r["cnpj_fmt"], r.get("razao_social",""), r["data_mensagem"], r["assunto"]])
    return out.getvalue()


# ---------------------------------------------------------------------------
# Execuções
# ---------------------------------------------------------------------------

def listar_execucoes(page: int = 1, per_page: int = 30) -> Dict:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS total FROM execucoes")
    total = cur.fetchone()["total"]
    offset = (page - 1) * per_page
    cur.execute(
        "SELECT id, inicio, fim, status, cnpjs_processados, observacoes "
        "FROM execucoes ORDER BY inicio DESC LIMIT %s OFFSET %s",
        (per_page, offset),
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        if r["inicio"] and r["fim"]:
            s = int((r["fim"] - r["inicio"]).total_seconds())
            r["duracao"] = f"{s // 60}m {s % 60}s"
        else:
            r["duracao"] = "—"
    return {"rows": rows, "total": total, "page": page, "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page)}


# ---------------------------------------------------------------------------
# Notificações — destinatários
# ---------------------------------------------------------------------------

def listar_destinatarios() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nome, email, ativo, criado_em FROM notif_destinatarios ORDER BY nome, email")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def criar_destinatario(nome: str, email: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notif_destinatarios (nome, email) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE nome=VALUES(nome), ativo=1",
        (nome.strip(), email.strip().lower()),
    )
    conn.commit(); cur.close(); conn.close()


def toggle_destinatario(dest_id: int, ativo: bool) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE notif_destinatarios SET ativo=%s WHERE id=%s", (1 if ativo else 0, dest_id))
    conn.commit(); cur.close(); conn.close()


def deletar_destinatario(dest_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM notif_destinatarios WHERE id=%s", (dest_id,))
    conn.commit(); cur.close(); conn.close()


# ---------------------------------------------------------------------------
# Notificações — verificar novidades
# ---------------------------------------------------------------------------

def buscar_mensagens_novas_ecac() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT e.id, e.cnpj, c.razao_social, e.remetente, e.assunto, e.data_envio, e.tipo_comunicacao
        FROM ecac_mensagens e
        LEFT JOIN cnpjs c ON c.cnpj = e.cnpj
        WHERE e.id NOT IN (SELECT mensagem_id FROM notif_log WHERE tipo = 'ecac')
        ORDER BY e.data_envio DESC, e.id DESC
        LIMIT 200
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        r["cnpj_fmt"] = _fmt_cnpj(r["cnpj"])
    return rows


def buscar_mensagens_novas_regularize() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, p.cnpj, c.razao_social, p.data_mensagem, p.assunto
        FROM pgfn_mensagens p
        LEFT JOIN cnpjs c ON c.cnpj = p.cnpj
        WHERE p.id NOT IN (SELECT mensagem_id FROM notif_log WHERE tipo = 'regularize')
        ORDER BY p.data_mensagem DESC, p.id DESC
        LIMIT 200
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    for r in rows:
        r["cnpj_fmt"] = _fmt_cnpj(r["cnpj"])
    return rows


def registrar_notificacoes(ids_ecac: List[int], ids_regularize: List[int]) -> None:
    if not ids_ecac and not ids_regularize:
        return
    conn = get_conn()
    cur = conn.cursor()
    for mid in ids_ecac:
        cur.execute("INSERT IGNORE INTO notif_log (tipo, mensagem_id) VALUES ('ecac', %s)", (mid,))
    for mid in ids_regularize:
        cur.execute("INSERT IGNORE INTO notif_log (tipo, mensagem_id) VALUES ('regularize', %s)", (mid,))
    conn.commit(); cur.close(); conn.close()


def ultima_verificacao() -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(enviado_em) FROM notif_log")
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and row[0]:
        return row[0].strftime("%d/%m/%Y %H:%M")
    return None


def contagem_pendentes() -> Dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ecac_mensagens WHERE id NOT IN (SELECT mensagem_id FROM notif_log WHERE tipo='ecac')")
    ecac = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pgfn_mensagens WHERE id NOT IN (SELECT mensagem_id FROM notif_log WHERE tipo='regularize')")
    regularize = cur.fetchone()[0]
    cur.close(); conn.close()
    return {"ecac": ecac, "regularize": regularize}
