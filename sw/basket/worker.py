import sqlite3
import atexit
import random
import time
import sys
from flask.cli import with_appcontext
from flask import current_app, g
import click

has_bluetooth = True
try:
    import Adafruit_BluefruitLE as able
    from Adafruit_BluefruitLE.services import UART
except ImportError:
    has_bluetooth = False


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
    db = sqlite3.connect(
        worker.db_path,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row

    try:
        db.execute("DELETE FROM bluetooth")
        db.commit()

        worker.ble.clear_cached_data()
        adapters = worker.ble.list_adapters()

        if len(adapters) == 0:
            print("No Bluetooth adapters found!", file=sys.stderr)
            return 1

        adapter = adapters[0]
        adapter.macaddr = adapter._props.Get(able.bluez_dbus.adapter._INTERFACE, "Address")
        db.execute("REPLACE INTO bluetooth VALUES(?, ?, NULL, 1)", (adapter.macaddr, adapter.name))
        db.commit()

        # make the name of the device significant (we want to notice the difference
        # so we can update the database)
        able.interfaces.Device.__hash__ = lambda self: hash((self.id, self.name, self.rssi))

        adapter.power_on()
        adapter.start_scan()
        atexit.register(adapter.stop_scan)
        atexit.register(adapter.power_off)

        known = set()
        while True:
            #found = set(UART.find_devices())
            found = set(worker.ble.list_devices())
            new = found - known
            for device in new:
                db.execute("REPLACE INTO bluetooth VALUES(?, ?, ?, 0)", (device.id, device.name, device.rssi))
            db.commit()
            time.sleep(1)
    finally:
        try:
            db.execute("DELETE FROM bluetooth WHERE hostDev = 1")
            db.commit()
        except:
            pass
        db.close()


@click.command("run-worker")
@with_appcontext
def run_worker():
    click.echo("Worker running.")
    worker.db_path = current_app.config["DATABASE"]
    worker.ble = able.get_provider()
    worker.ble.initialize()
    worker.ble.run_mainloop_with(worker)


def init_app(app):
    app.cli.add_command(run_dummy_worker)
    if has_bluetooth:
        app.cli.add_command(run_worker)
