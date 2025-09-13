# app/auth/routes.py
# ------------------
# Sign-up, log-in, log-out views wrapped in an `auth` blueprint.

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from app.models import db, User

bp = Blueprint("auth", __name__, url_prefix="/auth")

# ────────────────────────────────────────────────────────────────
@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        uname = request.form["username"].lower()
        email = request.form["email"].lower()
        pw    = request.form["password"]

        # Duplicate check
        if User.query.filter(
            (User.username == uname) | (User.email == email)
        ).first():
            flash("Username or email already taken")
            return redirect(url_for("auth.register"))

        # Create user
        u = User(username=uname, email=email)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()

        flash("Account created — log in below")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ────────────────────────────────────────────────────────────────
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        uname = request.form["username"].lower()
        pw    = request.form["password"]

        u = User.query.filter_by(username=uname).first()
        if u and u.check_password(pw):
            login_user(u)
            return redirect(url_for("main.home"))

        flash("Invalid username or password")

    return render_template("login.html")


# ────────────────────────────────────────────────────────────────
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
