"""
app/__init__.py
---------------
Application factory and global extensions.
"""

import os
from flask import Flask, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# ────────────────────────────────────────────────────────────────
# Global extension objects (shared across blueprints & modules)
# ────────────────────────────────────────────────────────────────
db = SQLAlchemy()
login = LoginManager()
login.login_view = "auth.login"        # where @login_required redirects guests

# Flag: run the app without DB/auth/writes (for quick launch on Fly)
READ_ONLY = os.getenv("STARTING5_READ_ONLY", "1").lower() in ("1", "true", "yes", "y")

# ────────────────────────────────────────────────────────────────
# Factory
# ────────────────────────────────────────────────────────────────
def create_app(config_class: type = Config) -> Flask:
    """Create and configure a Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Expose flag to templates (e.g., hide submit/login buttons)
    @app.context_processor
    def inject_read_only():
        return {"STARTING5_READ_ONLY": READ_ONLY}

    # In read-only mode: block all mutating requests to Starting5 endpoints
    # (POST/PUT/PATCH/DELETE). Safe GETs still work.
    if READ_ONLY:
        @app.before_request
        def _block_mutations():
            # only protect Starting5 routes; assuming they live under /starting5 in the host app
            if request.path.startswith("/starting5") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                abort(410, description="Submissions are temporarily disabled while we migrate.")

    # ── Register blueprints ─────────────────────────────────────
    # Your existing routes blueprint
    from .main.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Auth blueprint: only load when not read-only and module exists
    if not READ_ONLY:
        try:
            from .auth.routes import bp as auth_bp
            app.register_blueprint(auth_bp)
        except ModuleNotFoundError:
            pass

    # ── DB/Auth wiring (skip entirely in read-only) ─────────────
    if not READ_ONLY:
        # Initialise extensions
        db.init_app(app)
        login.init_app(app)

        # Import models & set user_loader after db is ready
        from .models import User, GuessLog, ScoreLog  # noqa: F401

        @login.user_loader
        def load_user(user_id: str):
            """Return user object from session-stored user_id."""
            from .models import User  # local import to avoid circular refs
            return User.query.get(int(user_id))

        # Ensure tables exist (SQLite dev convenience) + safe column adds
        with app.app_context():
            db.create_all()
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            cols = [c["name"] for c in insp.get_columns("score_log")]
            if "time_taken" not in cols:
                db.session.execute(text("ALTER TABLE score_log ADD COLUMN time_taken INTEGER"))
                db.session.commit()

            cols = [c["name"] for c in insp.get_columns("guess_log")]
            if "quiz_id" not in cols:
                db.session.execute(text("ALTER TABLE guess_log ADD COLUMN quiz_id VARCHAR(120)"))
                db.session.commit()

    return app
