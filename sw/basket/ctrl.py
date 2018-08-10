from socket import gethostname, gethostbyname
from threading import Event
from time import sleep
import json
from flask import Blueprint, render_template, redirect, request, url_for, session
from .utils import ip_addresses, get_temp, get_ble_addr, hashabledict, with_query_string
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


@bp.route("/bluetooth/restart")
@login_required
def bluetooth_restart():
    if has_uwsgi:
        uwsgi.mule_msg(b"bt restart")
    return redirect(url_for(".bluetooth"))


if has_uwsgi:

    def init_ws(app):
        bt_changed = Event()
        uwsgi.register_signal(1, "workers", lambda x: bt_changed.set())

        @ws.route("/bluetooth/ws")
        def bluetooth_ws(ws):
            with app.request_context(ws.environ):
                if not session.get("logged_in"):
                    return redirect(with_query_string(url_for('auth.login'), "next", request.url))
                bt_changed.clear()
                db = get_db()
                try:
                    while True:
                        old = set(filter(lambda x: not x["hostdev"], map(hashabledict, db.execute("SELECT * FROM bluetooth").fetchall())))
                        while not bt_changed.wait(1):
                            ws.recv_nb()
                        new = set(filter(lambda x: not x["hostdev"], map(hashabledict, db.execute("SELECT * FROM bluetooth").fetchall())))
                        bt_changed.clear()
                        if len(new) == 0:
                            ws.send(json.dumps({"action": "clear"}))
                        else:
                            for device in old - new:
                                ws.send(json.dumps(dict(**device, action="del")))
                            for device in new - old:
                                ws.send(json.dumps(dict(**device, action="add")))
                except (SystemError, OSError):
                    pass
