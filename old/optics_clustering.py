"""
create dataset for investigating optimal station networks

    @author: verena bessenbacher
    @date: 26 05 2020
"""

# decide which variables to use
# temperature, precipitation, evapotranspiration, runoff, soil moisture, sensible heat, carbon fluxes?
# mean, extremes and trends
# constant maps: altitude, topographic complexity, vegetation cover

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from sklearn.cluster import OPTICS

# define time range
years = list(np.arange(1979,2020))
#years = [2000]

# define paths
largefilepath = '/net/so4/landclim/bverena/large_files/'
era5path_variant = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_1m/processed/regrid/'
era5path_invariant = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_time-invariant/processed/regrid/'
era5path_max = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_1h/processed/regrid_tmax1d/'
era5path_min = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_1h/processed/regrid_tmin1d/'
era5path_sum = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_1h/processed/regrid_tsum1d/'
invarnames = ['lsm','z','slor','cvl','cvh', 'tvl', 'tvh']
varnames = ['skt','tp','swvl1','swvl2','swvl3','swvl4','e','ro','sshf','slhf','ssr','str']
varxnames = ['skt','t2m']
varsnames = ['e','tp']

# define files
filenames_var = [f'{era5path_variant}era5_deterministic_recent.{varname}.025deg.1m.{year}.nc' for year in years for varname in varnames]
filenames_max = [f'{era5path_max}era5_deterministic_recent.{varname}.025deg.1h.{year}.tmax1d.nc' for year in years for varname in varxnames]
filenames_min = [f'{era5path_min}era5_deterministic_recent.{varname}.025deg.1h.{year}.tmin1d.nc' for year in years for varname in varxnames]
filenames_sum = [f'{era5path_sum}era5_deterministic_recent.{varname}.025deg.1h.{year}.tsum1d.nc' for year in years for varname in varsnames]
filenames_invar = [f'{era5path_invariant}era5_deterministic_recent.{varname}.025deg.time-invariant.nc' for varname in invarnames]

# open files
data = xr.open_mfdataset(filenames_var, combine='by_coords')
constant_maps = xr.open_mfdataset(filenames_invar, combine='by_coords')
#data_max = xr.open_mfdataset(filenames_max, combine='by_coords').resample(time='1m').max().drop('time_bnds')
#data_max = data_max.rename({'skt':'sktmax','t2m':'t2mmax'})
#data_max = data_max.mean(dim='time')
#data_max.to_netcdf(largefilepath + 'era5_deterministic_recent.temp.025deg.1m.max.nc')
#data_min = xr.open_mfdataset(filenames_min, combine='by_coords').resample(time='1m').min().drop('time_bnds')
#data_min = data_min.rename({'skt':'sktmin','t2m':'t2mmin'})
#data_min = data_min.mean(dim='time')
#data_min.to_netcdf(largefilepath + 'era5_deterministic_recent.temp.025deg.1m.min.nc')
import IPython; IPython.embed()
data_sum = xr.open_mfdataset(filenames_sum, combine='by_coords').resample(time='1m').sum()
data_sum = data_sum.rename({'e':'esum','tp':'tpsum'})
data_sum = data_sum.mean(dim='time')
data_sum.to_netcdf(largefilepath + 'era5_deterministic_recent.precip.025deg.1m.sum.nc')

# create statistics: mean, extreme, trends
datamean = data.to_array().mean(dim='time').to_dataset(dim='variable')

# merge constant maps and variables
landmask = (constant_maps['lsm'].squeeze() > 0.8).load() # land is 1, ocean is 0
landlat, landlon = np.where(landmask)

data = datamean.merge(constant_maps).to_array()
data = data.isel(lon=xr.DataArray(landlon, dims='landpoints'), 
                 lat=xr.DataArray(landlat, dims='landpoints')).squeeze()

# normalise data
datamean = data.mean(dim=('landpoints'))
datastd = data.std(dim=('landpoints'))
data = (data - datamean) / datastd

# first try: clustering
print('clustering')
kmeans = OPTICS().fit(data.T)
labels = kmeans.labels_
print('clustering_finished')

# reshape to worldmap
clustered = xr.full_like(landmask.astype(float), np.nan)
clustered.values[landlat,landlon] = labels

# calculate grid point that contains station
largefilepath = '/net/so4/landclim/bverena/large_files/'
station_coords = pd.read_csv(largefilepath + 'fluxnet_station_coords.csv')
stations_lat = station_coords.LOCATION_LAT.values
stations_lon = station_coords.LOCATION_LONG.values

# find gridpoint where fluxnet station is
def find_closest(list_of_values, number):
    return min(list_of_values, key=lambda x:abs(x-number))
data_lat = np.unique(data['lat'])
data_lon = np.unique(data['lon'])
station_grid_lat = []
station_grid_lon = []
for lat, lon in zip(stations_lat,stations_lon):
    station_grid_lat.append(find_closest(data_lat, lat))
    station_grid_lon.append(find_closest(data_lon, lon))

# plot stations per cluster
station_cluster = []
for lat, lon in zip(station_grid_lat, station_grid_lon):
    station_cluster.append(clustered.sel(lat=lat, lon=lon).values.item())

# plot stations
fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(10,5))
clustered.plot(ax=ax[0], vmin=0, vmax=9, cmap='tab10')
ax[0].scatter(station_grid_lon, station_grid_lat, marker='x', s=5, c='indianred')

ax[1].hist(station_cluster, bins=np.arange(11))
plt.show()
