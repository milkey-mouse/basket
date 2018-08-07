from selectors import DefaultSelector, EVENT_READ
from io import TextIOWrapper
from signal import SIGINT
import subprocess
import random
import fcntl
import time
import sys
import os
import re
from flask.cli import with_appcontext
from flask import current_app, g
import click
from .utils import static_var
from .db import get_db


def get_dummy_mac():
    return (":".join(["{:02x}", ] * 6)).format(*os.urandom(6))


def dummy_worker():
    db = get_db()

    db.execute("DELETE FROM bluetooth")
    db.execute("INSERT INTO bluetooth VALUES(?, Test, NULL, 1)", (get_dummy_mac(),))
    db.commit()

    for i in range(0, 10):
        time.sleep(3)
        db.execute("INSERT INTO bluetooth VALUES(?, ?, NULL, 0)",
                   (get_dummy_mac(), random.choice(("Egg", None))))
        db.commit()


@click.command("run-dummy-worker")
@with_appcontext
def run_dummy_worker():
    click.echo("Dummy worker running.")
    dummy_worker()


def worker():
    db = get_db()
    db.execute("DELETE FROM bluetooth")
    db.commit()

    cmd = current_app.config["COMMAND_PREFIX"] + ["bluetoothctl"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, stdin=subprocess.PIPE, bufsize=0, start_new_session=True)
    fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
    fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    @static_var("data", b"")
    @static_var("ansi_escape", re.compile(rb"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]"))
    def expect(sentinel, *callbacks, timeout=None):
        timer = 0
        with DefaultSelector() as sel:
            sel.register(p.stdout, EVENT_READ)
            while p.poll() is None or len(sel.select(0)) > 0:
                chunk = p.stdout.read()
                if chunk is None or len(chunk) == 0:
                    if timeout is not None:
                        timer += 1
                        if timer > timeout:
                            raise subprocess.TimeoutExpired(cmd, timeout)
                    time.sleep(1)
                    continue
                timer = 0
                expect.data += chunk
                while True:
                    @static_var("none", len(expect.data) + 1)
                    def data_idx(x):
                        try:
                            return expect.data.index(x)
                        except ValueError:
                            # return a max value
                            return data_idx.none

                    idx = min(map(data_idx, b"\r\n"))
                    if idx == data_idx.none:
                        break

                    line = expect.ansi_escape.sub(b"", expect.data[:idx]).decode()
                    expect.data = expect.data[idx+1:]
                    if line == sentinel:
                        return
                    elif line.strip() == "":
                        continue

                    for callback in callbacks:
                        callback(line)

                if sentinel is None:
                    continue
                try:
                    encoded_sentinel = sentinel.encode()
                    escaped = expect.ansi_escape.sub(b"", expect.data)
                    idx = escaped.index(encoded_sentinel)
                    expect.data = escaped[idx+len(encoded_sentinel):]
                    return
                except ValueError:
                    pass

        if sentinel is not None:
            raise EOFError

    def update_controllers(line):
        try:
            evt, type, macaddr, name, *extra = line.split(" ")
            if type != "Controller": raise ValueError
        except ValueError:
            return
        if evt == "[NEW]":
            print("adding controller", macaddr)
            if len(extra) > 0:
                name += " " + " ".join(extra)
                if name.endswith(" (default)"):
                    name = name[:-len(" (default)")]
            db.execute("REPLACE INTO bluetooth VALUES(?, ?, NULL, 1)", (macaddr, name))
        elif evt == "[DEL]":
            print("deleting controller", macaddr)
            db.execute("DELETE FROM bluetooth WHERE macaddr = ?", (macaddr,))
        else:
            return
        db.commit()

    def update_devices(line):
        try:
            evt, type, macaddr, *extra = line.split(" ")
            if type != "Device": raise ValueError
        except ValueError:
            return
        if evt == "[NEW]":
            name = " ".join(extra) if len(extra) > 0 else None
            print("adding device", macaddr)
            db.execute("REPLACE INTO bluetooth VALUES(?, ?, NULL, 0)", (macaddr, name))
        elif evt == "[CHG]" and len(extra) > 0 and extra[0] == "Name:":
            name = " ".join(extra[1:])
            print("updating device", macaddr, "name to", name)
            db.execute("UPDATE bluetooth SET name = ? WHERE macaddr = ?", (name, macaddr))
        elif evt == "[CHG]" and len(extra) == 2 and extra[0] == "RSSI:":
            rssi = int(extra[1])
            print("updating device", macaddr, "RSSI to", rssi)
            db.execute("UPDATE bluetooth SET rssi = ? WHERE macaddr = ?", (rssi, macaddr))
        elif evt == "[DEL]":
            print("deleting device", macaddr)
            db.execute("DELETE FROM bluetooth WHERE macaddr = ?", (macaddr,))
        else:
            return
        db.commit()

    def update_version(line):
        if line.startswith("Version "):
            version = line.split(" ")[1]
            print("setting version to", version)
            db.execute("UPDATE singleton SET bluezVer = ?", (version,))
            db.commit()

    stdin = TextIOWrapper(p.stdin, "utf-8", write_through=True)
    try:
        expect("[bluetooth]# ", print, update_controllers, update_devices)
        print("version", file=stdin)
        expect("[bluetooth]# ", print, update_controllers, update_devices, update_version)
        print("power on", file=stdin)
        expect("[bluetooth]# ", print, update_controllers, update_devices, update_version)
        print("scan on", file=stdin)
        try:
            expect(None, print, update_controllers, update_devices, update_version)
        except KeyboardInterrupt:
            print("scan off", file=stdin)
            expect("[bluetooth]# ", timeout=1)
            print("power off", file=stdin)
            expect("[bluetooth]# ", timeout=1)
    finally:
        if p.poll() is None:
            print("cleaning up")
            print("exit", file=stdin)
            try:
                expect(None, update_controllers, update_devices, timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()


@click.command("run-worker")
@with_appcontext
def run_worker():
    click.echo("Worker running.")
    worker()


def init_app(app):
    app.cli.add_command(run_dummy_worker)
    app.cli.add_command(run_worker)
