from traceback import print_exc
from time import sleep
import sqlite3
import atexit
import random
import sys
import os
from click import command
from . import create_base

has_bluetooth = True
try:
    import Adafruit_BluefruitLE as able
    from Adafruit_BluefruitLE.services import UART
    from dbus.exceptions import DBusException
except ImportError:
    has_bluetooth = False

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False

if has_bluetooth:
    ble = able.get_provider()

if has_uwsgi:
    from threading import Thread
    import queue

    q = queue.Queue()


def get_dummy_mac():
    return (":".join(["{:02x}", ] * 6)).format(*os.urandom(6))


def dummy_worker():
    db = sqlite3.connect(
        dummy_worker.db_path,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row

    try:
        db.execute("DELETE FROM bluetooth")
        db.execute("INSERT INTO bluetooth VALUES(?, ?, NULL, 1)",
            (get_dummy_mac(), "Dummy Adapter"))
        db.commit()
        if has_uwsgi:
            uwsgi.signal(1)


        for i in range(0, 10):
            sleep(3)
            db.execute("INSERT INTO bluetooth VALUES(?, ?, ?, 0)",
                       (get_dummy_mac(), random.choice(("Egg", None)), random.randint(-128, 0)))
            db.commit()
            if has_uwsgi:
                uwsgi.signal(1)

        while True:
            sleep(1)
    finally:
        try:
            db.execute("DELETE FROM bluetooth WHERE hostDev = 1")
            db.commit()
        except:
            pass
        db.close()


def run_dummy_worker():
    print("Dummy worker running.")
    dummy_worker.db_path = create_base().config["DATABASE"]
    dummy_worker()


def push_mule_events():
    for msg in iter(uwsgi.mule_get_msg, b"exit"):
        q.put(msg.decode().split())


def worker():
    db = sqlite3.connect(
        worker.db_path,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row

    try:
        db.execute("DELETE FROM bluetooth")
        db.commit()
        if has_uwsgi:
            uwsgi.signal(1)

        try:
            ble.clear_cached_data()
        except DBusException:
            pass
        adapters = ble.list_adapters()

        if len(adapters) == 0:
            print("No Bluetooth adapters found!", file=sys.stderr)
            return 1

        adapter = adapters[0]
        adapter.macaddr = adapter._props.Get(
            able.bluez_dbus.adapter._INTERFACE,
            "Address"
        )
        db.execute("REPLACE INTO bluetooth VALUES(?, ?, NULL, 1)",
            (adapter.macaddr, adapter.name))
        db.commit()

        # TODO: upstream this
        def prop_suppress(prop):
            old = prop.fget
            def new(self):
                try:
                    return old(self)
                except DBusException as e:
                    if e.get_dbus_name() != "org.freedesktop.DBus.Error.InvalidArgs":
                        raise
                return None
            return prop.getter(new)


        bzd = able.bluez_dbus.device.BluezDevice
        bzd.name = prop_suppress(bzd.name)
        bzd.rssi = prop_suppress(bzd.rssi)

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
            found = set(ble.list_devices())
            new = found - known
            for device in new:
                db.execute("REPLACE INTO bluetooth VALUES(?, ?, ?, 0)",
                    (device.id, device.name, device.rssi))
            db.commit()
            if has_uwsgi:
                uwsgi.signal(1)
                try:
                    for msg in iter(q.get_nowait, None):
                        if msg[0] == "soft-restart":
                            worker()
                except queue.Empty:
                    pass
            sleep(1)
    finally:
        try:
            db.execute("DELETE FROM bluetooth WHERE hostDev = 1")
            db.commit()
        except:
            pass
        db.close()


def run_worker():
    if not has_bluetooth:
        print("Bluefruit LE library is not installed; Bluetooth worker cannot run.")
        if has_uwsgi:
            while True:
                sleep(1)
        return
    print("Worker running.")
    worker.db_path = create_base().config["DATABASE"]
    if has_uwsgi:
        t = Thread(target=push_mule_events)
        t.start()
    try:
        ble.initialize()
        ble.run_mainloop_with(worker)
    except Exception:
        print_exc()  # because uWSGI/Flask won't do it for us...
    finally:
        if has_uwsgi:
            uwsgi.mule_msg(b"exit", uwsgi.mule_id())
            t.join()


def init_app(app):
    app.cli.add_command(command("run-dummy-worker")(run_dummy_worker))
    if has_bluetooth:
        app.cli.add_command(command("run-worker")(run_worker))
