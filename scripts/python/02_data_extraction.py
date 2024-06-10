import numpy as np
import pdb
from qgis.core import (QgsSpatialIndex, QgsFeatureRequest, QgsGeometry, QgsVectorLayer, QgsRasterLayer,
                       QgsVectorFileWriter, QgsFeature, QgsField, QgsCoordinateTransformContext, QgsPointXY,
                       QgsWkbTypes, QgsProject, QgsRaster, QgsMapLayerRenderer)
                       
import functions.project_setup as ps
import functions.data_processing as dp
import functions.helper_functions as hf
import time

usgs = 'usgs_shapefiles/'
geopdf_path = raw + 'geopdf/'

usgs_path = raw + usgs
usgs_processed_path = processed + usgs

temp_path = raw.replace( 'raw', 'temp')


#list of all layers in proj
all_layers = QgsProject.instance().mapLayers().values()
# Add a new field to the attribute table to store elevations
anchors = ps.select_layers_by_substrings( all_layers, ['highline_anchors'])
anchor_points = ps.select_layers_by_substrings( all_layers, ['highline_anchors_points'])

anchors = anchors[0]
anchor_points = anchor_points[0]
#State extraction 
#may potentially be able to add other polygons to this 


# For nation wide layers we can extract all data at once
# TODO find shapefiles for landtype and jurisdiction

dp.add_state_to_attribute_table( 'United States', 'highline_anchors', 'state')
dp.extract_lengths( 'highline_anchors', 'length')
dp.check_features_within_bounds( 'highline_anchors', 'Forest Service Land', 'fs_land')
dp.check_features_within_bounds( 'highline_anchors', 'BLM Land', 'blm_land')

# Because USGS topo layers are so large we need to do this in a for loop iterating over each square
# 1) Download shapefile for given cluster
# 2) Determine all clusters within shapefiles bounds
# 3) Itterate through each cluster within said bounds and 
#   3a) Rasterize and make continuous contour layers
#   3b) Extract intersection data with trails, roads, and railroads
#   3c)TODO add hydrology layer for bodies of water and rivers
# 4) Remove all layers and delete downloaded files


#if re running the script remove layers
all_layers = QgsProject.instance().mapLayers().values()
if len( original_layers) > len( all_layers):
    set1 =  set( original_layers)
    set2 = set(all_layers)        
    to_remove = list(set2.difference(set1))  
    for layer in to_remove:
        print( 'removing '+ layer.name())
        ps.remove_layer( layer.name())
                
ps.clear_cache()

#delete all prior downloads
all_downloaded_layers = hf.prepend( os.listdir( usgs_processed_path), usgs_processed_path) +  hf.prepend( os.listdir( usgs_path), usgs_path)
if len( all_downloaded_layers) > 0:
    for downloads in all_downloaded_layers:
        ps.delete_folder( downloads)

if len( hf.prepend( os.listdir( usgs_processed_path), usgs_processed_path) +  hf.prepend( os.listdir( usgs_path), usgs_path)) > 0:
    pdb.set_trace()

groups = np.unique( ps.get_column_values( 'highline_anchors_points', 'cluster_group'))
to_skip_exists = 'to_skip' in locals() or 'to_skip' in globals()

if to_skip_exists:
    print( 'Clusters ' + str( to_skip) + ' have already been itterated through.  Skipping them')
else:
    print( 'Starting from the beginning')
    #stash starting layers
    #initiate skip array, items get appended to this occured in an earlier shapefile extent
    to_skip = []
    #initiate incomplete array, clusters that are unfinished get added to this
    incomplete = []
    #loop through cluster groups and get layers    
    g = 0


#If we are just rerunning this in order to populate new line values this limits 
#what it itterates through by rebuilding the to_skip variable 
point_names = ps.get_attribute_table_names( 'highline_anchors_points')
to_do = []
if 'elevation' in point_names and to_skip_exists == False:
    for i in groups[0]:
        print( i)
        cluster_is = ps.select_indexes_from_values( 'highline_anchors_points', 'cluster_group', [i])
        eles = ps.select_values_from_index( 'highline_anchors_points', cluster_is, 'elevation')
        if  None in eles or NULL in eles:
            to_do.append( i)
        else:
            to_skip.append( i)



