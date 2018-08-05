from socket import gethostname, gethostbyname
from operator import itemgetter
from flask import Blueprint, render_template, redirect, url_for
from .utils import ip_addresses, get_temp, get_ble_addr
from .auth import login_required
from .db import get_db

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
    devices = get_db().execute("SELECT * FROM bluetooth")
    return render_template("ctrl/bluetooth.html", devices=devices)
