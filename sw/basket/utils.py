from operator import itemgetter
import subprocess
import netifaces
from urllib.parse import urlparse, urlunparse
from werkzeug.urls import url_decode, url_encode
from flask import current_app
from .db import get_db


def static_var(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate


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
            p = subprocess.run(current_app.config["COMMAND_PREFIX"] + ["vcgencmd", "measure_temp"], stdout=subprocess.PIPE, check=True)
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


def get_bluez_version():
    qr = get_db().execute("SELECT bluezVer FROM singleton").fetchone()["bluezVer"]
    return "Unknown" if qr is None else qr
