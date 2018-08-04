import os
import base64
from flask import Flask, session, redirect, url_for
from werkzeug.security import generate_password_hash


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # the secret key doesn't need to persist; the user can just relogin
    app.secret_key = "dev" if app.debug else os.urandom(32)

    # create initial password
    os.makedirs(app.instance_path, exist_ok=True)
    if not os.path.isfile(os.path.join(app.instance_path, "password")):
        password = os.environ.get("INITIAL_PASSWORD")

        if password is None:
            password = base64.b32encode(os.urandom(20)).decode("utf-8").lower()
            print("A password has not previously been set and INITIAL_PASSWORD was not")
            print("specified in the config, so one has been automatically generated.")
            print("Your password is '{}'.".format(password))

        with app.open_instance_resource("password", "w") as f:
            f.write(generate_password_hash(password))

    from . import auth, ctrl
    app.register_blueprint(auth.bp)
    app.register_blueprint(ctrl.bp)

    app.add_url_rule("/", endpoint="index")

    return app
