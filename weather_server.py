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
    def __init__(self, port=8089, keyfile=None, certfile=None, default_station_id=None):
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('text/javascript', '.js')
        mimetypes.add_type('image/png', '.png')

        self.log = logging.getLogger("WeatherServer")
        self.port = port
        self.station_id = default_station_id
        self.keyfile=keyfile
        self.certfile=certfile

        disable_web_logs = True
        if disable_web_logs is True:
            wlog = logging.getLogger('werkzeug')
            wlog.setLevel(logging.ERROR)
            slog = logging.getLogger('geventwebsocket.handler')
            slog.setLevel(logging.ERROR)
        self.static_resources='web'
        if os.path.exists(self.static_resources) is False:
            os.makedirs(self.static_resources)
        self.app = Flask(__name__, static_folder=self.static_resources)
        self.app.config['SECRET_KEY'] = 'secretsauce'
        self.app.debug = False
        self.app.use_reloader = False

        self.app.add_url_rule('/', 'root', self.weather_plot)
        self.app.add_url_rule('/index.html', 'index', self.weather_plot)
        self.app.add_url_rule('/station/<path:path>', 'stations', self.stations)
        self.app.add_url_rule('/scripts/weather.js',
                              'script', self.weather_script)
        self.app.add_url_rule('/styles/weather.css',
                              'style', self.weather_style)
        self.app.add_url_rule('/weather.png',
                              'weather', self.weather_plot)
        self.active = True
        self.socket_handler()  # Start threads for web
        self.wplot=weather_plot.DwdForecastPlot()

    def web_root(self):
        return self.app.send_static_file('index.html')

    def weather_script(self):
        return self.app.send_static_file('scripts/weather.js')

    def weather_style(self):
        return self.app.send_static_file('styles/weather.css')

    def weather_plot(self):
        imagefile=os.path.join(self.static_resources,'weather.png')
        self.wplot.plot(self.station_id,image_file=imagefile)
        return self.app.send_static_file('weather.png')

    def stations(self, path):
        id=path.split('/')[-1]
        imagefile=os.path.join(self.static_resources,'weather.png')
        self.wplot.plot(id,image_file=imagefile)
        return self.app.send_static_file('weather.png')


    def socket_event_worker_thread(self, log, app, keyfile=None, certfile=None):
        if self.certfile is None or self.keyfile is None:
            server = pywsgi.WSGIServer(
                ('0.0.0.0', self.port), app)
            self.log.info(f"Web browser: http://{socket.gethostname()}:{self.port}")
        else:
            server = pywsgi.WSGIServer(
                ('0.0.0.0', self.port), app, keyfile=self.keyfile, certfile=self.certfile)
            self.log.info(f"Web browser: https://{socket.gethostname()}:{self.port}")
        server.serve_forever()

    def socket_handler(self):
        self.socket_thread_active = True

        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.log, self.app))
        self.socket_event_thread.setDaemon(True)
        self.socket_event_thread.start()

if __name__ == '__main__':
    import argparse

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG)
    mpl=logging.getLogger('matplotlib')
    mpl.setLevel(logging.WARNING)

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, help="port the web server uses")
    parser.add_argument("-c", "--certfile", help="optional certificate file")
    parser.add_argument("-k", "--keyfile", help="optional key file. If both certfile and keyfile are given, https is use.")
    args = parser.parse_args()

    ws = WeatherServer(port=args.port, keyfile=args.keyfile, certfile=args.certfile)
    while True:
        time.sleep(1)
