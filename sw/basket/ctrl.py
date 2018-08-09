from socket import gethostname, gethostbyname
from threading import Event
from time import sleep
from flask import Blueprint, render_template, redirect, request, url_for
from .utils import ip_addresses, get_temp, get_ble_addr
from .auth import login_required
from .db import get_db

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False

bp = Blueprint("ctrl", __name__)
ws = Blueprint("wsCtrl", __name__)


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
    bt_changed = Event()
    uwsgi.register_signal(1, "workers", lambda x: bt_changed.set())

    @ws.route("/bluetooth/ws")
    def bluetooth_ws(ws):
        bt_changed.clear()
        try:
            while not bt_changed.wait(1):
                ws.recv_nb()
            bt_changed.clear()
            ws.send("reload")
        except (SystemError, OSError):
            pass
