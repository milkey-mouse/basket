from flask import Blueprint, redirect, url_for
from .auth import login_required

bp = Blueprint("ctrl", __name__)


@bp.route("/")
@login_required
def index():
    return "Hello World!"
