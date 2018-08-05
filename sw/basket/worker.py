import os
import time
import random
from flask.cli import with_appcontext
from flask import current_app, g
import click
from .db import get_db


def get_dummy_mac():
    return (":".join(["{:02x}",]*6)).format(*os.urandom(6))


def init_dummy_worker():
    db = get_db()

    for i in range(0, 10):
        time.sleep(3)
        db.execute("INSERT INTO bluetooth values (?, ?)", (get_dummy_mac(), random.choice(("Egg", None))))
        db.commit()


@click.command("run-dummy-worker")
@with_appcontext
def init_dummy_worker_command():
    click.echo("Dummy worker running.")
    init_dummy_worker()


def init_app(app):
    app.cli.add_command(init_dummy_worker_command)
