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

from dateutil import tz
import time

from dwd_forecast import DWD


class DwdForecastPlot:
    def __init__(self):
        self.dwd=DWD()

    def _datetime_from_utc_to_local(self, utc_datetime):
        now_timestamp = time.time()
        # offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
        offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.fromtimestamp(now_timestamp)
        ts=(utc_datetime - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
        t1=datetime.datetime.utcfromtimestamp(ts) 
        localtime=t1+offset
        localtime=localtime.replace(tzinfo=tz.tzlocal())
        return localtime

    def get_local_minmaxs(self,x,y,mindist=2):
        mins=[]
        maxs=[]
        # lastx=x[0]
        lasty=y[0]
        dist=0
        lastdirection=None
        direction=0
        for xi,yi in zip(x,y):
            if yi>lasty:
                direction=1
            elif yi<lasty:
                direction=-1
            else:
                direction=0
            if lastdirection==None or dist<mindist:
                lasty=yi
                # lastx=xi
                lastdirection=direction
                dist+=1
                continue
            if lastdirection!=direction:
                if direction==1:
                    mins.append((xi,yi))
                    dist=0
                if direction==-1:
                    maxs.append((xi,yi))
                    dist=0
            else:
                dist+=1
            lasty=yi
            # lastx=xi
            lastdirection=direction
        return mins,maxs

    def format_date(self, x, pos=None):
        return x.to_datetime.strftime('%a, %d.%m.')

    def annotate(self, ax,x,y,text,offset):
        # bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
        # arrowprops=dict(arrowstyle="->",connectionstyle="angle,angleA=0,angleB=60")
        kw = dict(xycoords='data',textcoords="offset points",clip_on=True,
                ha="center", va="center",zorder=4) # arrowprops=arrowprops, bbox=bbox_props, 
        ax.annotate(text, xy=(x,y), xytext=offset,**kw)
        
    def annot_local_minmax(self,x,y, ax=None):
        mins, maxs=self.get_local_minmaxs(x,y,mindist=5)
        for mini,maxi in zip(mins, maxs):

            xmax = maxi[0] # x[np.argmax(y)]
            ymax = maxi[1] # y.max()
            dt=xmax.strftime('%H:%M')
            text= "{:.1f}°C\n{}".format(ymax,dt)
            self.annotate(ax,xmax,ymax,text,(0,0))
            
            xmin = mini[0] # x[np.argmax(y)]
            ymin = mini[1] # y.max()
            dt=xmin.strftime('%H:%M')
            text= "{:.1f}°C\n{}".format(ymin,dt)
            self.annotate(ax,xmin,ymin,text,(0,0))

    def plot(self, station_id, image_file='weather.png', force_cache_refresh=False):
        self.dx=self.dwd.station_forecast(station_id, force_cache_refresh=force_cache_refresh)
        if self.dx is None:
            return None

        # Temperature Kelvin -> Celsius
        self.dxl=self.dx
        self.dxl["TTT"] = self.dxl["TTT"].apply(lambda x: x - 273.15)
        x=self.dxl['TTT'].index.to_numpy()
        xl=[self._datetime_from_utc_to_local(xi) for xi in x]
        y=self.dxl['TTT'].to_numpy()
        y_sun=self.dxl['SunD1'].to_numpy()/3600
        y_rain=self.dxl['wwP'].to_numpy()/100.0
        y_rain_dur=self.dxl['DRR1'].to_numpy()/3600.0


        my_dpi=96
        plt.figure(figsize=(800/my_dpi, 480/my_dpi), dpi=my_dpi)
        fig, ax1 = plt.subplots()
        ax2=ax1.twinx()

        fig.set_size_inches(800/my_dpi, 480/my_dpi)
        ax1.plot(xl,y,alpha=1.0,color='r',zorder=3)
        ax1.grid(True)

        ax2=ax1.twinx()
        ax2.fill_between(x,0,y_sun,color='y',alpha=0.4,zorder=0)
        ax2.set_ylim(0,1)

        ax3=ax1.twinx()
        ax3.fill_between(x,0,y_rain,color='b',alpha=0.2,zorder=1)
        ax3.set_ylim(0,1)

        ax4=ax1.twinx()
        ax4.fill_between(x,0,y_rain_dur,color='b',alpha=0.3,zorder=2)
        ax4.set_ylim(0,1)
                
        self.annot_local_minmax(xl,y,ax1)

        ax1.axvline(datetime.datetime.now(), color='k', zorder=10, alpha=0.5)

        loc = WeekdayLocator(byweekday=(MO,TU,WE,TH,FR,SA,SU))  #, tz=tz)
        ax1.xaxis.set_major_locator(loc)

        better_formatter = DateFormatter('%a, %d.%m.')
        ax1.xaxis.set_major_formatter(better_formatter)
        fig.autofmt_xdate()
        if image_file is not None:
            plt.savefig(image_file,dpi=my_dpi,bbox_inches='tight')
        plt.close('all')  # otherwise auto-refresh of web-server creates infinite number of figures...


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG)
    mpl=logging.getLogger('matplotlib')
    mpl.setLevel(logging.WARNING)
    dfp = DwdForecastPlot()
    dfp.plot(10865)

