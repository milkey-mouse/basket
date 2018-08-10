import os
from socket import gethostname
from werkzeug.security import generate_password_hash
from flask import Flask, session, redirect, url_for

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False

if has_uwsgi:
    from flask_uwsgi_websocket import WebSocket


def create_base():
    app = Flask(__name__)
    app.config.from_mapping(
        # the secret key doesn't need to persist; the user can just relogin
        SECRET_KEY=("dev" if app.debug else os.urandom(32)),
        DATABASE=os.path.join(app.instance_path, "basket.sqlite"),
    )
    app.config.from_pyfile("config.py", silent=True)

    return app


def create_app():
    app = create_base()

    os.makedirs(app.instance_path, exist_ok=True)

    from . import style
    app.jinja_env.globals.update(icon=style.icon, gethostname=gethostname)
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True

    from . import worker, db
    worker.init_app(app)
    db.init_app(app)

    from . import auth, ctrl
    app.register_blueprint(auth.bp)
    app.register_blueprint(ctrl.bp)

    app.add_url_rule("/", endpoint="index")

    if has_uwsgi:
        ctrl.init_ws(app)
        ws = WebSocket(app)
        ws.register_blueprint(ctrl.ws)
        ws.app = app

    return app
