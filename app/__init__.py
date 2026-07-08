# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from flask import Flask, session, g
from .db import close_db
from .auth import bp as auth_bp
from .dashboard import bp as dashboard_bp
from .patients import bp as patients_bp
from .finance import bp as finance_bp
from .agenda import bp as agenda_bp
from .birthdays import bp as birthdays_bp
from .crm import bp as crm_bp

def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
    app.config["DB_PATH"] = os.environ.get("DB_PATH", os.path.join(app.instance_path, "eduarda_imbelloni.db"))

    # Informações da clínica (para impressão de orçamento/anamnese etc.)
    # Pode personalizar no Render/PC via variáveis de ambiente.
    app.config["CLINIC_NAME"] = os.environ.get("CLINIC_NAME", "Eduarda Imbelloni Clínica Especializada")
    app.config["CLINIC_PHONE"] = os.environ.get("CLINIC_PHONE", "")
    app.config["CLINIC_ADDRESS"] = os.environ.get("CLINIC_ADDRESS", "")
    app.config["CLINIC_EMAIL"] = os.environ.get("CLINIC_EMAIL", "")
    app.config["CLINIC_RESPONSIBLE"] = os.environ.get("CLINIC_RESPONSIBLE", "")
    app.config["CLINIC_CNPJ"] = os.environ.get("CLINIC_CNPJ", "")
    app.config["ASAAS_API_KEY"] = os.environ.get("ASAAS_API_KEY", "")
    app.config["ASAAS_ENV"] = os.environ.get("ASAAS_ENV", "sandbox")
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "/data/uploads")
    app.config["APP_VERSION"] = "App Premium V30"

    # Proteção extra do Financeiro (senha separada do login)
    # Pode alterar via variável de ambiente FINANCE_PASSWORD (ou FINANCE_PASS)
    # Se FINANCE_PASSWORD/FINANCE_PASS estiver definido no Coolify, ele tem prioridade.
    # Se não estiver, usa a senha salva no próprio sistema, escolhida no primeiro acesso.
    app.config["FINANCE_PASSWORD"] = os.environ.get("FINANCE_PASSWORD") or os.environ.get("FINANCE_PASS") or ""

    @app.context_processor
    def inject_flags():
        # Permite usar {{ finance_unlocked }} em qualquer template
        return {"finance_unlocked": bool(session.get("finance_unlocked"))}

    @app.context_processor
    def inject_clinic_info():
        # Permite usar {{ CLINIC_NAME }}, {{ CLINIC_PHONE }}, etc. em qualquer template.
        # Primeiro usa variáveis do Coolify. Se estiverem vazias, usa Configurações do sistema.
        settings = {}
        try:
            from .db import get_db
            rows = get_db().execute("SELECT key, value FROM app_settings").fetchall()
            settings = {r["key"]: (r["value"] or "") for r in rows}
        except Exception:
            settings = {}

        def pick(config_key, setting_key, default=""):
            return app.config.get(config_key) or settings.get(setting_key) or default

        role = ""
        try:
            role = g.user["role"] if getattr(g, "user", None) and "role" in g.user.keys() else ""
        except Exception:
            role = ""

        return {
            "CLINIC_NAME": pick("CLINIC_NAME", "clinic_name", "Eduarda Imbelloni Clínica Especializada"),
            "CLINIC_PHONE": pick("CLINIC_PHONE", "clinic_phone", ""),
            "CLINIC_ADDRESS": pick("CLINIC_ADDRESS", "clinic_address", ""),
            "CLINIC_EMAIL": pick("CLINIC_EMAIL", "clinic_email", ""),
            "CLINIC_RESPONSIBLE": pick("CLINIC_RESPONSIBLE", "clinic_responsible", ""),
            "CLINIC_CNPJ": pick("CLINIC_CNPJ", "clinic_cnpj", ""),
            "ASAAS_ENV": app.config.get("ASAAS_ENV") or settings.get("asaas_env", "sandbox"),
            "APP_VERSION": app.config.get("APP_VERSION", "App Premium V30"),
            "current_role": role,
        }

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(birthdays_bp)
    app.register_blueprint(crm_bp)

    # DB teardown
    app.teardown_appcontext(close_db)


    return app

# Compatibilidade Render (quando Start Command está como gunicorn app:app)
app = create_app()
