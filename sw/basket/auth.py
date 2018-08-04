import os
import functools
from flask import Blueprint, current_app, session, redirect, request, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash
from .utils import with_query_string

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("logged_in"):
            return redirect(with_query_string(url_for('auth.login'), "next", request.url))
        return view(**kwargs)

    return wrapped_view


@bp.route("/changepw", methods=("GET", "POST"))
@login_required
def changepw():
    error = None
    if request.method == "POST":
        oldpw = request.form["oldpw"]
        newpw = request.form["newpw"]
        newpw2 = request.form["newpw2"]

        if not oldpw:
            error = "Old password is required."
        elif not newpw or len(newpw) == 0:
            error = "New password is required."
        elif not newpw2:
            error = "Please repeat the new password."
        elif newpw != newpw2:
            error = "New passwords do not match."
        else:
            with current_app.open_instance_resource("password", "r") as f:
                hash = f.read()
            if not check_password_hash(hash, oldpw):
                error = "Incorrect old password."

        if error is None:
            with current_app.open_instance_resource("password.tmp", "w") as f:
                f.write(generate_password_hash(newpw))

            os.rename(
                os.path.join(current_app.instance_path, "password.tmp"),
                os.path.join(current_app.instance_path, "password")
            )

            # log everyone out by invalidating the signature of old session cookies
            current_app.secret_key = os.urandom(32)
            return redirect(url_for(".login"))

    return render_template("auth/changepw.html", error=error)


@bp.route("/login", methods=("GET", "POST"))
def login():
    error = None
    if request.method == "POST":
        password = request.form["password"]

        if not password:
            error = "Password is required."
        elif len(password) == 0:
            error = "Enter a password."
        else:
            with current_app.open_instance_resource("password", "r") as f:
                hash = f.read()

            if not check_password_hash(hash, password):
                error = "Nope."

        if error is None:
            session["logged_in"] = True
            return redirect(request.args.get("next", url_for("index")))
    return render_template("auth/login.html", placeholder=error)


@bp.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))
