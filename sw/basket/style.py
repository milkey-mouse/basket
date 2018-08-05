import os.path
from markupsafe import Markup
from flask import current_app


def icon(name):
    try:
        with current_app.open_resource(os.path.join("icons", name + ".svg"), "r") as f:
            return Markup(f.read())
    except FileNotFoundError:
        return ""
