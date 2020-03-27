import logging
import os
import time
import json
import pandas as pd
import xml.etree.cElementTree as et
import zipfile
import datetime

try:  # Python 3
    from urllib.request import urlopen
except ImportError:
    logging.error("Python 2 is not supported!")

from io import StringIO, BytesIO
from zipfile import ZipFile

try:
    from geopy import distance
    geopy_loaded=True
except:
    geopy_loaded=False
    logging.warning('location search not available: geopy not installed.')

# Doc on fields:
# https://opendata.dwd.de/weather/lib/MetElementDefinition.xml

class DWD:
    def __init__(self, cache_directory=None):
        self.log = logging.getLogger("DWD")
        if cache_directory is None:
            self.cachedir=self._get_default_cachedir()
            if self.cachedir is None:
                self.log.error(f'Failed to create cache directory {self.cachedir}')
                self.init=False
                return
        else:
            if os.path.exists(cache_directory) is False:
                try:
                    os.makedirs(cache_directory)
                except Exception as e:
                    self.log.error(f'Failed to create cache directory {cache_directory}: {e}')
                    self.init=False
                    return
            self.cachedir=cache_directory
        self.station_list_url='https://www.dwd.de/DE/leistungen/klimadatendeutschland/statliste/statlex_html.html?view=nasPublication&nn=16102'
        self.station_list_cache_days=1
        self.station_list_df=None
        self.forecasts_all_url='https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/all_stations/kml/MOSMIX_L_LATEST.kmz'
        self.forecast_station_url='https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{0}/kml/MOSMIX_L_LATEST_{0}.kmz'
        self.forecast_max_cache_secs=3600

    def _get_default_cachedir(self):
        cachedir= "./cache"
        if os.path.exists(cachedir) is False:
            try:
                os.makedirs(cachedir)
            except Exception as e:
                self.log.error(f'Failed to create cache directory {cachedir}: {e}')
                return None
        return "./cache"

    def _filter_tag(self, tag):
        i = tag.find('}')
        if i != -1:
            return tag[i+1:]
        else:
            return tag

    def _filter_attrib_dict(self, att):
        d = {}
        for el in att:
            d[self._filter_tag(el)] = att[el]
        return d

    def _is_uptodate(self, i):
        if self.station_list_df is None:
            return False
        tim=self.station_list_df['EndeDT'][i]
        if pd.isna(tim) is False:
            delta=datetime.datetime.now()-self.station_list_df['EndeDT'][i]
            if delta.total_seconds() < 7 * 24 * 3600: # Max 7 days
                return True
        return False

    def get_closest(self, lat, lon):
        ''' return tuple of (station-id, name, distance (km)) '''
        if geopy_loaded is False:
            self.log.error("get_closest() requires geopy module.")
            return None
        if self.station_list_df is None:
            self.read_station_list()
        dists=[]
        for i in range(len(self.station_list_df)):
            if self._is_uptodate(i):
                lati=self.station_list_df['Breite'][i]
                loni=self.station_list_df['Länge'][i]
                dist=distance.distance((lat, lon), (lati, loni))
                dists.append((i,dist))
        sdists=sorted(dists,key=lambda x: x[1])
        for di in sdists[:100]:
            url=self.forecast_station_url.format(self.station_list_df['Stations-kennung'][di[0]])
            try:
                urlopen(url)
                return (self.station_list_df['Stations-kennung'][di[0]], self.station_list_df['Stationsname'][di[0]], di[1])
            except:
                logging.debug(f"Station {self.station_list_df['Stations-kennung'][di[0]]} fails")
        return None

    def read_station_list(self, force_cache_refresh=False):
        df=None
        station_cache_file = os.path.join(self.cachedir, 'station-list.json')
        read_station_list=False
        if force_cache_refresh is True or os.path.exists(station_cache_file) is False:
            read_station_list=True
        else:
            try:
                with open(station_cache_file, 'r') as f:
                    station_list=json.load(f)
                    self.log.debug(f'Read station list {station_cache_file} from cache')
                if time.time() - station_list['timestamp'] > self.station_list_cache_days *24*3600:
                    self.log.info(f'Refreshing station list, age is > {self.station_list_cache_days}')
                    read_station_list=True
                del station_list['timestamp']
                try:
                    df=pd.read_json(json.dumps(station_list))
                    df[['Flussgebiet']] = df[['Flussgebiet']].astype(
                        float)  # NaN is not supported with int
                    df[['Stations_ID', 'Stations-höhe']
                    ] = df[['Stations_ID', 'Stations-höhe']].astype(int)
                    df[['Breite', 'Länge']] = df[['Breite', 'Länge']].astype(float)
                    df['BeginnDT'] = pd.to_datetime(
                        df['Beginn'], format='%d.%m.%Y', errors='ignore')
                    df['EndeDT'] = pd.to_datetime(
                        df['Ende'], format='%d.%m.%Y', errors='ignore')

                except Exception as e:
                    self.log.warning(f'Failed to convert station list to dataframe: {e}, trying to reload')
                    read_station_list=True
            except Exception as e:
                self.log.error(f'Failed to read station-list {station_cache_file}: {e}')
                read_station_list=True

        if read_station_list is True:
            try:
                station_list_raw = urlopen(self.station_list_url).read().decode('utf-8')
            except Exception as e:
                self.log.error(f'Failed to download DWD station list from {self.station_list_url}: {e}')
                return None

            # lst = pd.read_html(station_list_raw, parse_dates=[9, 10], header=2)
            lst = pd.read_html(station_list_raw, header=2)
            df = lst[0]
            df[['Flussgebiet']] = df[['Flussgebiet']].astype(
                float)  # NaN is not supported with int
            df[['Stations_ID', 'Stations-höhe']
            ] = df[['Stations_ID', 'Stations-höhe']].astype(int)
            df[['Breite', 'Länge']] = df[['Breite', 'Länge']].astype(float)
            df['BeginnDT'] = pd.to_datetime(
                df['Beginn'], format='%d.%m.%Y', errors='ignore')
            df['EndeDT'] = pd.to_datetime(
                df['Ende'], format='%d.%m.%Y', errors='ignore')

            try:
                station_list=json.loads(df.to_json())
            except Exception as e:
                self.log.error(f'Failed to convert dataframe to json: {e}')
                return None
            station_list['timestamp']=time.time()
            try:
                with open(station_cache_file, 'w') as f:
                    json.dump(station_list,f)
            except Exception as e:
                self.log.warning(f'Failed to save station_list cache {station_cache_file}: {e}')

        self.station_list_df=df
        return df

    def search_station_by_name(self, name):
        if self.station_list_df is None:
            df=self.read_station_list()
        else:
            df=self.station_list_df
        if df is None:
            self.log.error("Failed to get station-list")
            return None

        station_us = df[df['Stationsname'].str.contains(name)]
        if station_us is not None and len(station_us) > 0:
            station = station_us.sort_values(by='Ende', ascending=False)
            return station.iloc(0)[0]["Stations-kennung"]
        return None
        # else:
        #     self.log.info("Rereading station-list...")
        #     self.read_station_list(read_cache=False)
        #     station_us = df[df['Stationsname'].str.contains(name)]
        #     if station_us is not None and len(station_us) > 0:
        #         station = station_us.sort_values(by='Ende', ascending=False)
        #         self.log.debug("Success after reread.")
        #         return station.iloc(0)[0]["Stations-kennung"]
        #     else:
        #         self.log.warning("Failed to identify station!")
        #         return None

    def _download_unpack(self, url):
        try:
            self.log.debug(f'Downloading: {url}')
            resp = urlopen(url)
            zfile = ZipFile(BytesIO(resp.read()))
            iodata = zfile.open(
                zfile.namelist()[0]).read()
        except Exception as e:
            self.log.error(f'Unable to download {url}: {e}')
            return None
        return iodata

    def _download_forecast_all(self):
        return self._download_unpack(self.forecasts_all_url)

    def _download_station_forecast_raw(self,  station_id):
        dl_url = self.forecast_station_url.format(station_id)
        return self._download_unpack(dl_url)

    def station_forecast(self, station_id, force_cache_refresh=False):
        if station_id is None:
            forecast_cache_file = os.path.join(self.cachedir, 'station-forecast-all.json')
        else:
            forecast_cache_file = os.path.join(self.cachedir, f'station-forecast-{station_id}.json')

        dfd=None
        locations=None
        read_station_forecast=False
        if force_cache_refresh is True or os.path.exists(forecast_cache_file) is False:
            read_station_forecast=True
        else:
            try:
                with open(forecast_cache_file, 'r') as f:
                    station_forecast=json.load(f)
                if time.time() - station_forecast['timestamp'] > self.forecast_max_cache_secs:
                    self.log.info(f'Refreshing station forecast, age is > {self.forecast_max_cache_secs}')
                    read_station_forecast=True
                del station_forecast['timestamp']
                try:
                    if station_id is None:
                        locations=pd.read_json(json.dumps(station_forecast))
                        self.log.debug(f'Station forecast ALL read from cache {forecast_cache_file}')
                    else:
                        dfd=pd.read_json(json.dumps(station_forecast))
                        self.log.debug(f'Station forecast {station_id} read from cache {forecast_cache_file}')
                except Exception as e:
                    self.log.warning(f'Failed to convert station forecast to dataframe: {e}, trying to reload')
                    read_station_forecast=True
            except Exception as e:
                self.log.error(f'Failed to read station forecast {forecast_cache_file}: {e}')
                read_station_forecast =True

        if read_station_forecast is True:
            if station_id is None:
                iodata = self._download_forecast_all()
            else:
                iodata = self._download_station_forecast_raw(station_id)
            if iodata is None:
                return None
            self.log.debug(f"Starting to parse station {station_id} xml...")
            xmlroot = et.fromstring(iodata)
            self.log.debug("parsed xml")
            timesteps = []
            locations = []
            dfd = None
            for node in xmlroot:
                tag = self._filter_tag(node.tag)
                att = self._filter_attrib_dict(node.attrib)
                location = None
                for node2 in node:
                    tag = self._filter_tag(node2.tag)
                    att = self._filter_attrib_dict(node2.attrib)
                    if tag == "Placemark":
                        location = {}
                        dfd = pd.DataFrame({'time': timesteps})
                        dfd.index = pd.to_datetime(dfd.pop('time'))
                    for node3 in node2:
                        tag = self._filter_tag(node3.tag)
                        att = self._filter_attrib_dict(node3.attrib)
                        for node4 in node3:
                            tag = self._filter_tag(node4.tag)
                            att = self._filter_attrib_dict(node4.attrib)
                            if tag == 'Forecast':
                                key = att['elementName']
                            for node5 in node4:
                                data = None
                                tag = self._filter_tag(node5.tag)
                                att = self._filter_attrib_dict(node5.attrib)
                                text = node5.text
                                if tag == 'TimeStep':
                                    timesteps.append(text)
                                    text = None
                                if text is not None:
                                    data = text.split()
                                if data is not None and tag == 'value':
                                    dfd[key] = pd.to_numeric(
                                        pd.Series(data, index=dfd.index), errors='coerce')
                                else:
                                    data = None
                if location is not None:
                    dfd.index=dfd.index.tz_convert(tz=None)
                    location['forecast'] = dfd
                    locations.append(location)
                    location = None
            if station_id is not None:
                if len(locations)!=1:
                    self.log.error('Internal: length of locations is {len(locations)}, expected 1.')
                    return False
                dfd=locations[0]['forecast']
                try:
                    forecast=json.loads(dfd.to_json())
                    forecast['timestamp']=time.time()
                except Exception as e:
                    self.log.warning(f'Failed to convert forecast to json: {e}')
                    return dfd
                try:
                    with open(forecast_cache_file, 'w') as f:
                        json.dump(forecast,f)
                except Exception as e:
                    self.log.warning(f'Failed to write forecast cache file {forecast_cache_file}: {e}')
            else:
                try:
                    all_forecasts={'timestamp': time.time(),
                                    locations: []}
                    forecasts=json.loads(locations.to_json())
                    forecast['timestamp']=time.time()
                except Exception as e:
                    self.log.warning(f'Failed to convert forecast to json: {e}')
                    return dfd
                try:
                    with open(forecast_cache_file, 'w') as f:
                        json.dump(forecast,f)
                except Exception as e:
                    self.log.warning(f'Failed to write forecast cache file {forecast_cache_file}: {e}')
                
        if station_id is None:
            return locations
        else:
            return dfd


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG)
    dwd = DWD()
    dwd.read_station_list()
    df = dwd.station_forecast(10865)
    if df is not None:
        print(df)
