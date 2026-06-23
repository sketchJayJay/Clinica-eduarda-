# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

from flask import Blueprint, render_template, request, redirect, url_for, flash

from .auth import login_required
from .db import get_db
from .utils import cents_to_brl

bp = Blueprint("crm", __name__, url_prefix="/crm")

TASK_PRIORITIES = {"baixa", "normal", "alta", "urgente"}
LEAD_STATUSES = {"novo", "contato", "orçamento", "agendado", "perdido", "convertido"}


def _phone_to_whatsapp(phone: str | None, message: str = "") -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits and not digits.startswith("55"):
        digits = "55" + digits
    return f"https://wa.me/{digits}?text={quote(message)}" if digits else ""


def _setting(db, key: str, default: str = "") -> str:
    row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row and row["value"] is not None else default


@bp.route("/", methods=["GET"])
@login_required
def index():
    db = get_db()
    today = date.today().isoformat()
    next_7 = (date.today() + timedelta(days=7)).isoformat()
    old_cutoff = (date.today() - timedelta(days=180)).isoformat()
    clinic = _setting(db, "clinic_name", "Eduarda Imbelloni Clínica Especializada")

    task_filter = request.args.get("task_status", "aberta")
    if task_filter not in {"aberta", "feito", "todos"}:
        task_filter = "aberta"
    if task_filter == "todos":
        task_where = ""
        task_params = []
    else:
        task_where = "WHERE t.status=?"
        task_params = [task_filter]

    tasks = db.execute(
        f"""
        SELECT t.*, p.name AS patient_name, p.phone AS patient_phone
        FROM patient_tasks t
        LEFT JOIN patients p ON p.id=t.patient_id
        {task_where}
        ORDER BY
          CASE WHEN t.status='aberta' AND COALESCE(t.due_date,'9999-12-31') < date('now') THEN 0 ELSE 1 END,
          COALESCE(t.due_date,'9999-12-31') ASC,
          CASE t.priority WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
          t.id DESC
        LIMIT 80
        """,
        tuple(task_params),
    ).fetchall()

    leads = db.execute(
        "SELECT * FROM leads ORDER BY CASE status WHEN 'novo' THEN 0 WHEN 'contato' THEN 1 WHEN 'orçamento' THEN 2 WHEN 'agendado' THEN 3 WHEN 'convertido' THEN 4 ELSE 5 END, COALESCE(next_contact_date,'9999-12-31') ASC, id DESC LIMIT 80"
    ).fetchall()

    upcoming = db.execute(
        """
        SELECT a.*, p.name AS patient_name, p.phone AS patient_phone, pr.name AS provider_name
        FROM appointments a
        JOIN patients p ON p.id=a.patient_id
        LEFT JOIN providers pr ON pr.id=a.provider_id
        WHERE substr(a.start_at,1,10) BETWEEN ? AND ?
          AND COALESCE(a.status,'agendada') NOT IN ('cancelada','faltou')
        ORDER BY a.start_at ASC
        LIMIT 20
        """,
        (today, next_7),
    ).fetchall()

    no_return = db.execute(
        """
        SELECT p.*,
          MAX(substr(a.start_at,1,10)) AS last_visit
        FROM patients p
        LEFT JOIN appointments a ON a.patient_id=p.id
        GROUP BY p.id
        HAVING last_visit IS NULL OR last_visit <= ?
        ORDER BY COALESCE(last_visit,'1900-01-01') ASC, p.name COLLATE NOCASE ASC
        LIMIT 30
        """,
        (old_cutoff,),
    ).fetchall()

    overdue_receivables = db.execute(
        """
        SELECT t.*, p.name AS patient_name, p.phone AS patient_phone
        FROM transactions t
        LEFT JOIN patients p ON p.id=t.patient_id
        WHERE t.kind='income' AND t.status='pending' AND COALESCE(t.due_date,t.date)<date('now')
        ORDER BY COALESCE(t.due_date,t.date) ASC
        LIMIT 25
        """
    ).fetchall()

    stats = {
        "tasks_open": db.execute("SELECT COUNT(*) c FROM patient_tasks WHERE status='aberta'").fetchone()["c"],
        "tasks_overdue": db.execute("SELECT COUNT(*) c FROM patient_tasks WHERE status='aberta' AND due_date IS NOT NULL AND due_date < date('now')").fetchone()["c"],
        "leads_open": db.execute("SELECT COUNT(*) c FROM leads WHERE status NOT IN ('convertido','perdido')").fetchone()["c"],
        "appointments_week": db.execute("SELECT COUNT(*) c FROM appointments WHERE substr(start_at,1,10) BETWEEN ? AND ?", (today, next_7)).fetchone()["c"],
    }

    patients = db.execute("SELECT id, name, phone FROM patients ORDER BY name COLLATE NOCASE").fetchall()

    return render_template(
        "crm.html",
        stats=stats,
        tasks=tasks,
        leads=leads,
        upcoming=upcoming,
        no_return=no_return,
        overdue_receivables=overdue_receivables,
        patients=patients,
        task_filter=task_filter,
        today=today,
        clinic=clinic,
        cents_to_brl=cents_to_brl,
        wa=_phone_to_whatsapp,
    )


