from flask import Blueprint, redirect, url_for, Response
from .auth import login_required
from .db import get_db

has_uwsgi = True
try:
    import uwsgi
except ImportError:
    has_uwsgi = False

bp = Blueprint("stream", __name__, url_prefix="/stream")


@bp.route("/")
@login_required
def index():
    if not has_uwsgi:
        return redirect(url_for("static", filename="nocam.jpg"))
    def generate_mjpg_stream():
        #view = uwsgi.sharedarea_memoryview(0)
        while True:
            yield b"--frame\r\n"
            yield b"Content-Type: image/jpeg\r\n\r\n"
            uwsgi.sharedarea_wait(0)
            yield uwsgi.sharedarea_read(0, 0)
            yield b"\r\n"
    return Response(generate_mjpg_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")
