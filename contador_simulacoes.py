"""Contador global PostgreSQL, com SQLite opcional para desenvolvimento."""

import os
from contextlib import closing
import sqlite3
from pathlib import Path


def atualizar_contador(incrementar=False, database_url=None):
    database_url = database_url or os.environ.get("SIMULACOES_DATABASE_URL")
    if database_url:
        import psycopg

        with psycopg.connect(database_url, connect_timeout=10, options="-c statement_timeout=10000") as conexao:
            if incrementar:
                return conexao.execute(
                    "UPDATE public.contador_simulacoes SET total = total + 1 "
                    "WHERE id = 1 RETURNING total"
                ).fetchone()[0]
            return conexao.execute(
                "SELECT total FROM public.contador_simulacoes WHERE id = 1"
            ).fetchone()[0]
    # SQLite é opt-in para desenvolvimento; nunca substitui um banco remoto em falha.
    caminho_local = os.environ.get("SIMULACOES_DB_PATH")
    if not caminho_local:
        return None
    caminho = Path(caminho_local)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(caminho, timeout=30)) as conexao, conexao:
        conexao.execute(
            "CREATE TABLE IF NOT EXISTS contador "
            "(id INTEGER PRIMARY KEY CHECK (id = 1), total INTEGER NOT NULL DEFAULT 0)"
        )
        conexao.execute("INSERT OR IGNORE INTO contador (id, total) VALUES (1, 0)")
        if incrementar:
            conexao.execute("UPDATE contador SET total = total + 1 WHERE id = 1")
        return conexao.execute("SELECT total FROM contador WHERE id = 1").fetchone()[0]
