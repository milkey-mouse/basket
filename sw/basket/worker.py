from functools import partial, lru_cache
from itertools import chain, product
from contextlib import suppress
from traceback import print_exc
from time import sleep
from uuid import UUID
import operator
import sqlite3
import atexit
import random
import sys
import os
from click import command
from .utils import mule_msg_iter
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
    from uuid import UUID

    SERVO_SERVICE_UUID = UUID("00000420-0000-1000-8000-00805F9B34FB")
    SERVO_ANGLE_CHAR_UUID = UUID("00001337-0000-1000-8000-00805F9B34FB")

    ble = able.get_provider()

    # TODO: upstream this
    def prop_suppress(prop):
        old = prop.fget
        def new(self):
            try:
                return old(self)
            except DBusException as e:
                if e.get_dbus_name() not in ("org.freedesktop.DBus.Error.InvalidArgs", "org.freedesktop.DBus.Error.UnknownObject"):
                    raise
            return None
        return prop.getter(new)

    bzd = able.bluez_dbus.device.BluezDevice
    bzd.name = prop_suppress(bzd.name)
    bzd.rssi = prop_suppress(bzd.rssi)

    # don't upstream these
    bzd.id = prop_suppress(bzd.id)
    bzd.is_connected = prop_suppress(bzd.is_connected)


    def prop_to_type(prop, type):
        old = prop.fget
        return prop.getter(lambda self: type(old(self)))

    bzd.advertised = prop_to_type(bzd.advertised, tuple)
    #bzd.id = prop_to_type(bzd.id, UUID)

    # make the name of the device significant (we want to notice the difference
    # so we can update the database)
    able.interfaces.Device.__hash__ = lambda self: hash((self.id, self.name, self.rssi, self.is_connected))


def get_dummy_mac():
    return (":".join(["{:02x}", ] * 6)).format(*os.urandom(6)).upper()


