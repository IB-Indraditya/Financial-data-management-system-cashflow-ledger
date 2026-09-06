import os
from datetime import timedelta


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-change-me"
    )

    # MySQL database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:Root64$my2sql@localhost:3360/findb"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }

    PERMANENT_SESSION_LIFETIME = timedelta(
        days=7
    )

    # Admin credentials
    SEED_ADMIN_EMAIL = os.environ.get(
        "SEED_ADMIN_EMAIL",
        "acpl002@gmail.com"
    )

    SEED_ADMIN_PASSWORD = os.environ.get(
        "SEED_ADMIN_PASSWORD",
        "Admin@123"
    )

    # Optional GenAI
    ANTHROPIC_API_KEY = os.environ.get(
        "ANTHROPIC_API_KEY",
        ""
    )

    GEMINI_API_KEY = os.environ.get(
        "GEMINI_API_KEY",
        ""
    )

    GEMINI_MODEL = os.environ.get(
        "GEMINI_MODEL",
        "gemini-3.5-flash"
    )