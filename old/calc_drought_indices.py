"""
TEST
"""

import regionmask
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# load data
largefilepath = '/net/so4/landclim/bverena/large_files/station_network/'
modelname = 'CanESM5'
experimentname = 'ssp585'
ensemblename = 'r1i1p1f1'
orig = xr.open_dataset(f'{largefilepath}mrso_orig_{modelname}_{experimentname}_{ensemblename}.nc')['mrso']
experimentname = 'historical'
pred = xr.open_dataset(f'{largefilepath}mrso_hist_{modelname}_{experimentname}_{ensemblename}.nc')['mrso']
prednew = xr.open_dataset(f'{largefilepath}mrso_histnew_{modelname}_{experimentname}_{ensemblename}.nc')['mrso']
benchmark = xr.open_dataset(f'{largefilepath}mrso_benchmark_{modelname}_{experimentname}_{ensemblename}_euler.nc')['mrso'] # debug USE EULER

# select identical time period
orig = orig.sel(time=slice('1960','2014'))
pred = pred.sel(time=slice('1960','2014'))
benchmark = benchmark.sel(time=slice('1960','2014'))

# normalise
def standardised_anom(data):
    data_seasonal_mean = data.groupby('time.month').mean()
    data_seasonal_std = data.groupby('time.month').std()
    data = (data.groupby('time.month') - data_seasonal_mean) 
    data = data.groupby('time.month') / data_seasonal_std
    return data

orig = standardised_anom(orig)
pred = standardised_anom(pred)
prednew = standardised_anom(prednew)
benchmark = standardised_anom(benchmark)

# extract 10% driest values, boolean drought occurrence
#orig_drought = orig.where(orig < orig.quantile(0.1))
#pred_drought = pred.where(pred < pred.quantile(0.1))
#benchmark_drought = benchmark.where(benchmark < benchmark.quantile(0.1))
orig_drought = orig < orig.quantile(0.1)
pred_drought = pred < pred.quantile(0.1)
benchmark_drought = benchmark < benchmark.quantile(0.1)

# plot correlation
r2_benchmark = (xr.corr(orig, benchmark, dim='time')**2)
r2_pred = (xr.corr(orig, pred, dim='time')**2)
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(10,3))
ax1 = fig.add_subplot(131, projection=proj)
ax2 = fig.add_subplot(132, projection=proj)
ax3 = fig.add_subplot(133, projection=proj)
ax1.coastlines()
ax2.coastlines()
ax3.coastlines()
cbar_kwargs = {'orientation': 'horizontal', 'label': 'R2'}
r2_benchmark.plot(ax=ax1, cmap='Greens', vmin=0, vmax=1, add_colorbar=True, cbar_kwargs=cbar_kwargs)
r2_pred.plot(ax=ax2, cmap='Greens', vmin=0, vmax=1, add_colorbar=True, cbar_kwargs=cbar_kwargs)
(r2_benchmark - r2_pred).plot(ax=ax3, cmap='coolwarm', vmin=-0.3, vmax=0.3, add_colorbar=True, cbar_kwargs={'orientation': 'horizontal', 'label': 'R2 (benchmark ) - R2 (pred)'})
ax1.set_title('R2 orig ~ benchmark')
ax2.set_title('R2 orig ~ upscaled')
ax3.set_title('R2 diff')
plt.show()
#plt.savefig('r2_upscaling.png')
#quit()

# plot mean drought intensity
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(10,3))
fig.suptitle('global distribution of 10% driest values, mean per gridcell')
ax1 = fig.add_subplot(131, projection=proj)
ax2 = fig.add_subplot(132, projection=proj)
ax3 = fig.add_subplot(133, projection=proj)
ax1.coastlines()
ax2.coastlines()
ax3.coastlines()
vmin=0
vmax=170
orig_drought.sum(dim='time').plot(ax=ax1, cmap='hot_r', add_colorbar=True, cbar_kwargs={'orientation': 'horizontal', 'label': 'mean standardised soil moisture anomaly during drought'}, vmin=vmin, vmax=vmax)
benchmark_drought.sum(dim='time').plot(ax=ax2, cmap='hot_r',  add_colorbar=False, vmin=vmin, vmax=vmax)
pred_drought.sum(dim='time').plot(ax=ax3, cmap='hot_r', add_colorbar=False, vmin=vmin, vmax=vmax)
ax1.set_title('orig')
ax2.set_title('benchmark')
ax3.set_title('upscaled')
plt.show()
#plt.savefig('drought_upscaling.png')

# plot mean drought intensity rmse
orig_sum = orig_drought.sum(dim='time')
pred_sum = pred_drought.sum(dim='time')
benchmark_sum = benchmark_drought.sum(dim='time')

mae_irreducible = np.abs(orig_sum - benchmark_sum)
mae_represent = np.abs(orig_sum - pred_sum)
mae_diff = mae_represent - mae_irreducible

proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(10,3))
fig.suptitle('global distribution of 10% driest values, mean per gridcell')
ax1 = fig.add_subplot(131, projection=proj)
ax2 = fig.add_subplot(132, projection=proj)
ax3 = fig.add_subplot(133, projection=proj)
ax1.coastlines()
ax2.coastlines()
ax3.coastlines()
vmin= 0
vmax= 50
mae_irreducible.plot(ax=ax1, cmap='Reds', vmin=vmin, vmax=vmax, add_colorbar=True, cbar_kwargs={'orientation': 'horizontal', 'label': 'mean standardised soil moisture anomaly during drought'})
mae_represent.plot(ax=ax2, cmap='Reds', vmin=vmin, vmax=vmax, add_colorbar=False)
(mae_represent - mae_irreducible).plot(ax=ax3, cmap='coolwarm', add_colorbar=True, cbar_kwargs={'orientation': 'horizontal'})
ax1.set_title('irreducible error')
ax2.set_title('representation error')
ax3.set_title('positive: large repr div')
plt.show()

# investivage mae diff
data = xr.open_dataset(f'{largefilepath}df_gaps.nc')['__xarray_dataarray_variable__']
lat_cmip = []
lon_cmip = []
for lat, lon in zip(data.lat, data.lon):
    point = mae_diff.sel(lat=lat, lon=lon, method='nearest')
    lat_cmip.append(point.lat.item())
    lon_cmip.append(point.lon.item())
data = data.assign_coords(lat_cmip=('stations',lat_cmip))
data = data.assign_coords(lon_cmip=('stations',lon_cmip))

fig = plt.figure()
ax = fig.add_subplot(111, projection=proj)
mae_diff.plot(ax=ax)
ax.scatter(data.lon_cmip, data.lat_cmip, transform=proj)
ax.coastlines()
plt.show()

# mae diff per koeppen climate
fig = plt.figure()
fig.suptitle('Difference between RMSE of mean soil moisture anomaly (10% driest values globally) of CMIP-U and CMIP-B')
ax1 = fig.add_subplot(121, projection=proj)
ax2 = fig.add_subplot(122)

orig_drought = orig.where(orig < orig.quantile(0.1))
pred_drought = pred.where(pred < pred.quantile(0.1))
prednew_drought = prednew.where(prednew < prednew.quantile(0.1))
benchmark_drought = benchmark.where(benchmark < benchmark.quantile(0.1))
import IPython; IPython.embed()

#def rmse_skill(orig, benchmark, predict):
#    rmse_benchmark = np.sqrt(((orig_drought - benchmark_drought)**2).mean(dim='time'))
#    rmse_predict = np.sqrt(((orig_drought - pred_drought)**2).mean(dim='time'))
#    score = 1 - (rmse_predict / rmse_benchmark)
#    return score
#
#skill_pred = rmse_skill(orig_drought, benchmark_drought, pred_drought)
#skill_prednew = rmse_skill(orig_drought, benchmark_drought, prednew_drought)
rmse_irreducible = np.sqrt(((orig_drought - benchmark_drought)**2).mean(dim='time'))
rmse_repr = np.sqrt(((orig_drought - pred_drought)**2).mean(dim='time'))
rmse_repr_new = np.sqrt(((orig_drought - prednew_drought)**2).mean(dim='time'))
rmse_diff = rmse_repr - rmse_irreducible
rmse_diffnew = rmse_repr_new - rmse_irreducible
rmse_diff.plot(ax=ax1, cbar_kwargs={'orientation': 'horizontal', 'label': 'RMSE difference'})
ax1.coastlines()
ax1.set_title('')

koeppen_simple = xr.open_dataset(f'{largefilepath}koeppen_simple.nc')['__xarray_dataarray_variable__']
import xesmf as xe
regridder = xe.Regridder(rmse_diff, koeppen_simple, 'bilinear', reuse_weights=False)
koeppen_names = ['Af','Am','Aw','BW','BS','Cs','Cw','Cf','Ds','Dw','Df']
rmse_diff = regridder(rmse_diff)
rmse_diffnew = regridder(rmse_diffnew)
koeppen_rmse = []
koeppen_rmse_new = []
n_koeppen = list(range(1,12))
koeppen_density = [3.3126, 2.4572, 3.5573, 9.6494, 23.995, 117.3616, 2.8483, 41.2927, 60.6654, 29.6423, 37.4495]
for k in n_koeppen:
    mae_tmp = rmse_diff.where(koeppen_simple == k, np.nan)
    koeppen_rmse.append(mae_tmp.mean().item())
    mae_tmp = rmse_diffnew.where(koeppen_simple == k, np.nan)
    koeppen_rmse_new.append(mae_tmp.mean().item())
#fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(5,5))
#fig.suptitle('koeppen climate classes')
ax2.scatter(koeppen_density, koeppen_rmse, c='blue')
ax2.scatter(koeppen_density, koeppen_rmse_new, c='red')
for i,(x,y) in enumerate(zip(koeppen_density,koeppen_rmse)):
    ax2.annotate(koeppen_names[i], xy=(x,y))
