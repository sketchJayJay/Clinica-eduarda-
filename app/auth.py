# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import zipfile
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, current_app, send_file
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, init_db, ensure_seed_data

bp = Blueprint("auth", __name__)

ROLE_LABELS = {
    "admin": "Administrador",
    "recepcao": "Recepção",
    "profissional": "Profissional",
    "financeiro": "Financeiro",
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        init_db()
        ensure_seed_data()
        if session.get("user_id") is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles: str):
    def deco(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            init_db()
            ensure_seed_data()
            if session.get("user_id") is None:
                return redirect(url_for("auth.login"))
            user = getattr(g, "user", None)
            role = (user["role"] if user and "role" in user.keys() else "admin")
            if role not in roles and role != "admin":
                flash("Seu usuário não tem permissão para acessar essa área.", "warning")
                return redirect(url_for("dashboard.index"))
            return view(*args, **kwargs)
        return wrapped
    return deco


def get_settings_map() -> dict[str, str]:
    db = get_db()
    rows = db.execute("SELECT key, value FROM app_settings").fetchall()
    return {r["key"]: (r["value"] or "") for r in rows}


def set_setting(key: str, value: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def has_any_user() -> bool:
    try:
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        return bool(row and int(row["c"] or 0) > 0)
    except Exception:
        return False


def first_setup_pending() -> bool:
    """Mostra a configuração inicial também quando o sistema veio com o usuário padrão admin.

    Isso permite que a clínica abra o sistema pela primeira vez e já escolha
    o próprio login, senha de entrada e senha do financeiro, sem precisar
    entrar como admin/admin123 antes.
    """
    try:
        db = get_db()
        settings = get_settings_map()
        if settings.get("first_setup_done") == "1":
            return False

        total = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] or 0
        if int(total) <= 0:
            return True

        # Se existe somente o usuário padrão admin, deixa a clínica personalizar.
        admin = db.execute("SELECT * FROM users WHERE username='admin' ORDER BY id ASC LIMIT 1").fetchone()
        return bool(int(total) == 1 and admin)
    except Exception:
        return False


def log_action(action: str, entity: str | None = None, entity_id: int | None = None, detail: str | None = None) -> None:
    try:
        db = get_db()
        db.execute(
            "INSERT INTO audit_log(user_id, action, entity, entity_id, detail) VALUES(?,?,?,?,?)",
            (session.get("user_id"), action, entity, entity_id, detail),
        )
    except Exception:
        pass


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        try:
            g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        except Exception:
            g.user = None


@bp.route("/setup", methods=["GET", "POST"])
def first_setup():
    """Primeiro acesso: cria o login principal e a senha do financeiro.

    Essa tela só aparece enquanto ainda não existir usuário cadastrado.
    Depois disso, o sistema volta ao fluxo normal de login.
    """
    init_db()
    ensure_seed_data()
    db = get_db()

    if not first_setup_pending():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        finance_password = request.form.get("finance_password") or ""
        finance_password2 = request.form.get("finance_password2") or ""

        if len(username) < 3:
            flash("Escolha um usuário com pelo menos 3 caracteres.", "danger")
            return render_template("first_setup.html", username=username)
        if len(password) < 6:
            flash("A senha de entrada precisa ter pelo menos 6 caracteres.", "danger")
            return render_template("first_setup.html", username=username)
        if password != password2:
            flash("As senhas de entrada não conferem.", "danger")
            return render_template("first_setup.html", username=username)
        if len(finance_password) < 4:
            flash("A senha do financeiro precisa ter pelo menos 4 caracteres.", "danger")
            return render_template("first_setup.html", username=username)
        if finance_password != finance_password2:
            flash("As senhas do financeiro não conferem.", "danger")
            return render_template("first_setup.html", username=username)

        existing_admin = db.execute("SELECT * FROM users WHERE username='admin' ORDER BY id ASC LIMIT 1").fetchone()
        if existing_admin:
            uid = int(existing_admin["id"])
            db.execute(
                "UPDATE users SET username=?, password_hash=?, role=? WHERE id=?",
                (username, generate_password_hash(password), "admin", uid),
            )
        else:
            db.execute(
                "INSERT INTO users(username, password_hash, role) VALUES(?, ?, ?)",
                (username, generate_password_hash(password), "admin"),
            )
            uid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        set_setting("finance_password", finance_password)
        set_setting("first_setup_done", "1")
        db.execute(
            "INSERT INTO audit_log(user_id, action, entity, entity_id, detail) VALUES(?,?,?,?,?)",
            (int(uid), "first_setup", "user", int(uid), username),
        )
        db.commit()

        session.clear()
        session["user_id"] = int(uid)
        flash("Primeiro acesso configurado ✅", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("first_setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    init_db()
    ensure_seed_data()
    db = get_db()

    # Primeiro acesso: abre a tela para a clínica escolher login e senhas.
    # Também funciona quando o sistema veio com o usuário padrão admin.
    if first_setup_pending():
        return redirect(url_for("auth.first_setup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Login inválido.", "danger")
            return render_template("login.html")
        session.clear()
        session["user_id"] = int(user["id"])
        log_action("login", "user", int(user["id"]), username)
        db.commit()
        return redirect(url_for("dashboard.index"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    db = get_db()
    settings = get_settings_map()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    role = user["role"] if user and "role" in user.keys() else "admin"

    if request.method == "POST":
        action = request.form.get("action", "password")

        if action == "password":
            current = request.form.get("current_password", "")
            new1 = request.form.get("new_password", "")
            new2 = request.form.get("new_password2", "")
            if not check_password_hash(user["password_hash"], current):
                flash("Senha atual incorreta.", "danger")
            elif len(new1) < 6:
                flash("Senha nova muito curta. Use pelo menos 6 caracteres.", "danger")
            elif new1 != new2:
                flash("As senhas não conferem.", "danger")
            else:
                db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new1), session["user_id"]))
                log_action("change_password", "user", session["user_id"])
                db.commit()
                flash("Senha atualizada ✅", "success")
                return redirect(url_for("auth.settings"))

        elif action == "clinic" and role == "admin":
            for key in ["clinic_name", "clinic_phone", "clinic_address", "clinic_email", "clinic_cnpj", "clinic_responsible"]:
                set_setting(key, request.form.get(key, "").strip())
            log_action("update_clinic_settings", "settings")
            db.commit()
            flash("Dados da clínica atualizados ✅", "success")
            return redirect(url_for("auth.settings"))

        elif action == "integrations" and role == "admin":
            for key in ["finance_password", "asaas_env", "asaas_api_key", "whatsapp_reminder_template", "whatsapp_charge_template", "birthday_template"]:
                set_setting(key, request.form.get(key, "").strip())
            log_action("update_integrations", "settings")
            db.commit()
            flash("Financeiro, WhatsApp e Asaas atualizados ✅", "success")
            return redirect(url_for("auth.settings"))

        elif action == "new_user" and role == "admin":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            new_role = request.form.get("role", "recepcao")
            if new_role not in ROLE_LABELS:
                new_role = "recepcao"
            if not username or len(password) < 6:
                flash("Informe usuário e senha com pelo menos 6 caracteres.", "danger")
            else:
                try:
                    db.execute("INSERT INTO users(username, password_hash, role) VALUES(?,?,?)", (username, generate_password_hash(password), new_role))
                    new_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                    log_action("create_user", "user", int(new_id), username)
                    db.commit()
                    flash("Usuário criado ✅", "success")
                    return redirect(url_for("auth.settings"))
                except Exception:
                    flash("Esse nome de usuário já existe.", "danger")

        elif action == "delete_user" and role == "admin":
            uid = request.form.get("user_id", type=int)
            if uid == session.get("user_id"):
                flash("Você não pode remover o próprio usuário logado.", "warning")
            elif uid:
                db.execute("DELETE FROM users WHERE id=?", (uid,))
                log_action("delete_user", "user", uid)
                db.commit()
                flash("Usuário removido.", "info")
                return redirect(url_for("auth.settings"))

        else:
            flash("Ação não permitida para seu usuário.", "warning")

    settings = get_settings_map()
    users = db.execute("SELECT id, username, role, created_at FROM users ORDER BY username COLLATE NOCASE").fetchall()
    recent_logs = db.execute(
        "SELECT l.*, u.username FROM audit_log l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 20"
    ).fetchall()
    return render_template(
        "settings.html",
        settings=settings,
        users=users,
        recent_logs=recent_logs,
        role_labels=ROLE_LABELS,
    )


@bp.route("/settings/backup")
@login_required
@role_required("admin", "financeiro")
def download_backup():
    db_path = Path(current_app.config["DB_PATH"])
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, arcname=db_path.name)
        upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"))
        if upload_root.exists():
            for file in upload_root.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=str(Path("uploads") / file.relative_to(upload_root)))
        zf.writestr("LEIA-ME-BACKUP.txt", "Backup do sistema Eduarda Imbelloni Clínica Especializada. Guarde este arquivo com segurança.\n")
    mem.seek(0)
    log_action("download_backup", "backup")
    get_db().commit()
    return send_file(mem, as_attachment=True, download_name=f"backup_eduarda_clinica_{stamp}.zip", mimetype="application/zip")
