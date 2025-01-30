"# Pearson Correlation Script" 
import os
import rasterio
from preprocess import clip_raster_to_shape, resample_to_target
from correlation import calculate_pixelwise_pearson

# Define paths
data_folder = 'D:/PhDActivity/Correlation/INPUT'
shapefile = 'D:/PhDActivity/Correlation/CampaniaBorderShp/Campania.shp'
output_folder = 'D:/PhDActivity/Correlation/OUTPUT'
os.makedirs(output_folder, exist_ok=True)

# Paths to raw data
lst_folder = os.path.join(data_folder, 'MedianLST')
ndvi_folder = os.path.join(data_folder, 'MedianNDVI')
chirps_folder = os.path.join(data_folder, 'MedianCHIRPS')
burnt_folder = os.path.join(data_folder, 'BurntArea')

lst_files = sorted([os.path.join(lst_folder, f) for f in os.listdir(lst_folder) if f.endswith('.tif')])
ndvi_files = sorted([os.path.join(ndvi_folder, f) for f in os.listdir(ndvi_folder) if f.endswith('.tif')])
chirps_files = sorted([os.path.join(chirps_folder, f) for f in os.listdir(chirps_folder) if f.endswith('.tif')])
burnt_files = sorted([os.path.join(burnt_folder, f) for f in os.listdir(burnt_folder) if f.endswith('.tif')])

# Clip rasters to study area
clipped_lst_files = [clip_raster_to_shape(f, shapefile, os.path.join(output_folder, f'clipped_{os.path.basename(f)}')) for f in lst_files]
clipped_ndvi_files = [clip_raster_to_shape(f, shapefile, os.path.join(output_folder, f'clipped_{os.path.basename(f)}')) for f in ndvi_files]
clipped_chirps_files = [clip_raster_to_shape(f, shapefile, os.path.join(output_folder, f'clipped_{os.path.basename(f)}')) for f in chirps_files]
clipped_burnt_files = [clip_raster_to_shape(f, shapefile, os.path.join(output_folder, f'clipped_{os.path.basename(f)}')) for f in burnt_files)]

# Resample LST, NDVI, and Burnt Area to CHIRPS resolution
resampled_lst_files = [resample_to_target(f, clipped_chirps_files[0], os.path.join(output_folder, f'resampled_{os.path.basename(f)}')) for f in clipped_lst_files]
resampled_ndvi_files = [resample_to_target(f, clipped_chirps_files[0], os.path.join(output_folder, f'resampled_{os.path.basename(f)}')) for f in clipped_ndvi_files]
resampled_burnt_files = [resample_to_target(f, clipped_chirps_files[0], os.path.join(output_folder, f'resampled_{os.path.basename(f)}')) for f in clipped_burnt_files]

# Compute Pearson correlation
with rasterio.open(resampled_ndvi_files[0]) as ndvi_src, rasterio.open(resampled_burnt_files[0]) as burnt_src:
    ndvi_stack = ndvi_src.read()
    burnt_stack = burnt_src.read()
    profile = ndvi_src.profile
    calculate_pixelwise_pearson(ndvi_stack, burnt_stack, os.path.join(output_folder, 'pearson_ndvi_burnt.tif'), profile)

