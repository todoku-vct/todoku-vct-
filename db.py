import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "history.db"


def _get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                test_mode TEXT NOT NULL,
                profession TEXT NOT NULL,
                lp_text TEXT NOT NULL,
                persona_count INTEGER NOT NULL,
                main_rate TEXT,
                report_json TEXT,
                personas_json TEXT,
                reactions_json TEXT,
                client_name TEXT DEFAULT ''
            )
        """)
        # 既存DBへのカラム追加（すでにある場合は無視）
        try:
            conn.execute("ALTER TABLE test_history ADD COLUMN client_name TEXT DEFAULT ''")
        except Exception:
            pass


def save_result(
    test_mode: str,
    profession: str,
    lp_text: str,
    persona_count: int,
    main_rate: str,
    report: dict,
    personas: list,
    reactions: list,
    client_name: str = "",
):
    init_db()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO test_history
            (created_at, test_mode, profession, lp_text, persona_count, main_rate,
             report_json, personas_json, reactions_json, client_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                test_mode,
                profession,
                lp_text[:500],
                persona_count,
                main_rate,
                json.dumps(report, ensure_ascii=False),
                json.dumps(personas, ensure_ascii=False),
                json.dumps(reactions, ensure_ascii=False),
                client_name,
            ),
        )


def load_history(limit: int = 50, client_name: str = "") -> list[dict]:
    init_db()
    with _get_conn() as conn:
        if client_name:
            rows = conn.execute(
                "SELECT * FROM test_history WHERE client_name = ? ORDER BY created_at DESC LIMIT ?",
                (client_name, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM test_history ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def load_client_names() -> list[str]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT client_name FROM test_history WHERE client_name != '' ORDER BY client_name"
        ).fetchall()
    return [r["client_name"] for r in rows]


def load_detail(record_id: int) -> dict | None:
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM test_history WHERE id = ?", (record_id,)
        ).fetchone()
    if row:
        r = dict(row)
        r["report"] = json.loads(r["report_json"])
        r["personas"] = json.loads(r["personas_json"])
        r["reactions"] = json.loads(r["reactions_json"])
        return r
    return None


def delete_record(record_id: int):
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM test_history WHERE id = ?", (record_id,))
