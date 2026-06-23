# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory, abort
from .auth import login_required
from .db import get_db
from .utils import cents_to_brl, parse_brl_to_cents

bp = Blueprint("patients", __name__, url_prefix="/patients")

TABS = {"resumo", "orcamentos", "plano_ficha", "anamnese", "agenda", "odontograma", "fotos", "timeline"}


def _dtlocal_to_sql(dtlocal: str | None) -> str | None:
    """Converte 'YYYY-MM-DDTHH:MM' em 'YYYY-MM-DD HH:MM:SS'."""
    if not dtlocal:
        return None
    s = dtlocal.strip()
    if not s:
        return None
    try:
        # datetime-local -> sem timezone
        dt = datetime.fromisoformat(s)
    except ValueError:
        # tenta 'YYYY-MM-DD HH:MM'
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _sql_to_br(dt_sql: str | None) -> str:
    if not dt_sql:
        return ""
    # formatos comuns: 'YYYY-MM-DD HH:MM:SS' ou 'YYYY-MM-DDTHH:MM'
    s = dt_sql.replace("T", " ")
    if len(s) >= 10:
        try:
            y, m, d = s[0:4], s[5:7], s[8:10]
            rest = s[10:].strip()
            if rest:
                return f"{d}/{m}/{y} {rest[:5]}"
            return f"{d}/{m}/{y}"
        except Exception:
            return dt_sql
    return dt_sql


def _phone_to_whatsapp(phone: str | None, message: str = "") -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits and not digits.startswith("55"):
        digits = "55" + digits
    return f"https://wa.me/{digits}?text={quote(message)}" if digits else ""


def _setting(db, key: str, default: str = "") -> str:
    row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row and row["value"] is not None else default


def _audit(db, action: str, entity: str, entity_id: int | None = None, detail: str | None = None) -> None:
    try:
        from flask import session
        db.execute(
            "INSERT INTO audit_log(user_id, action, entity, entity_id, detail) VALUES(?,?,?,?,?)",
            (session.get("user_id"), action, entity, entity_id, detail),
        )
    except Exception:
        pass


