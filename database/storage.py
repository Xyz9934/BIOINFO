from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


DB_PATH = Path(__file__).resolve().parent / "app.db"


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_type TEXT NOT NULL,
                query TEXT NOT NULL,
                result_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                sequence TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                fasta_header TEXT,
                length INTEGER NOT NULL DEFAULT 0,
                gc_content REAL NOT NULL DEFAULT 0,
                molecular_weight REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bookmarked_genes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                gene_id TEXT NOT NULL,
                official_name TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                ncbi_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, gene_id)
            );
            """
        )


def log_search(search_type: str, query: str, result_count: int) -> None:
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO search_history (search_type, query, result_count)
            VALUES (?, ?, ?)
            """,
            (search_type, query, result_count),
        )


def save_sequence_record(label: str, sequence: str, notes: str, analysis: Dict[str, Any]) -> int:
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO saved_sequences (
                label, sequence, notes, fasta_header, length, gc_content, molecular_weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                label,
                sequence,
                notes,
                analysis.get("fasta_header"),
                int(analysis.get("length", 0)),
                float(analysis.get("gc_content", 0)),
                float(analysis.get("molecular_weight", 0)),
            ),
        )
        return int(cursor.lastrowid)


def save_bookmarked_gene(gene: Dict[str, Any]) -> int:
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO bookmarked_genes (
                symbol, gene_id, official_name, summary, ncbi_url
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(gene.get("symbol", "")).strip(),
                str(gene.get("gene_id", "")).strip(),
                str(gene.get("official_name", "")).strip(),
                str(gene.get("summary", "")).strip(),
                str(gene.get("ncbi_url", "")).strip(),
            ),
        )
        row = connection.execute(
            """
            SELECT id FROM bookmarked_genes
            WHERE symbol = ? AND gene_id = ?
            """,
            (str(gene.get("symbol", "")).strip(), str(gene.get("gene_id", "")).strip()),
        ).fetchone()
        return int(row["id"]) if row else 0


def fetch_recent_history(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, search_type, query, result_count, created_at
            FROM search_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_saved_sequences(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, label, sequence, notes, fasta_header, length, gc_content, molecular_weight, created_at
            FROM saved_sequences
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_bookmarked_genes(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, symbol, gene_id, official_name, ncbi_url, created_at
            FROM bookmarked_genes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_saved_sequence_by_id(record_id: int) -> Dict[str, Any] | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, label, sequence, notes, fasta_header, length, gc_content, molecular_weight, created_at
            FROM saved_sequences
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_bookmarked_gene_by_id(record_id: int) -> Dict[str, Any] | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, symbol, gene_id, official_name, summary, ncbi_url, created_at
            FROM bookmarked_genes
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return dict(row) if row else None