@bp.post("/tasks/add")
@login_required
def task_add():
    db = get_db()
    patient_id = request.form.get("patient_id") or None
    patient_id = int(patient_id) if str(patient_id).isdigit() else None
    title = (request.form.get("title") or "").strip()
    due_date = (request.form.get("due_date") or "").strip() or None
    priority = (request.form.get("priority") or "normal").strip()
    note = (request.form.get("note") or "").strip() or None
    if priority not in TASK_PRIORITIES:
        priority = "normal"
    if not title:
        flash("Informe o título da tarefa.", "danger")
        return redirect(url_for("crm.index"))
    db.execute(
        "INSERT INTO patient_tasks(patient_id, title, due_date, priority, note) VALUES(?,?,?,?,?)",
        (patient_id, title, due_date, priority, note),
    )
    db.commit()
    flash("Tarefa criada ✅", "success")
    return redirect(request.referrer or url_for("crm.index"))


@bp.post("/tasks/<int:tid>/toggle")
@login_required
def task_toggle(tid: int):
    db = get_db()
    task = db.execute("SELECT * FROM patient_tasks WHERE id=?", (tid,)).fetchone()
    if not task:
        flash("Tarefa não encontrada.", "warning")
        return redirect(url_for("crm.index"))
    if task["status"] == "feito":
        db.execute("UPDATE patient_tasks SET status='aberta', done_at=NULL WHERE id=?", (tid,))
    else:
        db.execute("UPDATE patient_tasks SET status='feito', done_at=datetime('now') WHERE id=?", (tid,))
    db.commit()
    return redirect(request.referrer or url_for("crm.index"))


@bp.post("/tasks/<int:tid>/delete")
@login_required
def task_delete(tid: int):
    db = get_db()
    db.execute("DELETE FROM patient_tasks WHERE id=?", (tid,))
    db.commit()
    flash("Tarefa removida.", "info")
    return redirect(request.referrer or url_for("crm.index"))


@bp.post("/leads/add")
@login_required
def lead_add():
    db = get_db()
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    source = (request.form.get("source") or "").strip() or None
    interest = (request.form.get("interest") or "").strip() or None
    next_contact_date = (request.form.get("next_contact_date") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None
    if not name:
        flash("Informe o nome do lead.", "danger")
        return redirect(url_for("crm.index"))
    db.execute(
        "INSERT INTO leads(name, phone, source, interest, next_contact_date, notes) VALUES(?,?,?,?,?,?)",
        (name, phone, source, interest, next_contact_date, notes),
    )
    db.commit()
    flash("Lead cadastrado ✅", "success")
    return redirect(url_for("crm.index"))


@bp.post("/leads/<int:lid>/status")
@login_required
def lead_status(lid: int):
    status = (request.form.get("status") or "novo").strip()
    if status not in LEAD_STATUSES:
        status = "novo"
    db = get_db()
    db.execute("UPDATE leads SET status=? WHERE id=?", (status, lid))
    db.commit()
    return redirect(url_for("crm.index"))


@bp.post("/leads/<int:lid>/delete")
@login_required
def lead_delete(lid: int):
    db = get_db()
    db.execute("DELETE FROM leads WHERE id=?", (lid,))
    db.commit()
    flash("Lead removido.", "info")
    return redirect(url_for("crm.index"))
