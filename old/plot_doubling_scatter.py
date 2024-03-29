import xarray as xr
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import regionmask
import numpy as np
import xesmf as xe
from calc_worldarea import calc_area

# TODO
# size of the marker is size of the region

colors = np.array([[81,73,171],[124,156,172],[236,197,140],[85,31,50],[189,65,70],[243,220,124]])
colors = colors/255.
col_random = colors[4,:]
col_swaths = colors[2,:]
col_real = colors[0,:]

# load files
largefilepath = '/net/so4/landclim/bverena/large_files/'
testcase = 'smmask'
metric = 'corr'
corrmaps = xr.open_mfdataset(f'corrmap_systematic_*_{metric}_{testcase}.nc', coords='minimal').squeeze().mrso
niter = xr.open_mfdataset(f'niter_systematic_*_{metric}_{testcase}.nc', coords='minimal').squeeze().mrso
#landmask = xr.open_dataarray(f'{largefilepath}opscaling/landmask.nc').squeeze()
obsmask = xr.open_dataarray(f'{largefilepath}opscaling/obsmask.nc').squeeze()

# extract current and double corr
min_frac = min(corrmaps.frac_observed)
double_frac = min_frac*2
orig = corrmaps.sel(frac_observed=min_frac, method='nearest')
double = corrmaps.sel(frac_observed=double_frac, method='nearest')
orig = orig.mean(dim='model')
double = double.mean(dim='model')

# double mask from niter
niter = niter / niter.max(dim=("lat", "lon")) # removed 1 - ...
meaniter = niter.mean(dim='model')

# calc obsmask
#import IPython; IPython.embed()
#obsmask = (np.isnan(meaniter) & landmask)

# mask for double frac
meaniter = meaniter < double_frac

# regions
landmask = regionmask.defined_regions.natural_earth_v5_0_0.land_110.mask(orig.lon, orig.lat)
regions = regionmask.defined_regions.ar6.land.mask(orig.lon, orig.lat)
regions = regions.where(~np.isnan(landmask))
koeppen = xr.open_dataarray(f'{largefilepath}opscaling/koeppen_simple.nc')
countries = regionmask.defined_regions.natural_earth_v5_0_0.countries_110.mask(orig.lon, orig.lat)
countries = countries.where(~np.isnan(landmask))

# area per grid point
grid = calc_area(regions)

# regrid for koeppen
regridder = xe.Regridder(koeppen, orig, 'bilinear', reuse_weights=False)
koeppen = regridder(koeppen)

# station density current and future
den_ar6_current = obsmask.groupby(regions).sum() / grid.groupby(regions).sum()
den_ar6_future = (obsmask | meaniter).groupby(regions).sum() / grid.groupby(regions).sum()

den_koeppen_current = obsmask.groupby(koeppen).sum() / grid.groupby(koeppen).sum()
den_koeppen_future = (obsmask | meaniter).groupby(koeppen).sum() / grid.groupby(koeppen).sum()

# get region names
countries_names = regionmask.defined_regions.natural_earth_v5_0_0.countries_110.names
region_names = regionmask.defined_regions.ar6.land.abbrevs
koeppen_names = ['Ocean','Af','Am','Aw','BW','BS','Cs','Cw','Cf','Ds','Dw','Df','EF','ET']

# group by region
orig_ar6 = orig.groupby(regions).mean()
orig_koeppen = orig.groupby(koeppen).mean()
orig_countries = orig.groupby(countries).mean()

double_ar6 = double.groupby(regions).mean()
double_koeppen = double.groupby(koeppen).mean()
double_countries = double.groupby(countries).mean()

# drop desert and ice regions from koeppen
orig_koeppen = orig_koeppen.drop_sel(group=[0,4,12,13])
double_koeppen = double_koeppen.drop_sel(group=[0,4,12,13])
den_koeppen_current = den_koeppen_current.drop_sel(group=[0,4,12,13])
den_koeppen_future = den_koeppen_future.drop_sel(group=[0,4,12,13])
koeppen_names = ['Af','Am','Aw','BS','Cs','Cw','Cf','Ds','Dw','Df']

# drop deserts and ice regions from ar6
#less than 10% covered; checked with
#np.array(region_names)[((~np.isnan(double)).groupby(regions).sum().values / xr.full_like(double,1).groupby(regions).sum().values) < 0.1]
ar6_exclude_desertice = [0,20,36,40,44,45]
orig_ar6 = orig_ar6.drop_sel(mask=ar6_exclude_desertice)
double_ar6 = double_ar6.drop_sel(mask=ar6_exclude_desertice)
den_ar6_current = den_ar6_current.drop_sel(mask=ar6_exclude_desertice)
den_ar6_future = den_ar6_future.drop_sel(mask=ar6_exclude_desertice)

