import logging
import time
import threading
import queue
import json
import mimetypes
import socket
import os

from flask import Flask, send_from_directory
from gevent import pywsgi

import weather_plot


class WeatherServer:
    def __init__(
        self,
        port=8089,
        keyfile=None,
        certfile=None,
        default_station_id=None,
        dpi=96,
        threading=True,
    ):
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("text/javascript", ".js")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("image/png", ".ico")

        self.log = logging.getLogger("WeatherServer")
        self.port = port
        self.station_id = default_station_id
        self.keyfile = keyfile
        self.certfile = certfile
        self.dpi = dpi

        disable_web_logs = True
        if disable_web_logs is True:
            wlog = logging.getLogger("werkzeug")
            wlog.setLevel(logging.ERROR)
            slog = logging.getLogger("geventwebsocket.handler")
            slog.setLevel(logging.ERROR)
        self.static_resources = "web"
        if os.path.exists(self.static_resources) is False:
            os.makedirs(self.static_resources)
        self.app = Flask(__name__, static_folder=self.static_resources)
        self.app.config["SECRET_KEY"] = "secretsauce"
        self.app.debug = False
        self.app.use_reloader = False

        self.app.add_url_rule("/", "root", self.weather_plot)
        self.app.add_url_rule("/index.html", "index", self.weather_plot)
        self.app.add_url_rule("/station/<path:path>", "stations", self.stations)
        self.app.add_url_rule("/auto/<path:path>", "autostations", self.autostations)
        self.app.add_url_rule("/scripts/weather.js", "script", self.weather_script)
        self.app.add_url_rule("/styles/weather.css", "style", self.weather_style)
        self.app.add_url_rule("/favicon.ico", "favi", self.favicon)
        self.app.add_url_rule("/weather.png", "weather", self.weather_plot)
        self.active = True
        if threading is True:
            self.socket_handler()  # Start threads for web
        self.wplot = weather_plot.DwdForecastPlot()

    def web_root(self):
        return self.app.send_static_file("index.html")

    def favicon(self):
        self.log.info("favi-info")
        return self.app.send_static_file("favicon.ico")

    def weather_script(self):
        return self.app.send_static_file("scripts/weather.js")

    def weather_style(self):
        return self.app.send_static_file("styles/weather.css")

    def weather_plot(self):
        imagefile = os.path.join(self.static_resources, "/weather.png")
        self.wplot.plot(self.station_id, image_file=imagefile)
        return self.app.send_static_file("weather.png")

    def autostations(self, path):
        return self.app.send_static_file("index.html")

    def stations(self, path):
        id = path.split("/")[-1]
        self.log.info(f"We are getting {id}")
        imagefile = os.path.join(self.static_resources, "weather.png")
        self.wplot.plot(id, image_file=imagefile, dpi=self.dpi)
        return self.app.send_static_file("weather.png")

    def socket_event_worker_thread(self, log, app, keyfile=None, certfile=None):
        if self.certfile is None or self.keyfile is None:
            server = pywsgi.WSGIServer(("0.0.0.0", self.port), app)
            self.log.info(f"Web browser: http://{socket.gethostname()}:{self.port}")
        else:
            server = pywsgi.WSGIServer(
                ("0.0.0.0", self.port),
                app,
                keyfile=self.keyfile,
                certfile=self.certfile,
            )
            self.log.info(f"Web browser: https://{socket.gethostname()}:{self.port}")
        server.serve_forever()

    def socket_handler(self):
        self.socket_thread_active = True

        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.log, self.app)
        )
        self.socket_event_thread.daemon = True
        self.socket_event_thread.start()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.DEBUG
    )
    mpl = logging.getLogger("matplotlib")
    mpl.setLevel(logging.WARNING)

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, help="port the web server uses")
    parser.add_argument(
        "-d",
        "--dpi",
        type=int,
        help="dpi of the plot (should be around 96)",
        default=96,
    )
    parser.add_argument(
        "-t",
        "--threading",
        default=False,
        action="store_true",
        help="use threading (don't use on Mac, crashes when plotting in non-main thread.)",
    )
    parser.add_argument("-c", "--certfile", help="optional certificate file")
    parser.add_argument(
        "-k",
        "--keyfile",
        help="optional key file. If both certfile and keyfile are given, https is use.",
    )
    args = parser.parse_args()

    ws = WeatherServer(
        port=args.port,
        keyfile=args.keyfile,
        certfile=args.certfile,
        threading=args.threading,
        dpi=args.dpi,
    )
    if args.threading is True:
        while True:
            time.sleep(1)
    else:
        ws.socket_event_worker_thread(
            ws.log, ws.app, keyfile=args.keyfile, certfile=args.certfile
        )
