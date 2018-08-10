from operator import itemgetter
from threading import Event
from time import monotonic
from queue import Empty
import subprocess
import netifaces
import os
from urllib.parse import urlparse, urlunparse
from werkzeug.urls import url_decode, url_encode
from flask import current_app
from .db import get_db

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False


def with_query_string(url, key, value):
    parsed = urlparse(url)
    query_string = url_decode(parsed.query)
    query_string[key] = value
    parsed = parsed._replace(query=url_encode(query_string))
    return urlunparse(parsed)


def ip_addresses():
    addresses = set()
    for interface in netifaces.interfaces():
        ifaddresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in ifaddresses:
            for link in ifaddresses[netifaces.AF_INET]:
                # filter out loopback addresses
                if "peer" not in link and "addr" in link:
                    addresses.add(link["addr"])
    return ", ".join(addresses) if len(addresses) > 0 else "None"


def get_temp():
    try:
        try:
            # try to use the Broadcom proprietary cmd for rpi
            p = subprocess.run(["vcgencmd", "measure_temp"], stdout=subprocess.PIPE, check=True)
            temp = float(p.stdout.decode("utf-8").split("=")[1].split("'")[0])
        except FileNotFoundError:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().rstrip("\n")) / 1000.0
    except FileNotFoundError:
        return "Unknown"
    return "{} °C".format(temp)


def get_ble_addr():
    # get the bluetooth controller name from bluetoothctl worker
    qr = get_db().execute("SELECT macaddr FROM bluetooth WHERE hostdev = 1").fetchall()
    if len(qr) > 0:
        return ", ".join(map(itemgetter("macaddr"), qr))
    else:
        return "Unknown"


if has_uwsgi:
    pong = Event()
    uwsgi.register_signal(3, "workers", lambda x: pong.set())

    def ping_worker():
        pong.clear()
        uwsgi.mule_msg(b"bt ping", 1)
        return pong.wait(3)
else:
    def ping_worker():
        for pid in filter(lambda x: x.isdigit(), os.listdir("/proc")):
            try:
                with open(os.path.join("/proc", pid, "cmdline"), "rb") as cmdline:
                    args = [x.decode() for x in cmdline.read().split(b"\x00")][:-1]
                    if (len(args) == 2 and os.path.basename(args[0]) == "flask" and args[1] in ("run-worker", "run-dummy-worker")) or \
                        (len(args) == 3 and os.path.basename(args[1]) == "flask" and args[2] in ("run-worker", "run-dummy-worker")):
                        return True
            except IOError:
                continue
        return False


def queue_timeout_iter(q, timeout):
    end = monotonic() + timeout
    while True:
        timeout = max(0, end - monotonic())
        try:
            item = q.get(block=False, timeout=timeout)
            if item is not None:
                yield item
            elif timeout == 0:
                break
        except Empty:
            if timeout == 0:
                break


class hashabledict(dict):
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()
