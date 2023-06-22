#!/usr/bin/env python3
# coding: utf-8

import logging

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import datetime
from matplotlib.dates import MO, TU, WE, TH, FR, SA, SU
from matplotlib.dates import WeekdayLocator
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

from dateutil import tz
import time

from dwd_forecast import DWD


class DwdForecastPlot:
    def __init__(self):
        self.dwd = DWD()

    def _datetime_from_utc_to_local(self, utc_datetime):
        now_timestamp = time.time()
        # offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
        offset = datetime.datetime.fromtimestamp(
            now_timestamp
        ) - datetime.datetime.fromtimestamp(now_timestamp)
        ts = (utc_datetime - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(
            1, "s"
        )
        t1 = datetime.datetime.utcfromtimestamp(ts)
        localtime = t1 + offset
        localtime = localtime.replace(tzinfo=tz.tzlocal())
        return localtime

    def get_local_minmaxs(self, x, y, mindist=2):
        mins = []
        maxs = []
        # lastx=x[0]
        lasty = y[0]
        dist = 0
        lastdirection = None
        direction = 0
        for xi, yi in zip(x, y):
            if yi > lasty:
                direction = 1
            elif yi < lasty:
                direction = -1
            else:
                direction = 0
            if lastdirection == None or dist < mindist:
                lasty = yi
                # lastx=xi
                lastdirection = direction
                dist += 1
                continue
            if lastdirection != direction:
                if direction == 1:
                    mins.append((xi, yi))
                    dist = 0
                if direction == -1:
                    maxs.append((xi, yi))
                    dist = 0
            else:
                dist += 1
            lasty = yi
            # lastx=xi
            lastdirection = direction
        return mins, maxs

    def format_date(self, x, pos=None):
        return x.to_datetime.strftime("%a, %d.%m.")

    def annotate(self, ax, x, y, text, offset):
        # bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
        # arrowprops=dict(arrowstyle="->",connectionstyle="angle,angleA=0,angleB=60")
        kw = dict(
            xycoords="data",
            textcoords="offset points",  # clip_on=True,
            ha="center",
            va="center",
        )  # arrowprops=arrowprops, bbox=bbox_props,
        ax.annotate(text, xy=(x, y), xytext=offset, annotation_clip=False, **kw)

    def annot_local_minmax(self, x, y, ax=None):
        mins, maxs = self.get_local_minmaxs(x, y, mindist=5)
        for mini, maxi in zip(mins, maxs):
            xmax = maxi[0]  # x[np.argmax(y)]
            ymax = maxi[1]  # y.max()
            dt = xmax.strftime("%H:%M")
            text = "{:.1f}°C\n{}".format(ymax, dt)
            self.annotate(ax, xmax, ymax, text, (7, 15))

            xmin = mini[0]  # x[np.argmax(y)]
            ymin = mini[1]  # y.max()
            dt = xmin.strftime("%H:%M")
            text = "{:.1f}°C\n{}".format(ymin, dt)
            self.annotate(ax, xmin, ymin, text, (7, -15))

    def plot(
        self,
        station_id,
        image_file="weather.png",
        force_cache_refresh=False,
        close_plot=True,
        dpi=96,
    ):
        self.dx = self.dwd.station_forecast(
            station_id, force_cache_refresh=force_cache_refresh
        )
        if self.dx is None:
            return None

        # Temperature Kelvin -> Celsius
        self.dxl = self.dx
        self.dxl["TTT"] = self.dxl["TTT"].apply(lambda x: x - 273.15)
        x = self.dxl["TTT"].index.to_numpy()
        xl = [self._datetime_from_utc_to_local(xi) for xi in x]
        y = self.dxl["TTT"].to_numpy()
        y_sun = self.dxl["SunD1"].to_numpy() / 3600
        y_rain = self.dxl["wwP"].to_numpy() / 100.0
        y_rain_dur = self.dxl["DRR1"].to_numpy() / 3600.0

        my_dpi = dpi
        plt.figure(figsize=(800 / my_dpi, 480 / my_dpi), dpi=my_dpi)
        fig, ax1 = plt.subplots()
        fig.set_size_inches(800 / my_dpi, 480 / my_dpi)

        ax1.set_zorder(10)
        ax1.patch.set_visible(False)
        title = "DWD OpenData - " + time.strftime("%A, %d.%m.%y %H:%M")
        ax1.text(
            1,
            1.01,
            title,
            horizontalalignment="right",
            color="gray",
            verticalalignment="bottom",
            transform=ax1.transAxes,
        )

        ax3 = ax1.twinx()
        ax3.set_zorder(1)
        ax3.fill_between(x, 0, y_rain, color="lightblue", alpha=0.6)
        ax3.set_ylim(0, 1)

        ax4 = ax1.twinx()
        ax4.set_zorder(2)
        ax4.fill_between(x, 0, y_rain_dur, color="cornflowerblue", alpha=0.7)
        ax4.set_ylim(0, 1)

        ax2 = ax1.twinx()
        ax2.set_zorder(3)
        ax2.grid(False)
        ax2.fill_between(x, 0, y_sun, color="gold", alpha=0.6)
        ax2.set_ylim(0, 1)

        ax1.plot(xl, y, alpha=0.6, linewidth=3, color="orangered")
        ax1.grid(True, linestyle="dotted")
        # ax1.set_axisbelow(False)

        self.annot_local_minmax(xl, y, ax1)

        ax1.axvline(datetime.datetime.now(), color="dimgray", alpha=0.6)

        lim = ax1.get_ylim()
        d = lim[1] - lim[0]
        lim2 = (lim[0] - d / 10, lim[1] + d / 10)
        ax1.set_ylim(lim2)

        loc = WeekdayLocator(byweekday=(MO, TU, WE, TH, FR, SA, SU))  # , tz=tz)
        ax1.xaxis.set_major_locator(loc)

        better_formatter = DateFormatter("%a  \n%d.%m.")
        ax1.xaxis.set_major_formatter(better_formatter)
        fig.autofmt_xdate()
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=0)

        for tick in ax1.xaxis.get_major_ticks():
            tick.label1.set_horizontalalignment("left")
        # ax1.xaxis.set_major_locator(MaxNLocator(prune='both'))

        if image_file is not None:
            plt.savefig(image_file, dpi=my_dpi, bbox_inches="tight")
        if close_plot is True:
            plt.close(
                "all"
            )  # otherwise auto-refresh of web-server creates infinite number of figures...


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.DEBUG
    )
    mpl = logging.getLogger("matplotlib")
    mpl.setLevel(logging.WARNING)
    dfp = DwdForecastPlot()
    dfp.plot(10865)
