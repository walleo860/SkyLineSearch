import os
from qgis.core import QgsProcessingFeatureSourceDefinition, QgsVectorLayer, QgsVectorFileWriter, QgsWkbTypes
from qgis import processing
import functions.project_setup as ps
import functions.data_processing as dp
from osgeo import gdal
import numpy as np
import processing
#list of all layers in proj
all_layers = QgsProject.instance().mapLayers().values()
# Add a new field to the attribute table to store elevations
anchors = ps.select_layers_by_substrings( all_layers, ['highline_anchors'])
anchor_points = ps.select_layers_by_substrings( all_layers, ['highline_anchors_points'])
#State extraction 
#may potentially be able to add other polygons to this 
dp.add_state_to_attribute_table( 'United States', 'highline_anchors', 'state')


# Because USGS topo layers are so large we need to do this in a for loop iterating over each square
# 1) load geopdf for i
# 2) select highlines that exist within said geapdf bounds
# 3) run intersections for trails, streets, railways, hydrology
# 4a) create bounding box for highlines to reduce amount needing rasterization
# 4b) cluster analysis for location to determine how many bounding boxs we need to make
# 5) use bounding box for rasterization
# 6) extract heights
def sample_raster_values(points_layer_name, raster_layer_name, bounding_box_layer_name):
    from qgis.core import (QgsSpatialIndex, QgsFeatureRequest, QgsGeometry, QgsVectorLayer, QgsRasterLayer,
                    QgsVectorFileWriter, QgsFeature, QgsField, QgsCoordinateTransformContext, QgsPointXY,
                    QgsWkbTypes, QgsProject, QgsRaster)
    # Load the point layer
    point_layer = QgsProject.instance().mapLayersByName(points_layer_name)[0]
    
    # Load the raster layer
    raster_layer = QgsProject.instance().mapLayersByName(raster_layer_name)[0]
    
    # Get the bounding box layer
    bounding_box_layer = QgsProject.instance().mapLayersByName(bounding_box_layer_name)[0]
    bounding_box_extent = bounding_box_layer.extent()
    
    # Create a new field to store the elevation values
    point_layer.startEditing()
    if not point_layer.fields().indexFromName('elevation') == -1:
        print("Elevation column already exists.")
        
    
    point_layer.addAttribute(QgsField('elevation', QVariant.Double))
    point_layer.updateFields()
    
    # Iterate over each point feature
    for feature in point_layer.getFeatures():
        point = feature.geometry().asPoint()
    
        # Check if the point is within the bounding box
        if not bounding_box_extent.contains(point):
            continue
    
        # Sample raster value at the point
        value = raster_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[1]
    
        # Update the elevation attribute
        point_layer.changeAttributeValue(feature.id(), point_layer.fields().indexFromName('elevation'), value)
    
    point_layer.commitChanges()
    print("Elevation values sampled and added to the point layer.")
        
        

def reproject_shapefile(input_file, output_file, epsg_code):
    # Load the input layer into QGIS
    input_layer = QgsVectorLayer(input_file, 'input_layer', 'ogr')
    if not input_layer.isValid():
        print("Error: Invalid input layer")
        return
    
    # Create a QgsCoordinateReferenceSystem object using the EPSG code
    crs = QgsCoordinateReferenceSystem(epsg_code)
    
    # Save the reprojected layer to a new file
    QgsVectorFileWriter.writeAsVectorFormat(input_layer, output_file, 'UTF-8', crs, 'ESRI Shapefile')
    
    print("Reprojection completed successfully")


# 7) extract jurisdiction/landtype/land cover 
# 8) remove layers
usgs = 'usgs_shapefiles/'
geopdf_path = raw + 'geopdf/'


usgs_path = raw + usgs
usgs_processed_path = processed + usgs

temp_path = raw.replace( 'raw', 'temp')

#This for loop goes through each zipped usgs sapefile
#   a) Unzips each  
#   b) Extracts wanted layers to processeed folder
#   c) reprojects each layer to the projsects projection CRS

if 'usgs_shapefiles' not in os.listdir( processed):
    os.makedirs( usgs_processed_path, exist_ok=True)
        
    #geopdf_list = os.listdir( geopdf_path)   
    zip_list = os.listdir( usgs_path)
    # US TOPO MAPS FROM: https://www.usgs.gov/the-national-map-data-delivery/gis-data-download
    #                    > topo map data and topo style sheet
    #                    > Shapefile
    
    # You can access this data via API, documentation is here:https://tnmaccess.nationalmap.gov/api/v1/docs
    for zip in zip_list:
        #print( zip)
        if zip.endswith('.zip'):
            #print( 'zip')
            # 1) load shapefiles        
            zip_file_path = usgs_path + zip
            
            location = os.path.basename(zip_file_path).replace( '_7_5_Min_Shape.zip', '').replace( 'VECTOR_', '')
            
            os.makedirs( usgs_processed_path + location + '/', exist_ok=True)
            
            extract_to = usgs_path
            ps.unzip_folder(zip_file_path, extract_to)
            zipped_contents = ps.list_contents(extract_to)
            shp_list = []
            
            for file in zipped_contents:
                if file.endswith('.shp'):
                        if any(substring in file.lower() for substring in ['rail', 'trail', 'road', 'water', 'hydro', 'ele']):
                            basename = os.path.basename( file)
                            reproject_shapefile( file, usgs_processed_path + location + '/' + basename, epsg_code)

