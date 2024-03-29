import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime

# open data map
largefilepath = '/net/so4/landclim/bverena/large_files/'
data = xr.open_dataarray(f'{largefilepath}df_gaps.nc')

icalc = False
if icalc:
    # load feature space X
    print('load data')
    largefilepath = '/net/so4/landclim/bverena/large_files/'
    era5path_invariant = '/net/exo/landclim/data/dataset/ERA5_deterministic/recent/0.25deg_lat-lon_time-invariant/processed/regrid/'
    invarnames = ['lsm','z','slor','cvl','cvh', 'tvl', 'tvh']
    freq = '1m'
    filenames_constant = [f'{era5path_invariant}era5_deterministic_recent.{varname}.025deg.time-invariant.nc' for varname in invarnames]
    filenames_variable = [f'{largefilepath}era5_deterministic_recent.temp.025deg.{freq}.max.nc', 
                         f'{largefilepath}era5_deterministic_recent.temp.025deg.{freq}.min.nc',
                         f'{largefilepath}era5_deterministic_recent.var.025deg.{freq}.mean.nc',
                         f'{largefilepath}era5_deterministic_recent.var.025deg.{freq}.roll.nc',
                         f'{largefilepath}era5_deterministic_recent.precip.025deg.{freq}.sum.nc']
    #filenames_variable = [f'{largefilepath}era5_deterministic_recent.var.025deg.{freq}.mean.nc']
    constant = xr.open_mfdataset(filenames_constant, combine='by_coords').load()
    variable = xr.open_mfdataset(filenames_variable, combine='by_coords').load()
    landlat, landlon = np.where((constant['lsm'].squeeze() > 0.8).load()) # land is 1, ocean is 0
    datalat, datalon = constant.lat.values, constant.lon.values
    #constant = constant.isel(lon=xr.DataArray(landlon, dims='landpoints'),
    #                         lat=xr.DataArray(landlat, dims='landpoints')).squeeze()
    #variable = variable.isel(lon=xr.DataArray(landlon, dims='landpoints'),
    #                         lat=xr.DataArray(landlat, dims='landpoints')).squeeze()
    #constant['latdat'] = ('landpoints', constant.lat.values)
    #constant['londat'] = ('landpoints', constant.lon.values)
    constant = constant.squeeze()

    # normalise data # for now omitted because expensive
    #print('normalise data')
    #mean = data.mean(dim='time')
    #std = data.std(dim='time')
    #data = (data - mean) / std
    #
    #mean = variable.mean(dim='time')
    #std = variable.std(dim='time')
    #variable = (variable - mean) / std

    # stack constant maps and merge with variables
    print('stack data')
    ntimesteps = variable.coords['time'].size # TODO use climfill package
    constant = constant.expand_dims({'time': ntimesteps}, axis=1)
    constant['time'] = variable['time']
    variable = variable.merge(constant)

    # select only station points in X (variable) data
    print('select stations')
    variable = variable.sel(lat=data.lat_grid, lon=data.lon_grid)

    # rf settings
    n_trees = 50
    kwargs = {'n_estimators': n_trees,
              'min_samples_leaf': 2,
              'max_features': 'auto', 
              'max_samples': None, 
              'bootstrap': True,
              'warm_start': True,
              'n_jobs': 50, # set to number of trees
              'verbose': 0}
    pred = xr.full_like(data, np.nan)

    # stack dimensions time and stations and remove not measured time points per station
    soil = data.stack(datapoints=('time','stations'))
    variable = variable.stack(datapoints=('time','stations'))
    soil = soil.where(~np.isnan(soil), drop=True)
    variable = variable.where(~np.isnan(soil), drop=True).to_array().T

    tmp = []

    for s, station in enumerate(data.stations):
        now = datetime.now()
        print(now, s)

        # define test and train data
        #y_test = data.where(data.stations == station, drop=True)
        X_test = variable.where(soil.stations == station, drop=True)
        y_train = soil.where(soil.stations != station, drop=True)
        X_train = variable.where(soil.stations != station, drop=True)
        if X_test.size < 1:
            tmp.append(s)
            print(f'station {station.item()} skipped no values')
            continue

        # train QRF
        rf = RandomForestRegressor(**kwargs)
        rf.fit(X_train, y_train)

        y_predict = rf.predict(X_test)
        pred.loc[X_test.time,station] = y_predict
        #res = np.zeros((n_trees, X_test.shape[0]))
        #for t, tree in enumerate(rf.estimators_):
        #    res[t,:] = tree.predict(X_test)
        #mean = np.mean(res, axis=0)
        #upper, lower = np.percentile(res, [95 ,5], axis=0)

    pred.to_netcdf(f'{largefilepath}pred_dat.nc') # TODO DEBUG REMOVE
else:
    pred = xr.open_dataset(f'{largefilepath}pred_dat.nc')
    pred = pred['__xarray_dataarray_variable__']

# calculate RMSE of CV # TODO data not yet normalised
#rmse = np.sqrt(((data - pred)**2).mean(dim='time'))
pcorr = xr.corr(data,pred, dim='time')

# plot
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(20,10))
ax = fig.add_subplot(111, projection=proj)
ax.set_title('Correlation of leave-one-out-CV and original station data')
im = ax.scatter(pred.lon, pred.lat, c=pcorr.values, marker='o', s=2, cmap='autumn_r', vmin=0, vmax=1)
cax = fig.add_axes([0.9, 0.2, 0.02, 0.6])
cbar = plt.colorbar(im, cax=cax)
cbar.set_label('correlation')
ax.coastlines()
plt.savefig('leave_one_out.png')
plt.close()

# plot per koeppen climate
koeppen_rmse = []
koeppen_minmax = np.zeros((2,14))
for i in range(14):
    tmp = pcorr.where(data.koeppen_simple == i)
    tmp_median = tmp.median().item()
    koeppen_rmse.append(tmp_median)
    koeppen_minmax[:,i] = tmp_median - np.nanpercentile(tmp, 10), np.nanpercentile(tmp,90) - tmp_median
reduced_names = ['Ocean','Af','Am','Aw','BW','BS','Cs','Cw','Cf','Ds','Dw','Df','ET','EF']
fig = plt.figure()
ax = fig.add_subplot(111)
ax.bar(reduced_names, koeppen_rmse)
ax.set_ylabel('median correlation')
ax.set_ylim([-0.1,1])
plt.savefig('LOO-CV_koeppen.png')
plt.close()

# scatter with station density
density = [3.3126400217852,
 2.4572254418477,
 3.5573204219480,
 9.6494712179372,
 23.995941152118,
 117.36169912495,
 2.8483855557724,
 41.292729367904,
 60.665451036883,
 29.642355656222,
 37.449535740312]

koeppen_rmse = koeppen_rmse[1:-2]
fig = plt.figure()
ax = fig.add_subplot(111)
ax.set_ylim([0,1])
ax.scatter(density, koeppen_rmse)
#ax.errorbar(density, koeppen_rmse, yerr=koeppen_minmax[:,1:], fmt='none')
for n, name in enumerate(reduced_names[1:-2]):
    ax.annotate(name, xy=(density[n], koeppen_rmse[n]))
ax.set_ylabel('median correlation')
ax.set_xlabel('station density [station per bio km^2]')
plt.show()
