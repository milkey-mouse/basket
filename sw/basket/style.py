import os.path
from markupsafe import Markup
from flask import current_app

def octicon(name):
    try:
        with current_app.open_resource(os.path.join("octicons", name + ".svg"), "r") as f:
            return Markup(f.read())
    except FileNotFoundError:
        return ""
