import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    _basedir = os.path.abspath(os.path.dirname(__file__))

    # ------------------------------------------------------------------
    # Database configuration
    # ------------------------------------------------------------------
    # PythonAnywhere’s MySQL only works from inside their network—
    # so we’ll default to SQLite when FLASK_ENV=development.
    ENV = os.getenv("FLASK_ENV", "production")
    if ENV == "development":
        # local dev: use SQLite in your project folder
        SQLALCHEMY_DATABASE_URI = (
            os.environ.get("DATABASE_URL")
            or f"sqlite:///{os.path.join(_basedir, 'dev.db')}"
        )
    else:
        # production: point at your PythonAnywhere MySQL
        DB_USER     = "devgreeny"
        DB_HOST     = "devgreeny.mysql.pythonanywhere-services.com"
        DB_NAME     = os.environ.get("DB_NAME", f"{DB_USER}$default")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "ziknip-kAvni2-duhvek")

        SQLALCHEMY_DATABASE_URI = (
            os.environ.get("DATABASE_URL")
            or f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Keep MySQL connections alive and test before use
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