def dummy_worker():
    db = sqlite3.connect(
        dummy_worker.db_path,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row

    try:
        db.execute("DELETE FROM bluetooth")
        db.execute("INSERT INTO bluetooth VALUES(?, ?, NULL, 1, 1)",
            (get_dummy_mac(), "Dummy Adapter"))
        db.commit()
        if has_uwsgi:
            uwsgi.signal(1)


        for i in range(0, 10):
            db.execute("INSERT INTO bluetooth VALUES(?, ?, ?, 0, 0)",
                       (get_dummy_mac(), random.choice(("Egg.", None)), random.randint(-128, 0)))
            db.commit()
            wait = 1 + random.random() * 2
            if has_uwsgi:
                uwsgi.signal(1)
                for raw_msg in filter(lambda x: x.startswith(b"bt "), mule_msg_iter(timeout)):
                    msg = raw_msg.split(b" ")[1:]
                    if msg == [b"restart"]:
                        return
                    elif msg == [b"ping"]:
                        uwsgi.signal(3)  # pong
                    elif len(msg) == 2 and msg[0] == b"connect":
                        sleep(1)
                        db.execute("UPDATE bluetooth SET connected = 1 WHERE macaddr = ?", (msg[1].decode(),))
                        db.commit()
                    elif len(msg) == 2 and msg[0] == b"disconnect":
                        sleep(1)
                        db.execute("UPDATE bluetooth SET connected = 0 WHERE macaddr = ?", (msg[1].decode(),))
                        db.commit()
            else:
                sleep(wait)
        while True:
            if has_uwsgi:
                for raw_msg in filter(lambda x: x.startswith(b"bt "), mule_msg_iter(1)):
                    msg = raw_msg.split(b" ")[1:]
                    if msg == [b"restart"]:
                        return
                    elif msg == [b"ping"]:
                        uwsgi.signal(3)  # pong
                    elif len(msg) == 2 and msg[0] == b"connect":
                        sleep(1)
                        db.execute("UPDATE bluetooth SET connected = 1 WHERE macaddr = ?", (msg[1].decode(),))
                        db.commit()
                    elif len(msg) == 2 and msg[0] == b"disconnect":
                        sleep(1)
                        db.execute("UPDATE bluetooth SET connected = 0 WHERE macaddr = ?", (msg[1].decode(),))
                        db.commit()
            else:
                sleep(1)
    finally:
        with suppress(Exception):
            db.execute("DELETE FROM bluetooth WHERE hostDev = 1")
            db.commit()
        db.close()


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

        if uwsgi.mule_id() == 1:
            with suppress(DBusException):
                ble.clear_cached_data()

        adapters = ble.list_adapters()

        if len(adapters) == 0:
            print("No Bluetooth adapters found!", file=sys.stderr)
            return 1

        adapter = adapters[0]
        adapter.macaddr = adapter._props.Get(
            able.bluez_dbus.adapter._INTERFACE,
            "Address"
        )

        if uwsgi.mule_id() == 1:
            db.execute("REPLACE INTO bluetooth VALUES(?, ?, NULL, 1, 1)",
                (adapter.macaddr, adapter.name))
            db.commit()

            adapter.power_on()
            adapter.start_scan()
            #atexit.register(partial(adapter.stop_scan, 5))
            #atexit.register(adapter.power_off)

        scan = True
        known = set()

        @lru_cache(16)
        def get_dev_by_id(macaddr):
            try:
                return next(filter(lambda x: x.id == macaddr, known))
            except StopIteration:
                raise KeyError

        while True:
            if scan:
                found = set(ble.list_devices())
                new = found - known
                known -= set(filter(lambda x: x[0].id == x[1].id, product(new, known)))
                for device in new:
                    device.svc = None
                    device.angle = None
                    db.execute("REPLACE INTO bluetooth VALUES(?, ?, ?, ?, 0)",
                        (device.id, device.name, device.rssi, device.is_connected))
                db.commit()
                known.update(new)
                if has_uwsgi and len(new) > 0:
                    uwsgi.signal(1)
            if has_uwsgi:
                for raw_msg in filter(lambda x: x.startswith(b"bt "), mule_msg_iter(5)):
                    print("worker {} processing".format(uwsgi.mule_id()), raw_msg)
                    msg = raw_msg.split(b" ")[1:]
                    if msg == [b"restart"]:
                        return
                    elif msg == [b"ping"]:
                        uwsgi.signal(3)  # pong
                    elif len(msg) == 2 and msg[0] == [b"scan"]:
                        with suppress(KeyError):
                            scan = {b"on": True, b"off": False}[msg[1]]
                    elif len(msg) == 2 and msg[0] == b"connect":
                        macaddr = msg[1].decode()
                        with suppress(RuntimeError, KeyError):
                            get_dev_by_id(macaddr).connect(0)
                    elif len(msg) == 2 and msg[0] == b"disconnect":
                        macaddr = msg[1].decode()
                        with suppress(RuntimeError, KeyError):
                            get_dev_by_id(macaddr).disconnect(0)
                    elif len(msg) >= 3 and msg[0] == b"send":
                        if uwsgi.mule_id() == 1:
                            scan = False
                        macaddr = msg[1].decode()
                        try:
                            dev = get_dev_by_id(macaddr)
                        except KeyError:
                            print("cache miss")
                            get_dev_by_id.cache_clear()
                            continue

                        if not dev.is_connected:
                            continue

                        if dev.svc is None:
                            dev.svc = dev.find_service(SERVO_SERVICE_UUID)
                        if dev.svc is None:
                            continue

                        if dev.angle is None:
                            dev.angle = dev.svc.find_characteristic(SERVO_ANGLE_CHAR_UUID)
                        if dev.angle is None:
                            continue

                        try:
                            dev.angle.write_value(b" ".join(msg[2:]))
                        except DBusException as e:
                            # multiple cores may be trying to write to the characteristic
                            if e.get_dbus_name() != "org.bluez.Error.InProgress":
                                raise
            else:
                sleep(1)
            #for dev in new:
            #    if dev.is_connected and not dev.discover([SERVO_SERVICE_UUID], [SERVO_ANGLE_CHAR_UUID], 10):
            #        dev.disconnect(5)
    finally:
        with suppress(Exception):
            db.execute("DELETE FROM bluetooth WHERE hostDev = 1")
            db.commit()
        db.close()


def run_dummy_worker():
    print("Dummy worker running.")
    dummy_worker.db_path = create_base().config["DATABASE"]
    try:
        while True:
            dummy_worker()
            if has_uwsgi:
                break
    except Exception:
        print_exc()  # because uWSGI/Flask won't do it for us...


def run_worker():
    if not has_bluetooth:
        print("Bluefruit LE library is not installed; Bluetooth worker cannot run.")
        if has_uwsgi:
            while True:
                sleep(1)
        return
    print("Worker running.")
    worker.db_path = create_base().config["DATABASE"]
    try:
        ble.initialize()
        while True:
            ble.run_mainloop_with(worker)
            if has_uwsgi:
                break
    except Exception:
        print_exc()


def init_app(app):
    app.cli.add_command(command("run-dummy-worker")(run_dummy_worker))
    if has_bluetooth:
        app.cli.add_command(command("run-worker")(run_worker))
