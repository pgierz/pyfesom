import click
from netCDF4 import Dataset, MFDataset, num2date
import matplotlib as mpl
mpl.use('Qt4Agg')
#%matplotlib inline
import matplotlib.pylab as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cmocean import cm as cmo
from matplotlib import cm
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
import pyfesom as pf
from cartopy.util import add_cyclic_point

@click.command()
@click.argument('meshpath', type=click.Path(exists=True))
@click.argument('ifile', type=click.Path(exists=True))
@click.argument('variable', default='temp', required=False)
@click.option('--depth', '-d', default=0, type=click.FLOAT, show_default=True,
               help='Depth in meters.')
@click.option('--box', '-b',
              nargs=4,
              type=(click.IntRange(-180, 180),
                    click.IntRange(-180, 180),
                    click.IntRange(-90, 90),
                    click.IntRange(-90, 90)),
             default=(-180,180,-80,90), show_default=True,
             help='Map boundaries in -180 180 -90 90 format.')
@click.option('--res', '-r', nargs=2,
              type=(click.INT, click.INT),
              default=(360, 170), show_default=True,
              help='Number of points along each axis (for lon and  lat).')
@click.option('--influence','-i', default=80000, show_default=True,
              help='Radius of influence for interpolation, in meters.')
@click.option('--timestep', '-t', default=0, show_default=True,
              help='Timstep from netCDF variable, strats with 0.')
@click.option('--levels', '-l', nargs=3, type=click.FLOAT,
              help='Levels for contour plot in format min max numberOfLevels.\
 If not provided min/max values from data will be used with 40 levels.')
@click.option('--quiet', '-q', is_flag=True,
              help='If present additional information will not be printed.')
@click.option('--ofile', '-o', type=click.Path(exists=False),
              help='Path to the output figure. If present the image\
 will be saved to the file instead of showing it. ')
@click.option('--mapproj','-m', type=click.Choice(['merc', 'pc', 'np', 'sp', 'rob']),
              default='merc')
@click.option('--abg', nargs=3, type=(click.FLOAT,
                    click.FLOAT,
                    click.FLOAT), default=(50, 15, -90))
@click.option('--clim','-c', type=click.Choice(['phc', 'woa05', 'gdem']),
              help='Select climatology to compare to. If option is set the model bias to climatology will be shown.')
@click.option('--cmap', help='Name of the colormap from cmocean package or from the standard matplotlib set. By default `Spectral_r` will be used for property plots and `balance` for bias plots.')
def showfile(ifile, variable, depth,
             meshpath, box, res, influence,
             timestep, levels, quiet, ofile, mapproj, abg, clim, cmap):
    '''
    meshpath - Path to the folder with FESOM1.4 mesh files.

    ifile    - Path to FESOM1.4 netCDF file.

    variable - The netCDF variable to be plotted.
    '''
    if not quiet:
        click.secho('Mesh: {}'.format(meshpath))
        click.secho('File: {}'.format(ifile))
        click.secho('Variable: {}'.format(variable), fg='red')
        click.secho('Depth: {}'.format(depth), fg='red')
        click.secho('BOX: {}'.format(box))
        click.secho('Resolution: {}'.format(res))
        click.secho('Influence raduis: {} meters'.format(influence), fg='red')
        click.secho('Timestep: {}'.format(timestep))
        if levels:
            click.secho('Levels: {}'.format(levels), fg='red')
        else:
            click.secho('Levels: auto', fg='red')
    
    if cmap:
        if cmap in cmo.cmapnames:
            colormap = cmo.cmap_d[cmap]
        elif cmap in plt.cm.datad:
            colormap = plt.get_cmap(cmap)
        else:
            raise ValueError('Get unrecognised name for the colormap `{}`. Colormaps should be from standard matplotlib set of from cmocean package.'.format(cmap))
    else:
        if clim:
            colormap = cmo.cmap_d['balance']
        else:
            colormap = plt.get_cmap('Spectral_r')

    
    sstep = timestep
    radius_of_influence = influence

    left, right, down, up = box
    lonNumber, latNumber = res

    mesh = pf.load_mesh(meshpath, abg=abg, usepickle=False, usejoblib=True)
    flf = Dataset(ifile)
    lonreg = np.linspace(left, right, lonNumber)
    latreg = np.linspace(down, up, latNumber)
    lonreg2, latreg2 = np.meshgrid(lonreg, latreg)
    
    dind=(abs(mesh.zlevs-depth)).argmin()
    realdepth = mesh.zlevs[dind]

    level_data, nnn = pf.get_data(flf.variables[variable][sstep], mesh, realdepth)
    ofesom = pf.fesom2regular(level_data, mesh, lonreg2, latreg2, radius_of_influence=radius_of_influence)

    if clim:
        if variable=='temp':
            climvar = 'T'
        elif variable == 'salt':
            climvar = 'S'
        else:
            raise ValueError('You have selected --clim/-c option, but variable `{}` is not in climatology. Acceptable values are `temp` and `salt` only.'.format(variable))
        #os.path.join(os.path.dirname(__file__), "../")
        pathToClim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/")
        print(pathToClim)
        w = pf.climatology(pathToClim, clim)
        xx, yy, oclim = pf.clim2regular(w, climvar, lonreg2, latreg2, levels=[realdepth],
                                     radius_of_influence=radius_of_influence)
        oclim = oclim[0, :, :]
        data = ofesom - oclim
    else:
        data = ofesom
    

    
    if mapproj == 'merc':
        ax = plt.subplot(111, projection=ccrs.Mercator())
    elif mapproj == 'pc':
        ax = plt.subplot(111, projection=ccrs.PlateCarree())
    elif mapproj == 'np':
        ax = plt.subplot(111, projection=ccrs.NorthPolarStereo())
    elif mapproj == 'sp':
        ax = plt.subplot(111, projection=ccrs.SouthPolarStereo())
    elif mapproj == 'rob':
            ax = plt.subplot(111, projection=ccrs.Robinson())

    ax.set_extent([left, right, down, up], crs=ccrs.PlateCarree())


    if levels:
        mmin, mmax, nnum = levels
        nnum = int(nnum)
    else:
        mmin = np.nanmin(data)
        mmax = np.nanmax(data)
        nnum = 40


    data_levels = np.linspace(mmin, mmax, nnum)

    mm = ax.contourf(lonreg,\
                     latreg,\
                     data,
                     levels = data_levels,
                     transform=ccrs.PlateCarree(),
                     cmap=colormap,
                    extend='both')
    ax.coastlines(resolution = '50m',lw=0.5)
    ax.add_feature(cfeature.GSHHSFeature(levels=[1], scale='low', facecolor='lightgray'))
    cb = plt.colorbar(mm, orientation='horizontal', pad=0.03)
    plt.title('{} at {}m'.format(variable, realdepth))
    plt.tight_layout()
    if ofile:
        plt.savefig(ofile, dpi=100)
    else:
        plt.show()

if __name__ == '__main__':
    showfile()