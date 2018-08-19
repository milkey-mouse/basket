from socket import gethostname, gethostbyname
from contextlib import suppress
from threading import Event
from struct import pack
from time import sleep
from uuid import UUID
import json
from flask import Blueprint, render_template, redirect, request, url_for, session
from .utils import ip_addresses, get_temp, get_ble_addr, hashabledict, with_query_string, ping_worker
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
    checklist = {
        "ctrl.bluetooth": ping_worker(),
        "Calibration": True,
        "Camera": False,
        "Streamer": True,
    }
    sysinfo = {
        "CPU temp": get_temp(),
        "Host Bluetooth address": get_ble_addr(),
        "Hostname": gethostname(),
        "IP address": ip_addresses(),
    }
    return render_template("ctrl/index.html", checklist=sorted(checklist.items()), sysinfo=sorted(sysinfo.items()))


@bp.route("/bt")
def bt():
    return redirect(url_for(".bluetooth"))


@bp.route("/bluetooth")
@login_required
def bluetooth():
    devices = get_db().execute("SELECT * FROM bluetooth WHERE hostdev = 0").fetchall()
    devices.sort(key=lambda x: x["rssi"] if x["rssi"] is not None else float("-inf"), reverse=True)
    return render_template("ctrl/bluetooth.html", devices=devices)


@bp.route("/control")
@login_required
def control():
    devices = get_db().execute("SELECT * FROM bluetooth WHERE connected = 1 AND hostdev = 0").fetchall()
    return render_template("ctrl/control.html", devices=devices)


@bp.route("/bluetooth/restart")
@login_required
def bluetooth_restart():
    if has_uwsgi:
        uwsgi.mule_msg(b"bt restart", 1)
    return redirect(url_for(".bluetooth"))


@bp.route("/connect/<macaddr>")
@login_required
def connect(macaddr):
    if has_uwsgi:
        uwsgi.mule_msg(b"bt connect " + macaddr.upper().encode(), 1)
    return render_template("ctrl/connect.html", macaddr=macaddr, connecting=True)


@bp.route("/disconnect/<macaddr>")
@login_required
def disconnect(macaddr):
    if has_uwsgi:
        uwsgi.mule_msg(b"bt disconnect " + macaddr.upper().encode(), 1)
    return render_template("ctrl/connect.html", macaddr=macaddr, connecting=False)


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
                with suppress(SystemError, OSError):
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

        @ws.route("/control/ws")
        def control_ws(ws):
            uwsgi.mule_msg(b"bt scan on", 1)
            try:
                with app.request_context(ws.environ):
                    if not session.get("logged_in"):
                        return redirect(with_query_string(url_for('auth.login'), "next", request.url))
                with suppress(SystemError, OSError):
                    for raw_msg in iter(ws.receive, None):
                        msg = json.loads(raw_msg.decode())
                        #for mule, dev in zip(cycle(range(1, NUM_BT_WORKERS+1)), msg["devices"]):
                        for dev in msg["devices"]:
                            uwsgi.mule_msg(b"bt send " + dev.encode() + b" " + pack("B", msg["angle"]))
            finally:
                uwsgi.mule_msg(b"bt scan off", 1)