@bp.route("/")
@login_required
def list_patients():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        rows = db.execute(
            "SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? OR cpf LIKE ? OR email LIKE ? ORDER BY name ASC",
            (like, like, like, like),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM patients ORDER BY name ASC").fetchall()
    return render_template("patients_list.html", patients=rows, q=q)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("patient_form.html", patient=None)
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        cpf = request.form.get("cpf", "").strip()
        address = request.form.get("address", "").strip()
        birth_date = request.form.get("birth_date", "").strip() or None
        notes = request.form.get("notes", "").strip()
        db = get_db()
        db.execute(
            "INSERT INTO patients(name, phone, email, cpf, address, birth_date, notes) VALUES(?,?,?,?,?,?,?)",
            (name, phone, email, cpf, address, birth_date, notes),
        )
        db.commit()
        flash("Paciente cadastrado ✅", "success")
        return redirect(url_for("patients.list_patients"))
    return render_template("patient_form.html", patient=None)


@bp.route("/<int:pid>", methods=["GET"])
@login_required
def view_patient(pid: int):
    """Painel premium do paciente: resumo, linha do tempo, fotos, financeiro e módulos clínicos."""
    tab = (request.args.get("tab") or "resumo").strip()
    if tab not in TABS:
        tab = "resumo"

    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    if not patient:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("patients.list_patients"))

    providers = db.execute("SELECT * FROM providers WHERE active=1 ORDER BY name ASC").fetchall()
    budgets = db.execute("SELECT * FROM budgets WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()

    plan_rows = db.execute("SELECT * FROM plan_items WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()
    plan_ids = [int(r["id"]) for r in plan_rows]
    steps_map: dict[int, list[dict]] = {}
    if plan_ids:
        placeholders = ",".join(["?"] * len(plan_ids))
        step_rows = db.execute(
            f"SELECT * FROM plan_steps WHERE plan_item_id IN ({placeholders}) ORDER BY id ASC",
            tuple(plan_ids),
        ).fetchall()
        for st in step_rows:
            steps_map.setdefault(int(st["plan_item_id"]), []).append(dict(st))
    plan = [dict(r) | {"steps": steps_map.get(int(r["id"]), [])} for r in plan_rows]

    records = db.execute("SELECT * FROM clinical_records WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()
    anamneses = db.execute("SELECT * FROM anamnesis WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall() if tab == "anamnese" else []
    appts = db.execute(
        "SELECT a.*, p.name AS provider_name FROM appointments a "
        "LEFT JOIN providers p ON p.id=a.provider_id "
        "WHERE a.patient_id=? ORDER BY a.start_at DESC, a.id DESC",
        (pid,),
    ).fetchall() if tab in {"agenda", "resumo", "timeline"} else []

    odontos = []
    mapa = {}
    if tab == "odontograma":
        odontos = db.execute("SELECT * FROM odontograma WHERE patient_id=? ORDER BY tooth ASC", (pid,)).fetchall()
        mapa = {row["tooth"]: row["status"] for row in odontos}

    tx = db.execute(
        "SELECT t.*, c.name AS category_name FROM transactions t "
        "LEFT JOIN categories c ON c.id=t.category_id "
        "WHERE t.patient_id=? ORDER BY COALESCE(t.due_date,t.date) DESC, t.id DESC LIMIT 10",
        (pid,),
    ).fetchall()

    finance_summary_row = db.execute(
        """
        SELECT
          SUM(CASE WHEN kind='income' THEN COALESCE(final_amount_cents, amount_cents, 0) ELSE 0 END) AS income_total,
          SUM(CASE WHEN kind='income' THEN COALESCE(paid_amount_cents, 0) ELSE 0 END) AS income_paid,
          SUM(CASE WHEN kind='income' THEN COALESCE(balance_cents, 0) ELSE 0 END) AS income_pending,
          SUM(CASE WHEN kind='income' AND status='pending' AND COALESCE(due_date,date)<date('now') THEN COALESCE(balance_cents,0) ELSE 0 END) AS overdue
        FROM transactions WHERE patient_id=?
        """,
        (pid,),
    ).fetchone()
    finance_summary = {k: cents_to_brl(int(finance_summary_row[k] or 0)) for k in finance_summary_row.keys()}

    plan_total = sum(int(r["amount_cents"] or 0) for r in plan_rows)
    plan_done = sum(int(r["amount_cents"] or 0) for r in plan_rows if int(r["done"] or 0) == 1)
    plan_summary = {
        "total": cents_to_brl(plan_total),
        "done": cents_to_brl(plan_done),
        "pending": cents_to_brl(max(plan_total - plan_done, 0)),
        "count": len(plan_rows),
        "done_count": sum(1 for r in plan_rows if int(r["done"] or 0) == 1),
    }

    photos = db.execute(
        "SELECT * FROM treatment_photos WHERE patient_id=? ORDER BY id DESC",
        (pid,),
    ).fetchall() if tab in {"fotos", "resumo", "timeline"} else []

    # Linha do tempo misturando clínica, agenda, orçamento, financeiro e fotos
    timeline = []
    for b in budgets[:8]:
        timeline.append({"date": b["created_at"], "icon": "🧾", "title": "Orçamento", "text": f"{b['description']} • R$ {cents_to_brl(b['amount_cents'])} • {b['status']}"})
    for r in records[:8]:
        timeline.append({"date": r["created_at"], "icon": "🩺", "title": "Ficha clínica", "text": (r["queixa"] or r["diagnostico"] or "Registro clínico")[:120]})
    for a in appts[:8]:
        timeline.append({"date": a["start_at"], "icon": "🗓️", "title": "Agenda", "text": f"{a['title']} • {a['provider_name'] or '-'} • {a['status'] if 'status' in a.keys() else 'agendada'}"})
    for t in tx[:8]:
        timeline.append({"date": t["created_at"] or t["date"], "icon": "💰", "title": "Financeiro", "text": f"{t['description'] or 'Lançamento'} • R$ {cents_to_brl(t['final_amount_cents'] or t['amount_cents'])} • {t['status']}"})
    for ph in photos[:8]:
        timeline.append({"date": ph["created_at"], "icon": "📸", "title": "Foto do tratamento", "text": ph["caption"] or ph["original_name"] or "Foto adicionada"})
    timeline.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    timeline = timeline[:18]

    # WhatsApp para cobrança e lembrete
    clinic = _setting(db, "clinic_name", current_app.config.get("CLINIC_NAME", "Eduarda Imbelloni"))
    reminder_tpl = _setting(db, "whatsapp_reminder_template", "Olá, {paciente}! Passando para lembrar da sua consulta na {clinica} no dia {data} às {hora}.")
    charge_tpl = _setting(db, "whatsapp_charge_template", "Olá, {paciente}! Segue a cobrança referente a {descricao}: {link}")
    wa_charge = ""
    pending_tx = next((t for t in tx if t["kind"] == "income" and t["status"] == "pending"), None)
    if pending_tx:
        link = pending_tx["asaas_invoice_url"] if "asaas_invoice_url" in pending_tx.keys() and pending_tx["asaas_invoice_url"] else "link da cobrança"
        msg = charge_tpl.replace("{paciente}", patient["name"]).replace("{clinica}", clinic).replace("{descricao}", pending_tx["description"] or "tratamento").replace("{link}", link)
        wa_charge = _phone_to_whatsapp(patient["phone"], msg)

    return render_template(
        "patient_view.html",
        patient=patient,
        tab=tab,
        providers=providers,
        budgets=budgets,
        plan=plan,
        records=records,
        anamneses=anamneses,
        appts=appts,
        odontos=odontos,
        mapa=mapa,
        tx=tx,
        photos=photos,
        timeline=timeline,
        finance_summary=finance_summary,
        plan_summary=plan_summary,
        wa_charge=wa_charge,
        reminder_template=reminder_tpl,
        cents_to_brl=cents_to_brl,
        sql_to_br=_sql_to_br,
        phone_to_whatsapp=_phone_to_whatsapp,
    )

@bp.route("/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(pid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    if not patient:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("patients.list_patients"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("patient_form.html", patient=patient)
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        cpf = request.form.get("cpf", "").strip()
        address = request.form.get("address", "").strip()
        birth_date = request.form.get("birth_date", "").strip() or None
        notes = request.form.get("notes", "").strip()
        db.execute(
            "UPDATE patients SET name=?, phone=?, email=?, cpf=?, address=?, birth_date=?, notes=? WHERE id=?",
            (name, phone, email, cpf, address, birth_date, notes, pid),
        )
        db.commit()
        flash("Paciente atualizado ✅", "success")
        return redirect(url_for("patients.view_patient", pid=pid))
    return render_template("patient_form.html", patient=patient)


@bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def delete_patient(pid: int):
    db = get_db()
    # mantém os lançamentos (FK ON DELETE SET NULL), apenas desvincula
    db.execute("DELETE FROM patients WHERE id=?", (pid,))
    db.commit()
    flash("Paciente removido.", "info")
    return redirect(url_for("patients.list_patients"))


# =========================
# Orçamentos
# =========================

@bp.post("/<int:pid>/budgets/add")
@login_required
def budget_add(pid: int):
    description = (request.form.get("description") or "").strip()
    amount_raw = (request.form.get("amount") or "").strip()
    if not description:
        flash("Informe a descrição do orçamento.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))
    cents = parse_brl_to_cents(amount_raw)
    if cents <= 0:
        flash("Valor inválido. Ex: 150 ou 150,50.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))

    db = get_db()
    db.execute(
        "INSERT INTO budgets(patient_id, description, amount_cents, status) VALUES(?,?,?,?)",
        (pid, description, cents, "aberto"),
    )
    db.commit()
    flash("Orçamento adicionado ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))


@bp.get("/<int:pid>/budgets/<int:bid>/status/<s>")
@login_required
def budget_status(pid: int, bid: int, s: str):
    s = (s or "aberto").lower()
    if s not in {"aberto", "aprovado", "reprovado"}:
        s = "aberto"

    db = get_db()
    b = db.execute(
        "SELECT * FROM budgets WHERE id=? AND patient_id=?",
        (bid, pid),
    ).fetchone()
    if not b:
        flash("Orçamento não encontrado.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))

    db.execute("UPDATE budgets SET status=? WHERE id=? AND patient_id=?", (s, bid, pid))

    if s == "aprovado":
        # Evita duplicar item do plano para o mesmo orçamento
        ex = db.execute("SELECT id FROM plan_items WHERE budget_id=?", (bid,)).fetchone()
        if not ex:
            db.execute(
                "INSERT INTO plan_items(patient_id, budget_id, tooth, procedure, amount_cents, done) "
                "VALUES (?,?,?,?,?,0)",
                (pid, bid, None, b["description"], int(b["amount_cents"])),
            )

    db.commit()
    flash("Status atualizado ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))


@bp.get("/<int:pid>/budgets/<int:bid>/print")
@login_required
def budget_print(pid: int, bid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    budget = db.execute(
        "SELECT * FROM budgets WHERE id=? AND patient_id=?",
        (bid, pid),
    ).fetchone()
    if not patient or not budget:
        flash("Orçamento não encontrado.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="orcamentos"))
    return render_template(
        "budget_print.html",
        patient=patient,
        budget=budget,
        cents_to_brl=cents_to_brl,
        sql_to_br=_sql_to_br,
    )


# =========================
# Plano e Ficha
# =========================

@bp.get("/<int:pid>/plan/<int:iid>/toggle")
@login_required
def plan_toggle(pid: int, iid: int):
    db = get_db()
    row = db.execute(
        "SELECT id, done FROM plan_items WHERE id=? AND patient_id=?",
        (iid, pid),
    ).fetchone()
    if not row:
        flash("Procedimento não encontrado.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))

    if int(row["done"]) == 1:
        db.execute(
            "UPDATE plan_items SET done=0, done_at=NULL WHERE id=? AND patient_id=?",
            (iid, pid),
        )
    else:
        db.execute(
            "UPDATE plan_items SET done=1, done_at=datetime('now') WHERE id=? AND patient_id=?",
            (iid, pid),
        )
    db.commit()
    return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))


@bp.post("/<int:pid>/plan/<int:iid>/steps/add")
@login_required
def plan_add_step(pid: int, iid: int):
    step = (request.form.get("step") or "").strip()
    if not step:
        flash("Informe a etapa.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))

    db = get_db()
    # garante que o item pertence ao paciente
    ex = db.execute("SELECT id FROM plan_items WHERE id=? AND patient_id=?", (iid, pid)).fetchone()
    if not ex:
        flash("Procedimento não encontrado.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))

    db.execute("INSERT INTO plan_steps(plan_item_id, step, done) VALUES(?,?,0)", (iid, step))
    db.commit()
    return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))


@bp.get("/<int:pid>/plan/steps/<int:sid>/toggle")
@login_required
def plan_step_toggle(pid: int, sid: int):
    db = get_db()
    row = db.execute(
        "SELECT ps.id, ps.done FROM plan_steps ps "
        "JOIN plan_items pi ON pi.id=ps.plan_item_id "
        "WHERE ps.id=? AND pi.patient_id=?",
        (sid, pid),
    ).fetchone()
    if not row:
        flash("Etapa não encontrada.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))

    if int(row["done"]) == 1:
        db.execute("UPDATE plan_steps SET done=0, done_at=NULL WHERE id=?", (sid,))
    else:
        db.execute("UPDATE plan_steps SET done=1, done_at=datetime('now') WHERE id=?", (sid,))
    db.commit()
    return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))


@bp.post("/<int:pid>/records/save")
@login_required
def record_save(pid: int):
    f = request.form
    db = get_db()
    db.execute(
        "INSERT INTO clinical_records(patient_id, queixa, historico, exames_extra, exames_intra, sinais_pa, sinais_fc, diagnostico, conduta, responsavel) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            pid,
            f.get("queixa") or None,
            f.get("historico") or None,
            f.get("exames_extra") or None,
            f.get("exames_intra") or None,
            f.get("sinais_pa") or None,
            f.get("sinais_fc") or None,
            f.get("diagnostico") or None,
            f.get("conduta") or None,
            f.get("responsavel") or None,
        ),
    )
    db.commit()
    flash("Ficha salva ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))


@bp.get("/<int:pid>/records/<int:rid>")
@login_required
def record_view(pid: int, rid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    rec = db.execute(
        "SELECT * FROM clinical_records WHERE id=? AND patient_id=?",
        (rid, pid),
    ).fetchone()
    if not patient or not rec:
        flash("Ficha não encontrada.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))
    return render_template("record_view.html", patient=patient, rec=rec, sql_to_br=_sql_to_br)


@bp.get("/<int:pid>/records/<int:rid>/print")
@login_required
def record_print(pid: int, rid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    rec = db.execute(
        "SELECT * FROM clinical_records WHERE id=? AND patient_id=?",
        (rid, pid),
    ).fetchone()
    if not patient or not rec:
        flash("Ficha não encontrada.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="plano_ficha"))
    return render_template("record_print.html", patient=patient, rec=rec, sql_to_br=_sql_to_br)


# =========================
# Anamnese
# =========================

@bp.post("/<int:pid>/anamnese/save")
@login_required
def anamnesis_save(pid: int):
    f = request.form
    def _ck(name: str) -> int:
        return 1 if (f.get(name) in {"1", "on", "true", "True", "yes", "sim"}) else 0

    db = get_db()
    db.execute(
        "INSERT INTO anamnesis(patient_id, responsavel, queixa, historico_medico, medicamentos, alergias, doencas, cirurgias, "
        "anestesia_reacao, sangramento, gestante, fumante, alcool, hipertensao, diabetes, cardiaco, hepatite, hiv, observacoes) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            pid,
            (f.get("responsavel") or "").strip() or None,
            (f.get("queixa") or "").strip() or None,
            (f.get("historico_medico") or "").strip() or None,
            (f.get("medicamentos") or "").strip() or None,
            (f.get("alergias") or "").strip() or None,
            (f.get("doencas") or "").strip() or None,
            (f.get("cirurgias") or "").strip() or None,
            (f.get("anestesia_reacao") or "").strip() or None,
            (f.get("sangramento") or "").strip() or None,
            (f.get("gestante") or "").strip() or None,
            (f.get("fumante") or "").strip() or None,
            (f.get("alcool") or "").strip() or None,
            _ck("hipertensao"),
            _ck("diabetes"),
            _ck("cardiaco"),
            _ck("hepatite"),
            _ck("hiv"),
            (f.get("observacoes") or "").strip() or None,
        ),
    )
    db.commit()
    flash("Anamnese salva ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="anamnese"))


@bp.get("/<int:pid>/anamnese/<int:aid>")
@login_required
def anamnesis_view(pid: int, aid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    rec = db.execute(
        "SELECT * FROM anamnesis WHERE id=? AND patient_id=?",
        (aid, pid),
    ).fetchone()
    if not patient or not rec:
        flash("Anamnese não encontrada.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="anamnese"))
    return render_template("anamnesis_view.html", patient=patient, rec=rec, sql_to_br=_sql_to_br)


@bp.get("/<int:pid>/anamnese/<int:aid>/print")
@login_required
def anamnesis_print(pid: int, aid: int):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    rec = db.execute(
        "SELECT * FROM anamnesis WHERE id=? AND patient_id=?",
        (aid, pid),
    ).fetchone()
    if not patient or not rec:
        flash("Anamnese não encontrada.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="anamnese"))
    return render_template("anamnesis_print.html", patient=patient, rec=rec, sql_to_br=_sql_to_br)


# =========================
# Agenda (por paciente)
# =========================

@bp.post("/<int:pid>/appointments/add")
@login_required
def appointment_add(pid: int):
    provider_id = request.form.get("provider_id") or None
    provider_id_int = int(provider_id) if provider_id and str(provider_id).isdigit() else None
    title = (request.form.get("title") or "Consulta").strip() or "Consulta"
    note = (request.form.get("note") or "").strip() or None
    status = (request.form.get("status") or "agendada").strip()
    if status not in {"agendada", "confirmada", "compareceu", "faltou", "cancelada"}:
        status = "agendada"

    start_at = _dtlocal_to_sql(request.form.get("start_at"))
    end_at = _dtlocal_to_sql(request.form.get("end_at"))

    if not start_at:
        flash("Informe a data/hora do agendamento.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="agenda"))

    if not end_at:
        try:
            dt = datetime.strptime(start_at, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=30)
            end_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            end_at = None

    db = get_db()
    db.execute(
        "INSERT INTO appointments(patient_id, provider_id, title, start_at, end_at, note, status) VALUES(?,?,?,?,?,?,?)",
        (pid, provider_id_int, title, start_at, end_at, note, status),
    )
    db.commit()
    flash("Agendamento salvo ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="agenda"))


@bp.post("/<int:pid>/appointments/<int:aid>/delete")
@login_required
def appointment_delete(pid: int, aid: int):
    db = get_db()
    db.execute("DELETE FROM appointments WHERE id=? AND patient_id=?", (aid, pid))
    db.commit()
    flash("Agendamento excluído.", "info")
    return redirect(url_for("patients.view_patient", pid=pid, tab="agenda"))



# =========================
# Fotos do tratamento
# =========================

@bp.post("/<int:pid>/photos/add")
@login_required
def photo_add(pid: int):
    db = get_db()
    patient = db.execute("SELECT id FROM patients WHERE id=?", (pid,)).fetchone()
    if not patient:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("patients.list_patients"))
    file = request.files.get("photo")
    caption = (request.form.get("caption") or "").strip()
    if not file or not file.filename:
        flash("Escolha uma imagem para enviar.", "warning")
        return redirect(url_for("patients.view_patient", pid=pid, tab="fotos"))
    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        flash("Envie imagem JPG, PNG ou WEBP.", "danger")
        return redirect(url_for("patients.view_patient", pid=pid, tab="fotos"))
    folder = Path(current_app.config.get("UPLOAD_FOLDER", "/data/uploads")) / "patients" / str(pid)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{ext}"
    file.save(folder / filename)
    db.execute(
        "INSERT INTO treatment_photos(patient_id, filename, original_name, caption) VALUES(?,?,?,?)",
        (pid, filename, file.filename, caption or None),
    )
    _audit(db, "add_photo", "patient", pid, caption)
    db.commit()
    flash("Foto adicionada ao tratamento ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="fotos"))


@bp.get("/<int:pid>/photos/<int:photo_id>/file")
@login_required
def photo_file(pid: int, photo_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM treatment_photos WHERE id=? AND patient_id=?", (photo_id, pid)).fetchone()
    if not row:
        abort(404)
    folder = Path(current_app.config.get("UPLOAD_FOLDER", "/data/uploads")) / "patients" / str(pid)
    return send_from_directory(folder, row["filename"])


@bp.post("/<int:pid>/photos/<int:photo_id>/delete")
@login_required
def photo_delete(pid: int, photo_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM treatment_photos WHERE id=? AND patient_id=?", (photo_id, pid)).fetchone()
    if row:
        folder = Path(current_app.config.get("UPLOAD_FOLDER", "/data/uploads")) / "patients" / str(pid)
        try:
            (folder / row["filename"]).unlink(missing_ok=True)
        except Exception:
            pass
        db.execute("DELETE FROM treatment_photos WHERE id=? AND patient_id=?", (photo_id, pid))
        _audit(db, "delete_photo", "patient", pid, row["original_name"])
        db.commit()
        flash("Foto removida.", "info")
    return redirect(url_for("patients.view_patient", pid=pid, tab="fotos"))


@bp.post("/<int:pid>/appointments/<int:aid>/status")
@login_required
def appointment_status(pid: int, aid: int):
    status = (request.form.get("status") or "agendada").strip()
    if status not in {"agendada", "confirmada", "compareceu", "faltou", "cancelada"}:
        status = "agendada"
    db = get_db()
    db.execute("UPDATE appointments SET status=? WHERE id=? AND patient_id=?", (status, aid, pid))
    _audit(db, "appointment_status", "appointment", aid, status)
    db.commit()
    flash("Status do agendamento atualizado ✅", "success")
    return redirect(url_for("patients.view_patient", pid=pid, tab="agenda"))


# =========================
# Odontograma
# =========================

@bp.post("/<int:pid>/odontograma/save_json")
@login_required
def odontograma_save_json(pid: int):
    payload = request.get_json(silent=True) or {}
    tooth = (payload.get("tooth") or "").strip()
    status = (payload.get("status") or "").strip()
    note = (payload.get("note") or "").strip()

    if not tooth or not status:
        return jsonify({"ok": False, "error": "tooth/status obrigatórios"}), 400

    db = get_db()
    # Upsert usando UNIQUE(patient_id,tooth)
    db.execute(
        "INSERT INTO odontograma(patient_id, tooth, status, note, updated_at) "
        "VALUES(?,?,?,?,datetime('now')) "
        "ON CONFLICT(patient_id, tooth) DO UPDATE SET "
        "status=excluded.status, note=excluded.note, updated_at=datetime('now')",
        (pid, tooth, status, note),
    )
    db.commit()
    row = db.execute(
        "SELECT tooth, status, note, updated_at FROM odontograma WHERE patient_id=? AND tooth=?",
        (pid, tooth),
    ).fetchone()
    return jsonify({"ok": True, "row": dict(row)}), 200
