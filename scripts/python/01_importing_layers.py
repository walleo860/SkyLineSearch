import sys 

project = QgsProject.instance()
project_file_path = project.fileName()
project_directory = os.path.dirname( project_file_path)
sys.path.append( project_directory + '/scripts/qgis')

from qgis.core import QgsCoordinateReferenceSystem
from osgeo import ogr, gdal
import os
import functions.project_setup as ps
import functions.data_processing as dp
import pdb
import logging

# Define the EPSG code of the CRS you want to set
epsg_code = 'EPSG:26912'  # For example, WGS 84

# Create a QgsCoordinateReferenceSystem object using the EPSG code
crs = QgsCoordinateReferenceSystem(epsg_code)

# Set the project CRS to the defined CRS
QgsProject.instance().setCrs(crs)

shapefile = project_directory + '/shapefiles/'
#open_grass_mapset( shapefile + )
# Specify the path to your vector file
raw =  shapefile + 'raw/'
raw_data = project_directory + "/data/raw/"
processed = raw.replace( 'raw', 'processed')
outs = raw.replace( 'raw', 'outputs')

anchors = "/highline_anchor_shapefile.shp"
states = 'cb_2018_us_state_500k.shp'
anchor_csv = raw_data + 'highline_point_data.csv'
#'C:\Users\Walte\Documents\github\highline_search\shapefiles\raw\S_USA.AdministrativeForest.shp'
fs_land = 'S_USA.AdministrativeForest.shp'
blm_land = 'BLM_Natl_Recreation_Site_Polygons.shp'


log_file = project_directory + '/logs/' +'project_setup.log'
#check if log file exists, if not create it
if not os.path.exists(log_file):
    open( log_file, 'w').close()
    logging.basicConfig(
    filename = log_file,
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s: %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
    )
    ps.update_last_run_time( log_file)



last_modification_time = ps.get_file_modification_time( anchor_csv)
last_run_time = ps.get_last_run_time(log_file)



if last_modification_time >= last_run_time:
    print( 'Detected Modification to Source CSV')
    print( 'Converting CSV to Shapefile')
    #The New data entry app writes a csv to t
    ps.convert_csv_to_shapefile( anchor_csv, raw + anchors)
    #shiny_data = len( pd.read_csv( raw_data + 'highline_point_data.csv'))
    layer = QgsVectorLayer( raw + anchors, '', 'ogr')
    basic_crs = QgsCoordinateReferenceSystem( 'EPSG:4326')
    layer.setCrs( basic_crs)
    writer = QgsVectorFileWriter.writeAsVectorFormat(layer, raw + anchors, 'utf-8', basic_crs, 'ESRI Shapefile')
    ps.reproject_shapefile( raw + anchors, processed + anchors, epsg_code)
    iface.addVectorLayer( processed + anchors, 'highline_anchors', 'ogr')  
    ps.add_id_column('highline_anchors', 'line_id')
else:
    iface.addVectorLayer( outs + 'highline_anchors.shp', 'highline_anchors', 'ogr')
    iface.addVectorLayer( outs + 'highline_anchors_points.shp', 'highline_anchors_points', 'ogr')



if states not in os.listdir( processed):
    ps.reproject_shapefile( raw + states, processed + states, epsg_code)
if fs_land not in os.listdir( processed):
    ps.reproject_shapefile( raw + fs_land, processed + fs_land, epsg_code)
if blm_land not in os.listdir( processed):
    ps.reproject_shapefile( raw + blm_land, processed + blm_land, epsg_code)


#gdb = 'SMA_WM.gdb'
#gdb_path = raw + gdb
## Open the Geodatabase
#gdb = ogr.Open(gdb_path)
#
## Check if the Geodatabase was opened successfully
#if gdb is None:
#    print("Failed to open Geodatabase!")
#else:
#    # Get the number of layers (feature classes) within the Geodatabase
#    num_layers = gdb.GetLayerCount()
#    layer_names = []
#    # Loop through each layer (feature class) and print its name
#    for i in range(num_layers):
#        layer = gdb.GetLayerByIndex(i)
#        layer_name = layer.GetName()
#        layer_names.append( layer_name)
#
## Close the Geodatabase
#gdb = None

#Load state and province outlines
iface.addVectorLayer(  processed + states, 'United States', 'ogr')
iface.addVectorLayer(  processed + fs_land, 'Forest Service Land', 'ogr')
iface.addVectorLayer( processed + blm_land, 'BLM Land', 'ogr')

#iface.addVectorLayer( canada, 'Canada', 'ogr')

#loop through each layer name and add it from the GDB
#for layer_name in layer_names:    
#    layer = QgsVectorLayer( gdb_path, layer_name, 'ogr')
#    QgsProject.instance().addMapLayer(layer)

#add highline anchors
#iface.addVectorLayer( processed + anchors, 'highline_anchors', 'ogr')
#add an ID for these features



#if 'highline_anchors_points.shp' in os.listdir( outs):
#    iface.addVectorLayer( outs + 'highline_anchors_points.shp', 'highline_anchors_points', 'ogr')
#else:
if last_modification_time >= last_run_time:
    #create a point layer of each line with points seperated by 1 meter
    dp.lines_to_points( 'highline_anchors', 'highline_anchors_points', 'line_id')
    #give this layer an ID column
    ps.add_id_column('highline_anchors_points', 'id')
    #group points into clusters for to reduce computation diurring rasterization
    dp.cluster_points_with_dbscan("highline_anchors_points", eps=0.004, min_samples=15)
    #color points catagoricly based on cluster_group
    ps.apply_categorized_symbology("highline_anchors_points", "cluster_group")

#Convert all layers to Project CRS
all_layers = QgsProject.instance().mapLayers().values()

for layer in all_layers:
    # Set projection only for vector layers
    if layer.type() == QgsMapLayer.VectorLayer and layer.name() == 'highline_anchors':
        crs = QgsCoordinateReferenceSystem( epsg_code)
        layer.setCrs(crs)

        # Print the name of the layer and its projection after setting
        print("Layer Name:", layer.name())
        print("Layer Projection:", layer.crs().authid())

 #Refresh the map canvas to update the changes
iface.mapCanvas().refreshAllLayers()


original_layers = QgsProject.instance().mapLayers().values()

print( '----Finished Importing Initial Layers----')

