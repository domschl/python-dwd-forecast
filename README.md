# python-dwd-forecast

Detailed weather forecast from DWD (Deutscher Wetter Dienst)

This provides:

* a module to download German weather forecasts (10 days, 1 hour resolution) as pandas dataframe
* a module to generate a forecast plot
* a module to serve the forecast plot via web server for integration in home automation panels or similar

![weather](https://github.com/domschl/python-dwd-forecast/blob/master/resources/weather.png)

The plot shows detailed temperature forecasts and sunshine probabilites (yellow) and rain probabilities (blue).

Have a look at the [jupyter notebook](https://github.com/domschl/python-dwd-forecast/blob/master/tests.ipynb) for an overview of the functionality.

## `dwd_forecast`: download and normalize weather data

### Find your station id

Either use the [reference list](https://www.dwd.de/DE/leistungen/klimadatendeutschland/statliste/statlex_html.html?view=nasPublication&nn=16102) provided by the Open Data project of DWD, or search via location:

```python
from dwd_forecast import DWD
d=DWD()
my_lat, my_lon=(48.15, 11.56)
nearest=d.get_closest(my_lat,my_lon)
print(nearest)
# ('10865', 'München-Stadt', Distance(1.9339969383980125))
```

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
wp.plot("10865",image_file='weather.png')  # station-id 10865 from above.
```

## `weather_server`: your private weather forecast server

```python
from weather_server import WeatherServer
ws = WeatherServer(port=8089, keyfile=my_keyfile, certfile=my_certfile)
while True:
    time.sleep(1)
```
If keyfile and certfile are ommited, the web server serves on http://localhost:8089/station/<id>, e.g. http://localhost:8089/10865. With cert- and keyfile given, https is used: https://hostname:8089/station/10865.

The server simply returns a PNG that can be embedded in other portals (e.g. Home Assistant)

## References

* [A list of all weather stations supported by DWD](https://www.dwd.de/DE/leistungen/klimadatendeutschland/statliste/statlex_html.html?view=nasPublication&nn=16102)
* [Documentation for the weather station list](https://www.dwd.de/DE/leistungen/klimadatendeutschland/stationsliste.html)
* [Documentation of forecast data format](https://opendata.dwd.de/weather/lib/MetElementDefinition.xml)