"""
TEST
"""

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor

largefilepath = '/net/so4/landclim/bverena/large_files/'
case = 'latlontime'

def to_latlon(data):
    t = data.time.shape[0]
    lsmfile = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_time-invariant/processed/regrid/era5_deterministic_recent.lsm.025deg.time-invariant.nc'
    lsm = xr.open_mfdataset(lsmfile, combine='by_coords')
    shape = lsm['lsm'].squeeze().shape
    landlat, landlon = np.where((lsm['lsm'].squeeze() > 0.8).load()) # land is 1, ocean is 0
    tmp = xr.DataArray(np.full((t,shape[0],shape[1]),np.nan), coords=[data.coords['time'],lsm.coords['lat'], lsm.coords['lon']], dims=['time','lat','lon'])
    tmp.values[:,landlat,landlon] = data
    return tmp

# load data
print('load data')
X_train = xr.open_dataarray(f'{largefilepath}X_train_{case}.nc')
y_train = xr.open_dataarray(f'{largefilepath}y_train_{case}.nc')
X_test = xr.open_dataarray(f'{largefilepath}X_test_{case}.nc')
y_test = xr.open_dataarray(f'{largefilepath}y_test_{case}.nc')

# normalise values
datamean = y_train.mean().values.copy()
datastd = y_train.std().values.copy()
y_train = (y_train - datamean) / datastd
y_test = (y_test - datamean) / datastd

# train RF on observed points 
n_trees = 500
kwargs = {'n_estimators': n_trees,
          'min_samples_leaf': 2,
          'max_features': 'auto', 
          'max_samples': None, 
          'bootstrap': True,
          'warm_start': True,
          'n_jobs': None, # set to number of trees
          'verbose': 0}
rf = RandomForestRegressor(**kwargs)
# TODO idea: add penalty for negative soil moisture?
rf.fit(X_train, y_train)

res = np.zeros((n_trees, X_test.datapoints.shape[0]))
for t, tree in enumerate(rf.estimators_):
    print(t)
    res[t,:] = tree.predict(X_test)
mean = np.mean(res, axis=0)
upper, lower = np.percentile(res, [95 ,5], axis=0)

# predict GP on all other points of grid
y_train_empty = xr.full_like(y_train, np.nan)
y_predict = xr.full_like(y_test, np.nan)
y_unc = xr.full_like(y_test, np.nan)
y_predict[:] = mean
y_unc[:] = (upper - lower)
datamap = to_latlon(xr.concat([y_test, y_train_empty], dim='datapoints').set_index(datapoints=('time', 'landpoints')).unstack('datapoints'))
predmap = to_latlon(xr.concat([y_predict, y_train_empty], dim='datapoints').set_index(datapoints=('time', 'landpoints')).unstack('datapoints'))
uncmap = to_latlon(xr.concat([y_unc, y_train_empty], dim='datapoints').set_index(datapoints=('time', 'landpoints')).unstack('datapoints'))
datamean = xr.open_dataarray(f'{largefilepath}datamean_{case}.nc')
datastd = xr.open_dataarray(f'{largefilepath}datastd_{case}.nc')
datamap = datamap * datastd + datamean
predmap = predmap * datastd + datamean
uncmap = uncmap * datastd 

# save results
datamap.to_netcdf(f'{largefilepath}ERA5_{case}.nc')
predmap.to_netcdf(f'{largefilepath}RFpred_{case}.nc')
uncmap.to_netcdf(f'{largefilepath}UncPred_{case}.nc')
