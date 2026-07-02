# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote
from flask import current_app
from flask import Blueprint, render_template, request, session, jsonify
from .auth import login_required
from .db import get_db, get_open_cash_session_id
from .utils import cents_to_brl

bp = Blueprint("dashboard", __name__)


def _digits_phone(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _get_setting(db, key: str, default: str = "") -> str:
    row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return (row["value"] if row and row["value"] is not None else default)


def _render_charge_message(template: str, *, paciente: str, descricao: str, valor: str, vencimento: str, clinica: str) -> str:
    msg = template or ""
    return (
        msg.replace("{paciente}", paciente or "")
           .replace("{nome}", paciente or "")
           .replace("{descricao}", descricao or "")
           .replace("{valor}", valor or "")
           .replace("{vencimento}", vencimento or "")
           .replace("{clinica}", clinica or "")
           .replace("{link}", "")
    )


@bp.post("/charge-reminders/mark_sent")
@login_required
def mark_charge_sent():
    db = get_db()
    transaction_id = request.form.get("transaction_id", type=int)
    sent_on = (request.form.get("sent_on") or date.today().isoformat()).strip()
    message = (request.form.get("message") or "").strip()
    if not transaction_id:
        return jsonify({"ok": False, "error": "transaction_id faltando"}), 400

    tx = db.execute("SELECT id, patient_id FROM transactions WHERE id=?", (transaction_id,)).fetchone()
    if not tx:
        return jsonify({"ok": False, "error": "lançamento não encontrado"}), 404

    db.execute(
        "INSERT OR IGNORE INTO charge_log(transaction_id, patient_id, sent_on, channel, message) VALUES(?,?,?, 'whatsapp', ?)",
        (transaction_id, tx["patient_id"], sent_on, message),
    )
    db.commit()
    return jsonify({"ok": True})


@bp.route("/")
@login_required
def index():
    db = get_db()
    finance_unlocked = bool(session.get("finance_unlocked"))
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()

    # Por segurança, o Financeiro não aparece na Home enquanto não for desbloqueado.
    # Depois do desbloqueio, mostramos o resumo normalmente.
    stats = None
    if finance_unlocked:
        def sum_cents(sql, params):
            row = db.execute(sql, params).fetchone()
            return int(row["s"] or 0)

        income_today = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='income' AND status='paid' AND date=?",
            (today,),
        )
        expense_today = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='expense' AND status='paid' AND date=?",
            (today,),
        )
        income_month = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='income' AND status='paid' AND date>=?",
            (month_start,),
        )
        expense_month = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='expense' AND status='paid' AND date>=?",
            (month_start,),
        )
        pending_receivables = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='income' AND status='pending'",
            (),
        )
        pending_payables = sum_cents(
            "SELECT SUM(amount_cents) s FROM transactions WHERE kind='expense' AND status='pending'",
            (),
        )

        open_cash_id = get_open_cash_session_id()
        cash_total = 0
        if open_cash_id:
            cash_total = sum_cents(
                "SELECT SUM(amount_cents) s FROM transactions WHERE status='paid' AND payment_method='cash' AND cash_session_id=?",
                (open_cash_id,),
            )
            row_open = db.execute("SELECT open_balance_cents FROM cash_sessions WHERE id=?", (open_cash_id,)).fetchone()
            cash_total += int(row_open["open_balance_cents"] or 0)

        stats = {
            "income_today": cents_to_brl(income_today),
            "expense_today": cents_to_brl(expense_today),
            "income_month": cents_to_brl(income_month),
            "expense_month": cents_to_brl(expense_month),
            "pending_receivables": cents_to_brl(pending_receivables),
            "pending_payables": cents_to_brl(pending_payables),
            "cash_open": bool(open_cash_id),
            "cash_total": cents_to_brl(cash_total),
        }
    # Lembrete de aniversários (mostra na Home)
    tpl_row = db.execute("SELECT value FROM app_settings WHERE key='birthday_template'").fetchone()
    birthday_template = (tpl_row["value"] if tpl_row and tpl_row["value"] else "Oi {nome}! 🎉 A {clinica} deseja um dia incrível! 🙂")
    clinica = current_app.config.get("CLINIC_NAME", "Eduarda Imbelloni")

    mmdd = date.today().strftime("%m-%d")
    bday_rows = db.execute(
        "SELECT id, name, phone, birth_date FROM patients WHERE birth_date IS NOT NULL AND birth_date!='' AND substr(birth_date,6,5)=? ORDER BY name COLLATE NOCASE",
        (mmdd,),
    ).fetchall()

    sent_today = {
        int(r["patient_id"])
        for r in db.execute("SELECT patient_id FROM birthday_log WHERE sent_on=? AND channel='whatsapp'", (today,)).fetchall()
    }

    todays_birthdays = []
    for r in bday_rows:
        msg = (birthday_template or "").replace("{nome}", r["name"]).replace("{clinica}", clinica)
        phone = "".join(ch for ch in (r["phone"] or "") if ch.isdigit())
        if phone and not phone.startswith("55"):
            phone = "55" + phone
        wa_link = f"https://wa.me/{phone}?text={quote(msg)}" if phone else ""
        todays_birthdays.append({
            "id": int(r["id"]),
            "name": r["name"],
            "phone": r["phone"] or "",
            "birth_date": r["birth_date"] or "",
            "message": msg,
            "wa_link": wa_link,
            "sent": int(r["id"]) in sent_today,
        })

    # Lembrete de cobranças do dia e vencidas (somente com financeiro desbloqueado)
    payment_reminders = []
    payment_reminders_count = 0
    charge_template = _get_setting(
        db,
        "whatsapp_charge_template",
        "Oi {paciente}, tudo bem? Passando para lembrar do pagamento referente a {descricao}, no valor de R$ {valor}, com vencimento em {vencimento}. Qualquer dúvida, estamos à disposição. {clinica}",
    )
    if finance_unlocked:
        charge_sent_today = {
            int(r["transaction_id"])
            for r in db.execute("SELECT transaction_id FROM charge_log WHERE sent_on=? AND channel='whatsapp'", (today,)).fetchall()
        }
        pay_rows = db.execute(
            """
            SELECT t.*, p.name AS patient_name, p.phone AS patient_phone
            FROM transactions t
            LEFT JOIN patients p ON p.id=t.patient_id
            WHERE t.kind='income'
              AND t.status='pending'
              AND COALESCE(t.balance_cents, t.final_amount_cents, t.amount_cents, 0) > 0
              AND COALESCE(t.due_date, t.date) <= ?
            ORDER BY COALESCE(t.due_date, t.date) ASC, p.name COLLATE NOCASE
            LIMIT 20
            """,
            (today,),
        ).fetchall()
        for r in pay_rows:
            due = r["due_date"] or r["date"] or today
            balance = int(r["balance_cents"] if r["balance_cents"] is not None else (r["final_amount_cents"] or r["amount_cents"] or 0))
            patient_name = r["patient_name"] or "Paciente"
            desc = r["description"] or "pagamento"
            msg = _render_charge_message(
                charge_template,
                paciente=patient_name,
                descricao=desc,
                valor=cents_to_brl(balance),
                vencimento=due,
                clinica=clinica,
            )
            phone = _digits_phone(r["patient_phone"] or "")
            if phone and not phone.startswith("55"):
                phone = "55" + phone
            payment_reminders.append({
                "id": int(r["id"]),
                "patient_id": int(r["patient_id"]) if r["patient_id"] else None,
                "patient_name": patient_name,
                "phone": r["patient_phone"] or "",
                "description": desc,
                "due_date": due,
                "balance": cents_to_brl(balance),
                "overdue": due < today,
                "sent": int(r["id"]) in charge_sent_today,
                "message": msg,
                "wa_link": f"https://wa.me/{phone}?text={quote(msg)}" if phone else "",
            })
        payment_reminders_count = len(payment_reminders)

    # Premium V3: operacional do dia, consultas próximas, tarefas e leads
    week_end = (date.today() + timedelta(days=7)).isoformat()
    agenda_today = db.execute(
        """
        SELECT a.*, p.name AS patient_name, p.phone AS patient_phone, pr.name AS provider_name
        FROM appointments a
        JOIN patients p ON p.id=a.patient_id
        LEFT JOIN providers pr ON pr.id=a.provider_id
        WHERE substr(a.start_at,1,10)=?
        ORDER BY a.start_at ASC
        LIMIT 12
        """,
        (today,),
    ).fetchall()
    tasks_due = db.execute(
        """
        SELECT t.*, p.name AS patient_name, p.phone AS patient_phone
        FROM patient_tasks t
        LEFT JOIN patients p ON p.id=t.patient_id
        WHERE t.status='aberta' AND (t.due_date IS NULL OR t.due_date<=?)
        ORDER BY COALESCE(t.due_date,'9999-12-31') ASC,
          CASE t.priority WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
          t.id DESC
        LIMIT 10
        """,
        (today,),
    ).fetchall()
    leads_due = db.execute(
        """
        SELECT * FROM leads
        WHERE status NOT IN ('convertido','perdido') AND (next_contact_date IS NULL OR next_contact_date<=?)
        ORDER BY COALESCE(next_contact_date,'9999-12-31') ASC, id DESC
        LIMIT 10
        """,
        (today,),
    ).fetchall()
    open_budgets = db.execute(
        """
        SELECT b.*, p.name AS patient_name
        FROM budgets b JOIN patients p ON p.id=b.patient_id
        WHERE b.status='aberto'
        ORDER BY b.id DESC LIMIT 10
        """
    ).fetchall()
    ops = {
        "patients_total": db.execute("SELECT COUNT(*) c FROM patients").fetchone()["c"],
        "agenda_today_count": len(agenda_today),
        "tasks_due_count": len(tasks_due),
        "leads_due_count": len(leads_due),
        "payments_due_count": payment_reminders_count,
        "week_appointments": db.execute("SELECT COUNT(*) c FROM appointments WHERE substr(start_at,1,10) BETWEEN ? AND ?", (today, week_end)).fetchone()["c"],
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        todays_birthdays=todays_birthdays,
        agenda_today=agenda_today,
        tasks_due=tasks_due,
        leads_due=leads_due,
        open_budgets=open_budgets,
        payment_reminders=payment_reminders,
        charge_template=charge_template,
        ops=ops,
    )