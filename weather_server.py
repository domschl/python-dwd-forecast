import logging
import time
import threading
import queue
import json
import mimetypes
import socket
import os
import struct

from flask import Flask, send_from_directory
from gevent import pywsgi
from PIL import Image

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
        mimetypes.add_type("image/bmp", ".bmp")

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
        self.app.add_url_rule(
            "/ministation/<path:path>", "ministations", self.ministations
        )
        self.app.add_url_rule("/auto/<path:path>", "autostations", self.autostations)
        self.app.add_url_rule("/scripts/weather.js", "script", self.weather_script)
        self.app.add_url_rule("/styles/weather.css", "style", self.weather_style)
        self.app.add_url_rule("/favicon.ico", "favi", self.favicon)
        self.app.add_url_rule("/weather.png", "weather", self.weather_plot)
        self.app.add_url_rule("/weather.bmp", "miniweather", self.miniweather_plot)
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

    def miniweather_plot(self):
        imagefile = os.path.join(self.static_resources, "/weather.bmp")
        self.wplot.plot(self.station_id, image_file=imagefile)
        return self.app.send_static_file("weather.bmp")

    def autostations(self, path):
        return self.app.send_static_file("index.html")

    def stations(self, path):
        id = path.split("/")[-1]
        self.log.info(f"We are getting {id}")
        imagefile = os.path.join(self.static_resources, "weather.png")
        self.wplot.plot(id, image_file=imagefile, dpi=self.dpi)
        return self.app.send_static_file("weather.png")

    def save_bmp_24bit(self, image, output_file):
        width, height = image.size
        pixel_data = list(image.getdata())

        # BMP header (14 bytes)
        header = struct.pack("<2sIHHI", b"BM", 54 + width * height * 3, 0, 0, 54)

        # DIB header (40 bytes)
        dib_header = struct.pack(
            "<IIIHHIIIIII", 40, width, height, 1, 24, 0, width * height * 3, 0, 0, 0, 0
        )

        # Pixel data (row order is reversed)
        pixel_bytes = []
        for i in range(height - 1, -1, -1):
            for j in range(width):
                r, g, b = pixel_data[i * width + j]
                pixel_bytes.extend([b, g, r])

        # Save the BMP file
        with open(output_file, "wb") as f:
            f.write(header + dib_header + bytes(pixel_bytes))

    def ministations(self, path):
        id = path.split("/")[-1]
        self.log.info(f"We are getting {id}")
        imagefile = os.path.join(self.static_resources, "weather.png")
        self.wplot.plot(id, image_file=imagefile, dpi=self.dpi)
        # resize imagefile to 240x135 and save as weather.bmp
        image = Image.open(imagefile).convert("RGB")
        # image_rgb = image.convert("RGB")
        # Resize the image
        resized_image = image.resize((240, 135))
        bmpimagefile = os.path.join(self.static_resources, "weather.bmp")

        image_16bit = Image.new("RGB565", resized_image.size)

        # Iterate over each pixel and convert to RGB565 format
        for y in range(resized_image.height):
            for x in range(resized_image.width):
                r, g, b = resized_image.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                image_16bit.putpixel((x, y), rgb565)

        # Save the image as a 16-bit BMP file
        image_16bit.save(bmpimagefile, format="BMP")

        # self.save_bmp_24bit(resized_image, bmpimagefile)
        # resized_image.save(bmpimagefile, format="BMP",
        return self.app.send_static_file("weather.bmp")

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
