"""
number of stations per year vs prediction uncertainty and error
"""

import numpy as np
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import cartopy.crs as ccrs
import xarray as xr

largefilepath = '/net/so4/landclim/bverena/large_files/'
stations = pd.read_csv(f'{largefilepath}station_info_grid.csv')
case = 'latlontime'

# get number of stations per year
start_year = []
end_year = []
for s in range(stations.shape[0]):
    start_year.append(int(stations.start[s][:4]))
    end_year.append(int(stations.end[s][:4]))

start_year = np.array(start_year)
end_year = np.array(end_year)

no_stations = []
for year in np.arange(1950,2021):
    no_stations.append(((year >= start_year) & (year <= end_year)).sum())

no_years = []
for start, end in zip(stations.start, stations.end):
    no_years.append(pd.date_range(start,end,freq='y').shape[0])

# 3d plot station coverage
data = xr.open_dataset(largefilepath + 'era5_deterministic_recent.var.025deg.1y.mean.nc')
pltarr = xr.full_like(data['e'], 0)
stations.start = [datetime.strptime(date, '%Y-%m-%d %M:%S:%f') for date in stations.start]
stations.end = [datetime.strptime(date, '%Y-%m-%d %M:%S:%f') for date in stations.end]
for lat, lon, start, end in zip(stations.lat_grid, stations.lon_grid, stations.start, stations.end):
    pltarr.loc[slice(start,end),lat,lon] = 1
fig = plt.figure()
z,x,y = pltarr.values.nonzero()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(x, y, -z, zdir='z', c= 'red')
plt.show()

# plot statistcs on stations
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(10,5))
ax1 = fig.add_subplot(131, projection=proj)
ax2 = fig.add_subplot(132, projection=proj)
ax3 = fig.add_subplot(133, projection=proj)
ax1.coastlines()
ax2.coastlines()
ax3.coastlines()
ax1.set_title('length of observation period [years]')
ax2.set_title('start of observation period [year]')
ax3.set_title('end of observation period [year]')
sc = ax1.scatter(stations.lon,stations.lat, c=no_years, cmap='Greens', s=0.5, vmin=1, vmax=40)
plt.colorbar(sc, ax=ax1)
sc = ax2.scatter(stations.lon,stations.lat, c=start_year, cmap='Greens', s=0.5, vmin=1950, vmax=2021)
plt.colorbar(sc, ax=ax2)
sc = ax3.scatter(stations.lon,stations.lat, c=end_year, cmap='Greens', s=0.5, vmin=1950, vmax=2021)
plt.colorbar(sc, ax=ax3)
plt.show()

