from operator import itemgetter
from flask import Blueprint, render_template, redirect, url_for
from .auth import login_required

bp = Blueprint("ctrl", __name__)


@bp.route("/")
@login_required
def index():
    checklist = [
        ("Bluetooth", True),
        ("Camera", False),
        ("Streamer", True),
        ("Calibration", True)
    ]
    return render_template("ctrl/index.html", checklist=checklist)

@bp.route("/bt")
def bt():
    return redirect(url_for(".bluetooth"))

@bp.route("/bluetooth")
def bluetooth():
    return render_template("ctrl/bluetooth.html", devices=[{"macaddr": "12::34", "name": "meme"}, {"macaddr": "34::56", "name": None}])