anchors = anchors[0]
anchor_points = anchor_points[0]

#In this for loop we loop through each location of the downloaded USGS maps to get 
for location in os.listdir( usgs_processed_path):
    print( '----------------Itterating for ' + location + '----------------')
    print( '1) Loading all layers')
    full_location = usgs_processed_path + location + '/'
    usgs_basenames = []
    for file in os.listdir( full_location):
        if file.endswith( '.shp'):
            basename = os.path.basename(file).replace( '.shp', '')
            usgs_basenames.append( basename)
            if basename == 'Elev_Contour':
                contours_file = file  
            #print( file)    
            iface.addVectorLayer( full_location + file, basename, 'ogr')
            #print( basename + ' loaded correctly')
    #refresh all layers
    all_layers = QgsProject.instance().mapLayers().values()
    #print( all_layers   )
    #get contour layer
    print( 'Selecting contours')
    contours = ps.select_layers_by_substrings( all_layers, ['Contour'])
    #print( contours)
    contours = contours[0]

    
    #export_pdf_layer_to_shp( geopdf_path + i , contours.name(), temp_path + 'contour_shapefile.shp')
    print(  '2) Select highlines that exist within contours')
    
    #debugging
    #if location == 'Electra_Lake_CO':
    #    pdb.set_trace() #equivalent to browser
    
    #get highlines that intersect with contours
    int_indexs = dp.get_intersecting_indexes( 'highline_anchors', 'Elev_Contour')
    #select associated line ids
    line_ids_in_contours = np.unique( ps.select_values_from_index( 'highline_anchors', int_indexs, 'line_id'))
    #use line ids to select indexs from points layer
    points_in_contours = ps.select_indexes_from_values( 'highline_anchors_points', 'line_id', line_ids_in_contours)
    #use indexs to select unique clusters
    clusters = np.unique( ps.select_values_from_index( 'highline_anchors_points', points_in_contours, 'cluster_group'))
    
    #loop through the clusters to reduce computation time from rasterization
    print( 'There are ' + str( len( clusters)) + ' within this layer')
    for z in clusters:
        cluster_layers = []
        #select indexs of points in cluster
        cluster_lines = ps.select_indexes_from_values( 'highline_anchors_points', 'cluster_group', [z])
        #get lines in contours and those in cluster z
        these_lines = list(set(cluster_lines).intersection(points_in_contours))
        #select line_ids in cluster
        line_ids = np.unique( ps.select_values_from_index( 'highline_anchors_points', these_lines, 'line_id'))
        #select indexs from original layer
        line_indexs = ps.select_indexes_from_values( 'highline_anchors', 'line_id', line_ids)     
   
        
        # 4) create bounding box to reduce computation
        print( '3) Creating Bounding Box for cluster ' + str( z))
        bb = dp.get_bounding_box_dimensions( anchors, line_indexs)
        temp_raster = temp_path + 'output_raster.tif'
        bounding_box = QgsRectangle( bb['min_x'],bb['min_y'], bb['max_x'],  bb['max_y'])
        bb_path = temp_path + 'raster_bb.shp'
        dp.create_polygon_layer_from_bbox( bounding_box, bb_path, crs)
        
        # 5) rasterize features
        print( '4) Rasterizing')
        contour_layer_path = full_location + contours_file
        bounding_box_layer_name = 'Bounding Box'  # Name of the bounding box layer in the GUI
        cluster_layers.append( bounding_box_layer_name)
        attribute_field = 'ContourEle'
        output_raster_path = 'C:/Users/Walte/Documents/github/highline_search/shapefiles/temp/contour_raster.tif'
        pdb.set_trace()
        
        raster_name = 'Rasterized Contours'
        cluster_layers.append( raster_name)
        dp.rasterize_contours_within_bbox( contour_layer_path, bounding_box_layer_name, attribute_field, output_raster_path)
        input_raster_layer = QgsProject.instance().mapLayersByName(raster_name)[0]
        continuous_raster_layer = dp.make_raster_continuous(input_raster_layer)
        #make_raster_continuous( )
        # 6)extract heights
        print( '5)Extracting points at ' + location + ' for cluster ' + str( z))
        sample_raster_values('highline_anchors_points', 'Rasterized Contours', 'Bounding Box')
        print( 'Removing cluster layers')
        for layer in cluster_layers:
            ps.remove_layer(layer)    
    
    print( '6)Intersection Analysis')
    keywords = [ 'Rail', 'Road', 'Trail']
    to_cross = ps.select_layers_by_substrings( all_layers, keywords)
    print( keywords)
    for i in range( len( keywords) ):
        print( keywords[i])
        print(to_cross[i])
        intersection_analysis( anchors, to_cross[i], 'xs'+keywords[i])
    
    #remove layers before repeating 
    print( 'Removing ' + location + "'s layers")
    for layer in usgs_basenames:
        ps.remove_layer(layer)    
    #save layer before repeating
    layer_name = "highline_anchors_points"
    save_path = processed + 'highline_elevations.shp'
    ps.save_temp_layer_as_permanent(layer_name, save_path)
    print( '----------------'+ 'End of ' + location + ' itteration----------------') 