for i,(x,y) in enumerate(zip(koeppen_density,koeppen_rmse_new)):
    ax2.annotate(koeppen_names[i], xy=(x,y))
ax2.set_ylabel('RMSE difference')
ax2.set_xlabel('station density [bio km^2]')
ax2.set_title('Per Koeppen climate')
plt.show()
import IPython; IPython.embed()

# for each of the five koeppen climates with largest RMSE, point with largest RMSE
# five koeppen with largest RMSE: Af, Am, Dw, Df, Aw
# five points in these climates with largest RMSE among climate:
# Af: (177, 242) latlon: 1.25, -58.75 latloncmip: 1.25 -58.75
# Am : (177, 243) latlon: 1.25, -58.25 latloncmip:  1.25 -58.75 REJECTED
# Am: (third largest value) latlon: 1.25 60.35 latloncmip: 1.25 -61.25
# Aw:  (174, 240) latlon: 2.75, -59.75 latloncmip: 3.75 -58.75
# Dw: (47, 637) latlon: 66.25, 138.8 latloncmip: 66.25 138.8
# Df: (52, 668) latlon: 63.75, 154.2 latloncmip: 63.75 153.8


# define drought as driest 10% of values for each of the datasets individually
#orig_perc = orig.groupby('time.month').quantile(0.1)
#pred_perc = pred.groupby('time.month').quantile(0.1)
#
## mask non-drought values
#orig_drought = orig.groupby('time.month').where(orig.groupby('time.month') < orig_perc) 
#pred_drought = pred.groupby('time.month').where(pred.groupby('time.month') < pred_perc)
#
## set percentile to zero: soil moisture anomalies above drought threshold in mm
#orig_drought = (orig_drought.groupby('time.month') - orig_perc)*(-1)
#pred_drought = (pred_drought.groupby('time.month') - pred_perc)*(-1)
#import IPython; IPython.embed()

#orig_perc = orig.quantile(0.1, dim='time')
#orig_drought = (orig - orig_perc)
#orig_drought = orig_drought.where(orig_drought < 0, 0)
##pred_perc = pred.quantile(0.1, dim='time') # two options, this one is harder, show that not only the maginutide is off (same percentiles) but also some droughts are missed outside of well-observed spaces (different percentiles)
#pred_drought = (pred - pred_perc)
#pred_drought = pred_drought.where(pred_drought < 0, 0)

# drought indices: duration, severity, frequency, extent 
# TODO also do severity and duration, but for now only frequency and extent
#pred_bool = (pred_drought < 0)*1 # True (1) is drought
#orig_bool = (orig_drought < 0)*1 # True (1) is drought
#
#proj = ccrs.PlateCarree()
#fig = plt.figure(figsize=(10,3))
#ax1 = fig.add_subplot(121, projection=proj)
#ax2 = fig.add_subplot(122, projection=proj)
#ax1.coastlines()
#ax2.coastlines()
#(orig_bool.diff(dim='time') == 1).sum(dim='time').plot(ax=ax1, vmin=0, vmax=60, cmap='hot_r')
#(pred_bool.diff(dim='time') == 1).sum(dim='time').plot(ax=ax2, vmin=0, vmax=60, cmap='hot_r')
#plt.show()


# look at drought pattern per region
#mask = regionmask.defined_regions.ar6.all.mask(orig)
#res = xr.full_like(mask, np.nan)
##orig_freq = orig_drought != 0
##pred_freq = pred_drought != 0
##drought_underestimation = (orig_freq.groupby('time.year').sum() - pred_freq.groupby('time.year').sum()) # underestimation is positive
#for i in range(58):
#    tmp = orig_drought.where(mask == i).mean(dim=('lat','lon')) - pred_drought.where(mask == i).mean(dim=('lat','lon'))
#    res = res.where(mask != i, tmp.sum().item())
#
#import IPython; IPython.embed()
#
## plot 
quit()
proj = ccrs.PlateCarree()
for t, time in enumerate(pred_drought.time):
    fig = plt.figure(figsize=(10,3))
    fig.suptitle(f'{str(time.values)[:7]}')
    ax1 = fig.add_subplot(121, projection=proj)
    ax2 = fig.add_subplot(122, projection=proj)
    orig_drought.sel(time=time).plot(ax=ax1, cmap='hot', add_colorbar=False, vmin=-3, vmax=-1.5)
    pred_drought.sel(time=time).plot(ax=ax2, cmap='hot', add_colorbar=False, vmin=-3, vmax=-1.5)
    ax1.set_title('orig')
    ax2.set_title('upscaled')
    ax1.coastlines()
    ax2.coastlines()
    plt.show()
    #plt.savefig(f'drought_gif/drought_evolution_{t:03d}.png')
    plt.close()