# drop ar6 regions where no stations were added for cleaning up plot
ar6_exclude = den_ar6_future.mask[den_ar6_future.squeeze() == 0]
ar6_include = den_ar6_future.mask[den_ar6_future.squeeze() != 0] 
orig_ar6 = orig_ar6.drop_sel(mask=ar6_exclude)
double_ar6 = double_ar6.drop_sel(mask=ar6_exclude)
den_ar6_current = den_ar6_current.drop_sel(mask=ar6_exclude)
den_ar6_future = den_ar6_future.drop_sel(mask=ar6_exclude)

idxs = np.arange(46)
idxs = [idx for idx in idxs if idx not in ar6_exclude_desertice]
idxs = [idx for idx in idxs if idx not in ar6_exclude]
region_names = np.array(region_names)[idxs]

# create legend
a = 0.5
legend_elements = [Line2D([0], [0], marker='o', color='w', 
                   label='current station number', markerfacecolor=col_random,
                   markeredgecolor='black', alpha=a, markersize=10),
                   Line2D([0], [0], marker='o', color='w', 
                   label='globally doubled station number', markerfacecolor=col_random,
                   markeredgecolor=col_random, alpha=1, markersize=10)]

# plot
#fig = plt.figure(figsize=(10,5))
#ax = fig.add_subplot(111)
#
#ax.grid(0.2)
#
#ax.set_title('(c) Koppen-Geiger climates')
#
#for x1,y1,x2,y2 in zip(den_koeppen_current,orig_koeppen,den_koeppen_future,double_koeppen):
#    ax.plot([x1, x2], [y1, y2], c=col_random, alpha=a)
#for label,x,y in zip(koeppen_names, den_koeppen_future, double_koeppen):
#    ax.text(x=x,y=y,s=label)
#ax.scatter(den_koeppen_current,orig_koeppen, c=col_random, edgecolor='black', alpha=a)
#ax.scatter(den_koeppen_future,double_koeppen, c=col_random)
#
#ax.set_xlabel('stations per Mio $km^2$')
#
#ax.set_ylabel('pearson correlation')
#ax.set_ylim([0.2,0.7])
#ax.set_xlim([0,8])
#
#ax. legend(handles=legend_elements)
#
#plt.savefig(f'doubling_scatter_{testcase}.pdf', bbox_inches='tight')

# plot
fig = plt.figure(figsize=(10,10))
ax1 = fig.add_subplot(211)
ax2 = fig.add_subplot(212)

ax1.grid(0.2)
ax2.grid(0.2)

ax1.set_title('(c) Koppen-Geiger climates')
ax2.set_title('(d) AR6 regions')

for x1,y1,x2,y2 in zip(den_koeppen_current,orig_koeppen,den_koeppen_future,double_koeppen):
    ax1.plot([x1, x2], [y1, y2], c=col_random, alpha=a)
for label,x,y in zip(koeppen_names, den_koeppen_future, double_koeppen):
    ax1.text(x=x,y=y,s=label)
ax1.scatter(den_koeppen_current,orig_koeppen, c=col_random, edgecolor='black', alpha=a)
ax1.scatter(den_koeppen_future,double_koeppen, c=col_random)


for x1,y1,x2,y2 in zip(den_ar6_current,orig_ar6,den_ar6_future,double_ar6):
    ax2.plot([x1, x2], [y1, y2], c=col_random, alpha=a)
for label,x,y in zip(region_names, den_ar6_future, double_ar6):
    ax2.text(x=x,y=y,s=label)
ax2.scatter(den_ar6_current,orig_ar6, c=col_random, edgecolor='black', alpha=a)
ax2.scatter(den_ar6_future,double_ar6, c=col_random)


#ax1.set_xlabel('stations per Mio $km^2$')
ax2.set_xlabel('stations per Mio $km^2$')

ax1.set_ylabel('pearson correlation')
ax2.set_ylabel('pearson correlation')
#ax1.set_ylim([0.15,0.9]) # DEBUG
#ax2.set_ylim([0.15,0.9])

ax1. legend(handles=legend_elements)

plt.show()
#plt.savefig(f'doubling_scatter_{testcase}.pdf', bbox_inches='tight')