print( 'Starting while loop')
while g <= max( groups[0]):
    iface.mapCanvas().refreshAllLayers()
    if g not in to_skip:
        print( '----Assesing Cluster ' + str( g) + '----')
        g_indexes = ps.select_indexes_from_values( 'highline_anchors_points', 'cluster_group', [g])
        bb = dp.get_bounding_box_dimensions( anchor_points, g_indexes)
        utm_bbox = bb['min_x'],bb['min_y'], bb['max_x'],  bb['max_y']
        converted_bbox = dp.convert_bbox_to_decimal_degrees( utm_bbox, '26912')
        # Download a shapefile from the National Map
        print( '1) Downloading shapefiles from The National Map')
        files = ps.download_shapefile_from_bbox( converted_bbox, usgs_path)
        if files is None:
            print( 'The National Map returned no JSON response for specified area')
            incomplete.append( g)
            g += 1
        else:
            folder_num = 0
            wanted = ['Rail', 'Trail', 'Road', 'Elev']
            for folder in os.listdir( usgs_path):
                if folder in list(map(os.path.basename, files)):
                    if len( files) == 1:
                        folder_num = ''
                    else:
                        folder_num = int( folder_num) + 1 
                    shp_path = usgs_path + folder + '/Shape/'
                    for file in os.listdir( shp_path):
                        if file.endswith('.shp'):                
                            if any(substring in file for substring in wanted):
                                basename = os.path.basename( file)
                                reprojected_shp = usgs_processed_path + folder + '/' + basename
                                ps.reproject_shapefile( shp_path + file, reprojected_shp, epsg_code)
                                layer_name = basename.replace( '.shp','') + str( folder_num)
                                iface.addVectorLayer( reprojected_shp, layer_name, 'ogr')
            
            all_layers = QgsProject.instance().mapLayers().values()
            #Merge all layers if bounding box for cluster g overlaps multiple areas
            if files:
                if len( files) > 1:
                    print( 'There are multiple files downloaded from The National Map. Merging them...')
                    for keyword in wanted:
                        all_layers = QgsProject.instance().mapLayers().values()
                        if keyword not in ['Water', 'Elev'] : 
                            keyword = "_" + keyword
                        layers_to_join =  ps.select_layers_by_substrings( all_layers, [keyword])
                        similarlayers = []
                        for layer in layers_to_join:
                            similarlayers.append( layer.name())
                        dp.merge_layers( similarlayers, re.sub(r'\d', '', layers_to_join[0].name()))
                        if keyword == 'Elev':
                            contour_path = temp_path + 'contours.shp'
                            ps.save_temp_layer_as_permanent( 'Elev_Contour', contour_path)
                else:
                    contour_path = usgs_processed_path + os.path.basename( files[0]) + '/Elev_Contour.shp'                
            else:
                print( 'Single File Downloaded from The National Map')
                contour_path = usgs_processed_path + os.path.basename( files[0]) + '/Elev_Contour.shp'
            
            #refresh all layers
            all_layers = QgsProject.instance().mapLayers().values()
            #get contour layer
            print( 'Selecting contours')
            contours = ps.select_layers_by_substrings( all_layers, ['Contour'])
            #print( contours)
            contours = contours[0]
            print(  '2) Select highlines that exist within contours')
            
            #get highlines that intersect with contours
            int_indexs = dp.get_intersecting_indexes( 'highline_anchors', 'Elev_Contour')
            #select associated line ids
            line_ids_in_contours = np.unique( ps.select_values_from_index( 'highline_anchors', int_indexs, 'line_id'))
            #use line ids to select indexs from points layer
            points_in_contours = ps.select_indexes_from_values( 'highline_anchors_points', 'line_id', line_ids_in_contours)
            
            if points_in_contours == []: #this is incase non of the lines overlap contours. we can assume that the cluster we are itterating over is within the bounds of the contours
                points_in_contours = g_indexes
                
            #use indexs to select unique clusters
            clusters_o = np.unique( ps.select_values_from_index( 'highline_anchors_points', points_in_contours, 'cluster_group'))
            #remove clusters we already itterated over
            set1 =  set( to_skip)
            set2 = set(clusters_o)        
            clusters = list(set2.difference(set1))
            #loop through the clusters to reduce computation time from rasterization
            print( 'There are ' + str( len( clusters)) + ' clusters within these contours')
            print( 'Itterating over ' + str( len( clusters)) + ' of them')
            
            for z in clusters:
                cluster_layers = []
                #select indexs of points in cluster
                cluster_lines = ps.select_indexes_from_values( 'highline_anchors_points', 'cluster_group', [z])
                #get lines in contours and those in cluster z
                these_lines = list(set(cluster_lines).intersection(points_in_contours))
                
                if these_lines == []:
                    these_lines = cluster_lines
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
                if contour_path:
                    contour_layer_path = contour_path
                else:
                    contour_layer_path = usgs_processed_path + os.path.basename(files[0]) + '/Elev_Contour.shp'
                bounding_box_layer_name = 'Bounding Box'  # Name of the bounding box layer in the GUI
                cluster_layers.append( bounding_box_layer_name)
                attribute_field = 'ContourEle'
                output_raster_path = project_directory + '/shapefiles/temp/contour_raster.tif'
                #pdb.set_trace()
                
                raster_name = 'Rasterized Contours'
                cluster_layers.append( raster_name)
                dp.rasterize_contours_within_bbox( contour_path, bounding_box_layer_name, attribute_field, output_raster_path)
                input_raster_layer = QgsProject.instance().mapLayersByName(raster_name)[0]
                print( 'Making Raster Layer Continuous. This may take a few moments...')
                continuous_raster_layer = dp.make_raster_continuous(input_raster_layer)
                #make_raster_continuous( )
                # 6)extract elevations 
                print( '5)Extracting points for cluster ' + str( z))
                dp.sample_raster_values('highline_anchors_points', 'Rasterized Contours', 'Bounding Box')            
                elevations = ps.select_values_from_index( 'highline_anchors_points', cluster_lines, 'elevation')
                
                if None in elevations :
                    print( 'Not all points have elevations for cluster ' + str(z))
                    incomplete.append( z)
                else: 
                    to_skip.append( z)                
                
                for layer in cluster_layers:
                    ps.remove_layer( layer)
                    
            all_layers = QgsProject.instance().mapLayers().values()
    
            #intersection analysis
            print( '6)Intersection Analysis')
            keywords = [ 'Rail', 'Road', 'Trail']
            to_cross = ps.select_layers_by_substrings( all_layers, keywords)
            for i in range( len( keywords) ):
                print(to_cross[i])
                to_search = '_' +keywords[i]
                intersecting_layer = ps.select_layers_by_substrings( all_layers, [to_search] )[0].name()
                dp.intersection_analysis( anchors.name(), intersecting_layer, 'xs'+keywords[i])
            
            #Before we itterate through the next potential cluster we must remove all the layers added for this process
            all_layers = QgsProject.instance().mapLayers().values()
            #s = 0
            #if g == 2:
            #    pdb.set_trace()
            #while len( all_layers) != len( original_layers):  
                #s = s+1
            #if g == 2:
            #    pdb.set_trace()
            set1 =  set( original_layers)
            set2 = set(all_layers)
            #pdb.set_trace()
            # Find symmetric difference between starting layers and final
            to_remove = list(set2.difference(set1)) 
            
            for layer in to_remove:
                if layer.isValid():
                    print( 'removing '+ layer.name())
                    while layer in all_layers:
                        ps.remove_layer( layer.name())
                        iface.mapCanvas().refreshAllLayers()
                        #time.sleep( 3)
                        all_layers = QgsProject.instance().mapLayers().values()
                        
            set1 =  set( original_layers)
            set2 = set(all_layers)
            to_remove = list(set2.difference(set1)) 
            if len( to_remove) > 0:
                print( 'Qgis failed to remove a layer')
                pdb.set_trace()
            
            
            #delete all downloaded layers           #
            iface.mapCanvas().refreshAllLayers()
            all_downloaded_layers = hf.prepend( os.listdir( usgs_processed_path), usgs_processed_path) +  hf.prepend( os.listdir( usgs_path), usgs_path)
            
            
            #TODO for some reason deleting files of layers does not work in this for loop
            for downloads in all_downloaded_layers:                
                attempt = 1
                ps.clear_cache()
                print( attempt)
                iface.mapCanvas().refreshAllLayers()
                ps.delete_folder( downloads)
                attempt = attempt + 1
                    
                
            #if the layers cannot be deleted halt execution
            if len( hf.prepend( os.listdir( usgs_processed_path), usgs_processed_path) +  hf.prepend( os.listdir( usgs_path), usgs_path)) > 0:
                print( 'qgis failed to delete folders')
            ps.save_temp_layer_as_permanent( 'highline_anchors_points', outs + 'highline_anchors_points.shp')    
            ps.save_temp_layer_as_permanent( 'highline_anchors', outs + 'highline_anchors.shp')
            g += 1
            
    else:
        print( 'Skipping cluster ' + str(g))
        g += 1         

#iface.addVectorLayer(  outs + 'highline_anchors_points.shp', 'highline_anchors_points', 'ogr')

export_attribute_table_to_csv( 'highline_anchors_points', project_directory + "/data/output/" + 'highline_anchors_points.csv')
export_attribute_table_to_csv( 'highline_anchors', project_directory + "/data/output/" + 'highline_anchors.csv')
    