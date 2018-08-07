from socket import gethostname, gethostbyname
from flask import Blueprint, render_template, redirect, url_for
from .utils import ip_addresses, get_temp, get_ble_addr
from .auth import login_required
from .db import get_db

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False

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
    sysinfo = [
        ("Hostname", gethostname()),
        ("IP address", ip_addresses()),
        ("Host Bluetooth address", get_ble_addr()),
        ("CPU temp", get_temp()),
    ]
    return render_template("ctrl/index.html", checklist=checklist, sysinfo=sysinfo)


@bp.route("/bt")
def bt():
    return redirect(url_for(".bluetooth"))


@bp.route("/bluetooth")
@login_required
def bluetooth():
    devices = get_db().execute("SELECT * FROM bluetooth WHERE hostdev = 0").fetchall()
    devices.sort(key=lambda x: x["rssi"] if x["rssi"] is not None else float("-inf"), reverse=True)
    return render_template("ctrl/bluetooth.html", devices=devices)


if has_uwsgi:
    @bp.route("/debug/reload")
    @login_required
    def reload_server():
        uwsgi.reload()
        return redirect(url_for("index"))
