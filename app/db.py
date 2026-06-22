# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = current_app.config["DB_PATH"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        g.db = con
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()



def _column_exists(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _add_column_if_missing(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _column_exists(db, table, column):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_finance_migrations(db: sqlite3.Connection) -> None:
    """Migrações leves do financeiro.

    São seguras para bancos já usados: apenas adiciona colunas/tabelas
    e preenche dados antigos sem apagar nada.
    """
    _add_column_if_missing(db, "transactions", "gross_amount_cents", "INTEGER")
    _add_column_if_missing(db, "transactions", "discount_percent", "REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(db, "transactions", "discount_cents", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(db, "transactions", "final_amount_cents", "INTEGER")
    _add_column_if_missing(db, "transactions", "paid_amount_cents", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(db, "transactions", "balance_cents", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(db, "transactions", "installments_total", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(db, "transactions", "installment_number", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(db, "transactions", "parent_transaction_id", "INTEGER")
    _add_column_if_missing(db, "transactions", "repasse_paid_at", "TEXT")
    _add_column_if_missing(db, "transactions", "repasse_payment_note", "TEXT")

    db.executescript("""
    CREATE TABLE IF NOT EXISTS transaction_payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'pix',
        notes TEXT,
        cash_session_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
        FOREIGN KEY(cash_session_id) REFERENCES cash_sessions(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_txpay_transaction ON transaction_payments(transaction_id);
    CREATE INDEX IF NOT EXISTS idx_txpay_date ON transaction_payments(date);
    CREATE INDEX IF NOT EXISTS idx_txpay_method ON transaction_payments(payment_method);
    """)

    # Compatibilidade com lançamentos antigos: amount_cents continua sendo o valor final.
    db.execute("UPDATE transactions SET gross_amount_cents=amount_cents WHERE gross_amount_cents IS NULL")
    db.execute("UPDATE transactions SET final_amount_cents=amount_cents WHERE final_amount_cents IS NULL")

    # Cria histórico de pagamento para lançamentos antigos pagos, caso ainda não tenham histórico.
    db.execute("""
        INSERT INTO transaction_payments(transaction_id, date, amount_cents, payment_method, notes, cash_session_id)
        SELECT t.id, COALESCE(t.date, date('now')), COALESCE(t.amount_cents, 0), COALESCE(t.payment_method, 'other'),
               'Migração automática', t.cash_session_id
        FROM transactions t
        WHERE t.status='paid'
          AND NOT EXISTS (SELECT 1 FROM transaction_payments p WHERE p.transaction_id=t.id)
    """)

    # Recalcula pago/saldo/status a partir do histórico.
    db.execute("""
        UPDATE transactions
        SET paid_amount_cents = COALESCE((SELECT SUM(p.amount_cents) FROM transaction_payments p WHERE p.transaction_id=transactions.id), 0)
    """)
    db.execute("UPDATE transactions SET balance_cents = MAX(COALESCE(final_amount_cents, amount_cents, 0) - COALESCE(paid_amount_cents, 0), 0)")
    db.execute("UPDATE transactions SET status = CASE WHEN COALESCE(final_amount_cents, amount_cents, 0) > 0 AND paid_amount_cents >= COALESCE(final_amount_cents, amount_cents, 0) THEN 'paid' ELSE 'pending' END")
    db.execute("UPDATE transactions SET amount_cents = COALESCE(final_amount_cents, amount_cents, 0)")


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        birth_date TEXT,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS providers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Dentista',
        default_repasse_percent INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL DEFAULT 'both', -- income|expense|both
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cash_sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opened_at TEXT NOT NULL,
        closed_at TEXT,
        opened_by INTEGER,
        open_balance_cents INTEGER NOT NULL DEFAULT 0,
        close_balance_cents INTEGER,
        expected_balance_cents INTEGER,
        notes TEXT,
        FOREIGN KEY(opened_by) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,            -- income|expense
        status TEXT NOT NULL,          -- paid|pending
        date TEXT NOT NULL,            -- data efetiva (pagamento)
        due_date TEXT,                 -- vencimento (quando pendente)
        amount_cents INTEGER NOT NULL,
        payment_method TEXT NOT NULL,  -- cash|pix|card|transfer|other
        description TEXT,
        patient_id INTEGER,
        category_id INTEGER,
        provider_id INTEGER,
        repasse_percent INTEGER NOT NULL DEFAULT 0,
        repasse_paid INTEGER NOT NULL DEFAULT 0,
        cash_session_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE SET NULL,
        FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL,
        FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE SET NULL,
        FOREIGN KEY(cash_session_id) REFERENCES cash_sessions(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
    CREATE INDEX IF NOT EXISTS idx_tx_due ON transactions(due_date);
    CREATE INDEX IF NOT EXISTS idx_tx_kind ON transactions(kind);
    CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);

    -- ===== MÓDULOS DO PACIENTE (Painel) =====
    CREATE TABLE IF NOT EXISTS budgets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'aberto', -- aberto|aprovado|reprovado
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_budgets_patient ON budgets(patient_id);

    CREATE TABLE IF NOT EXISTS plan_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        budget_id INTEGER,
        tooth TEXT,
        procedure TEXT NOT NULL,
        amount_cents INTEGER NOT NULL DEFAULT 0,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        done_at TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY(budget_id) REFERENCES budgets(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_plan_patient ON plan_items(patient_id);

    CREATE TABLE IF NOT EXISTS plan_steps(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_item_id INTEGER NOT NULL,
        step TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        done_at TEXT,
        FOREIGN KEY(plan_item_id) REFERENCES plan_items(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_plan_steps_item ON plan_steps(plan_item_id);

    CREATE TABLE IF NOT EXISTS clinical_records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        queixa TEXT,
        historico TEXT,
        exames_extra TEXT,
        exames_intra TEXT,
        sinais_pa TEXT,
        sinais_fc TEXT,
        diagnostico TEXT,
        conduta TEXT,
        responsavel TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_records_patient ON clinical_records(patient_id);


    CREATE TABLE IF NOT EXISTS anamnesis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        responsavel TEXT,
        queixa TEXT,
        historico_medico TEXT,
        medicamentos TEXT,
        alergias TEXT,
        doencas TEXT,
        cirurgias TEXT,
        anestesia_reacao TEXT,
        sangramento TEXT,
        gestante TEXT,
        fumante TEXT,
        alcool TEXT,
        hipertensao INTEGER NOT NULL DEFAULT 0,
        diabetes INTEGER NOT NULL DEFAULT 0,
        cardiaco INTEGER NOT NULL DEFAULT 0,
        hepatite INTEGER NOT NULL DEFAULT 0,
        hiv INTEGER NOT NULL DEFAULT 0,
        observacoes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_anamnesis_patient ON anamnesis(patient_id);


    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        provider_id INTEGER,
        title TEXT NOT NULL DEFAULT 'Consulta',
        start_at TEXT NOT NULL,
        end_at TEXT,
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_appt_patient_start ON appointments(patient_id, start_at);

    CREATE TABLE IF NOT EXISTS odontograma(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        tooth TEXT NOT NULL,
        status TEXT NOT NULL,
        note TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(patient_id, tooth),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_odonto_patient ON odontograma(patient_id);

    CREATE TABLE IF NOT EXISTS app_settings(
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS birthday_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        sent_on TEXT NOT NULL,
        channel TEXT NOT NULL DEFAULT 'whatsapp',
        message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(patient_id, sent_on, channel),
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_bdaylog_patient_sent ON birthday_log(patient_id, sent_on);

    """)
    _ensure_finance_migrations(db)
    db.commit()

def ensure_seed_data():
    db = get_db()
    # Categorias padrão
    defaults = [
        ("Consultas", "income"),
        ("Procedimentos", "income"),
        ("Materiais/Estoque", "expense"),
        ("Aluguel", "expense"),
        ("Internet/Luz/Água", "expense"),
        ("Outros", "both"),
    ]
    for name, kind in defaults:
        db.execute("INSERT OR IGNORE INTO categories(name, kind) VALUES(?, ?)", (name, kind))
    # Mensagem padrão de aniversário (WhatsApp)
    db.execute(
        "INSERT OR IGNORE INTO app_settings(key, value) VALUES(?, ?)",
        (
            "birthday_template",
            "Oi {nome}! 🎉 Hoje é seu aniversário e a {clinica} deseja um dia incrível! Se quiser agendar sua consulta/revisão, é só me chamar por aqui 🙂",
        ),
    )
    db.commit()

def get_open_cash_session_id() -> int | None:
    db = get_db()
    row = db.execute(
        "SELECT id FROM cash_sessions WHERE closed_at IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return int(row["id"]) if row else None
