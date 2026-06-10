#!/usr/bin/python3
# Copyright (c) 2017-2019 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE

#
# Copyright 2016-2017 David Steele <steele@debian.org>
# This file is part of comitup
# Available under the terms of the GNU General Public License version 2
# or later
#

import logging
import sys
import time
import urllib
from logging.handlers import TimedRotatingFileHandler
from multiprocessing import Process

from cachetools import TTLCache, cached
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
)

sys.path.append(".")
sys.path.append("..")

from comitup import client as ciu  # noqa

ciu_client = None  # type: ignore
LOG_PATH = "/var/log/comitup-web.log"
TEMPLATE_PATH = "/usr/share/comitup/web/templates"

ttl_cache: TTLCache = TTLCache(maxsize=10, ttl=5)


def deflog():
    log = logging.getLogger("comitup_web")
    log.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(
        LOG_PATH,
        encoding="utf=8",
        when="W0",
        backupCount=8,
    )
    fmtr = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(fmtr)
    log.addHandler(handler)

    return log


def do_connect(ssid, password, log):
    time.sleep(1)
    log.debug("Calling client connect")
    ciu_client.service = None  # type: ignore
    ciu_client.ciu_connect(ssid, password)  # type: ignore


@cached(cache=ttl_cache)
def cached_points():
    return ciu_client.ciu_points()  # type: ignore


def create_app(log):
    app = Flask(__name__, template_folder=TEMPLATE_PATH)

    @app.after_request
    def add_header(response):
        response.cache_control.max_age = 0
        return response

    @app.route("/")
    def index():
        points = cached_points()
        for point in points:
            point["ssid_encoded"] = urllib.parse.quote(  # type: ignore
                point["ssid"]
            )
        log.info("index.html - {} points".format(len(points)))
        return render_template(
            "index.html", points=points, can_blink=ciu.can_blink()
        )

    @app.route("/confirm")
    def confirm():
        ssid = request.args.get("ssid", "")
        ssid_encoded = urllib.parse.quote(ssid.encode())  # type: ignore
        encrypted = request.args.get("encrypted", "unencrypted")

        mode = ciu_client.ciu_info()["imode"]  # type: ignore

        log.info("confirm.html - ssid {0}, mode {1}".format(ssid, mode))

        return render_template(
            "confirm.html",
            ssid=ssid,
            encrypted=encrypted,
            ssid_encoded=ssid_encoded,
            mode=mode,
            can_blink=ciu.can_blink(),
        )

    @app.route("/connect", methods=["POST"])
    def connect():
        ssid = urllib.parse.unquote(request.form["ssid"])  # type: ignore
        password = request.form["password"].encode()

        # ship_prep: WPA2 length guard
        # WPA2-PSK passphrase must be either empty (open network) or 8..63 chars.
        # Reject 1..7 here before do_connect spawns, so the buyer sees an
        # immediate styled error instead of waiting ~95s for NM to fail.
        if 0 < len(password) < 8:
            log.warning("rejected short password (len=%d) for ssid %s" % (len(password), ssid))
            return (
                "<!DOCTYPE html><html><head><meta charset=utf-8>"
                "<meta name=viewport content='width=device-width,initial-scale=1'>"
                "<title>xAMP - Password too short</title>"
                "<style>body{background:linear-gradient(135deg,#0d0820,#1a0f33);"
                "color:#f0e8f5;font-family:-apple-system,sans-serif;min-height:100vh;"
                "padding:40px 20px;margin:0}.wrap{max-width:420px;margin:0 auto;text-align:center}"
                "h1{color:#ff4ecd;font-size:24px;margin-bottom:14px}"
                "p{color:#9a8eb0;line-height:1.6}a{display:inline-block;margin-top:24px;"
                "padding:12px 24px;background:#ff4ecd;color:#fff;text-decoration:none;"
                "border-radius:8px;font-weight:700;letter-spacing:1px;text-transform:uppercase}</style>"
                "</head><body><div class=wrap><h1>Password too short</h1>"
                "<p>WiFi passwords must be at least 8 characters. "
                "Tap below to try again.</p>"
                "<a href=/>Go Back</a></div></body></html>",
                400,
                {"Content-Type": "text/html; charset=utf-8"},
            )


        cached_points()

        p = Process(target=do_connect, args=(ssid, password, log))
        p.start()

        log.info("connect.html - ssid {0}".format(ssid))
        return render_template(
            "connect.html",
            ssid=ssid,
            password=password,
        )

    @app.route("/blink")
    def blink():
        log.info("blinking")
        ciu.blink()

        resp = jsonify(success=True)
        return resp

    @app.route("/img/favicon.ico")
    def favicon():
        log.info("Returning 404 for favicon request")
        abort(404)

    @app.route("/img/<path:path>")
    def send_image(path):
        return send_from_directory(TEMPLATE_PATH + "/images", path)

    @app.route("/js/<path:path>")
    def send_js(path):
        return send_from_directory(TEMPLATE_PATH + "/js", path)

    @app.route("/css/<path:path>")
    def send_css(path):
        return send_from_directory(TEMPLATE_PATH + "/css", path)

    @app.route("/<path:path>")
    def catch_all(path):
        log.info("Redirecting {0}".format(path))
        return redirect("http://10.41.0.1/", code=302)

    @app.errorhandler(500)
    def internal_error(error):
        # ship_prep: do not sys.exit() on 500 — orderly response keeps comitup-web alive
        log.error("Internal Error detected: %r" % (error,))
        return ("Internal Server Error — see /var/log/comitup-web.log", 500,
                {"Content-Type": "text/plain; charset=utf-8"})

    return app


def main():
    log = deflog()
    log.info("Starting comitup-web")

    global ciu_client
    ciu_client = ciu.CiuClient()

    ciu_client.ciu_state()
    ciu_client.ciu_points()

    app = create_app(log)
    app.run(host="0.0.0.0", port=80, debug=False, threaded=True)


if __name__ == "__main__":
    main()
