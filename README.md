# python-dwd-forecast

Detailed weather forecast from [DWD (Deutscher Wetter Dienst)](https://www.dwd.de/EN/ourservices/opendata/opendata.html)

This provides:

* a module to download German weather forecasts (10 days, 1 hour resolution) as pandas dataframe
* a module to generate a forecast plot
* a module to serve the forecast plot via web server for integration in home automation panels or similar

![weather](https://github.com/domschl/python-dwd-forecast/blob/master/resources/weather.png)

The plot shows detailed temperature forecasts and sunshine probabilites (yellow) and rain probabilities (blue).

Have a look at the [jupyter notebook](https://github.com/domschl/python-dwd-forecast/blob/master/tests.ipynb) for an overview of the functionality.

## `dwd_forecast`: download and normalize weather data

### Find your station id

Either use the [reference list](https://www.dwd.de/DE/leistungen/klimadatendeutschland/statliste/statlex_html.html?view=nasPublication&nn=16102), column `Stations-kennung` is the `station-id`, provided by the Open Data project of DWD, or use the location API below.

Caveat: this reference list contains many weather stations that are no longer active, or do not provide forecast data. If you want to search manually, you will need to search for stations that are still active (look at `Ende` column which marks the last data transmission) and actually provide data. 

The API call `get_closest(lat,lon)` does that automatically.

```python
from dwd_forecast import DWD
d=DWD()
my_lat, my_lon=(48.15, 11.56)
nearest=d.get_closest(my_lat,my_lon)
print(nearest)
# ('10865', 'München-Stadt', Distance(1.9339969383980125))
```

Station id is `10865`, name of this station is `München-Stadt`, and the station is 1.93km from the given coordinates.

### Get the forecast data

```python
from dwd_forecast import DWD
d=DWD()
dw=d.station_forecast('10865')  # station-id from above
dw.head()  # dataframe with detailed forecast information (see https://opendata.dwd.de/weather/lib/MetElementDefinition.xml)
```

## `weather_plot`: plot a forecast

```python
from weather_plot import DwdForecastPlot
wp=DwdForecastPlot()
wp.plot("10865",image_file='weather.png')  # station-id 10865 from above.
```

## `weather_server`: your private weather forecast server

```python
from weather_server import WeatherServer
ws = WeatherServer(port=8089, keyfile=my_keyfile, certfile=my_certfile) # creates thread that serves web requests
while True:
    time.sleep(1)
```
If keyfile and certfile are ommited, the web server serves on http://localhost:8089/station/my-station-id, e.g. http://localhost:8089/station/10865. With cert- and keyfile given, https is used: https://hostname:8089/station/10865.

The server simply returns a PNG that can be embedded in other portals (e.g. Home Assistant)

## Start weather server

```bash
python weather_server.py --port 8089 --certfile cert.pem --keyfile key.pem
```
This starts a web server on port 8089, access for example for station 10865 with: http://localhost:8089/station/10865 (no certs given). With cert- and keyfile given, https is used: https://hostname:8089/station/10865

The file `weather_server_sample.service` can be used as a base for systemd installatins.

## Dependencies

`dwd_forecast`:
* `pandas`: Forecast results are given as pandas `Dataframes`
* `geopy`: [optional], needed to find nearest station via latitude/longitude search

`weather_plot`, additionally:
* `matplotlib`, `numpy` for plotting

`weather_server`, additionally:
* `flask`, `gevent` for the web server part.

## Notes

Downloaded data is automatically cached to prevent unnecessary load on the DWD servers. Station-ID lists are cached for 30 days, and weather forecast data ist cached for 1 hour before the next download is initiated.

## References

* The [DWD Open Data](https://www.dwd.de/EN/ourservices/opendata/opendata.html) project.
* [A list of all weather stations supported by DWD](https://www.dwd.de/DE/leistungen/klimadatendeutschland/statliste/statlex_html.html?view=nasPublication&nn=16102)
* [Documentation for the weather station list](https://www.dwd.de/DE/leistungen/klimadatendeutschland/stationsliste.html)
* [Documentation of forecast data format](https://opendata.dwd.de/weather/lib/MetElementDefinition.xml)
