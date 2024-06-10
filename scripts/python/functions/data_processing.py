import os
import numpy as np

from qgis.core import (QgsSpatialIndex, QgsFeatureRequest, QgsGeometry, QgsVectorLayer, QgsRasterLayer,
                       QgsVectorFileWriter, QgsFeature, QgsField, QgsCoordinateTransformContext, QgsPointXY,
                       QgsWkbTypes, QgsProject, QgsRaster, QgsProcessingException, QgsMapLayerRenderer)
from osgeo import gdal
from qgis.analysis import ( QgsRasterCalculator, QgsRasterCalculatorEntry, QgsNativeAlgorithms)
from PyQt5.QtCore import QVariant
import processing
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from PyQt5.QtCore import QVariant

def compare_crs(layer1, layer2):
    crs1 = layer1.crs()
    crs2 = layer2.crs()

    if crs1 != crs2:
        print("Error: CRS of the two layers is different.")
        return False
    else:
        return True

def add_state_to_attribute_table(states_layer, target_layer, column_name):
    # Create a spatial index for the states layer for faster querying
    
    
    states_layer = QgsProject.instance().mapLayersByName(states_layer)[0]
    index = QgsSpatialIndex(states_layer.getFeatures())

    # Start editing the target layer
    target_layer = QgsProject.instance().mapLayersByName(target_layer)[0]
    target_layer.startEditing()

    # Add a new field to the target layer if the specified column name doesn't exist
    if target_layer.fields().indexFromName(column_name) == -1:
        target_layer.addAttribute(QgsField(column_name, QVariant.String))

    # Get the index of the newly added column
    column_index = target_layer.fields().lookupField(column_name)

    # Iterate over features in the target layer
    for feature in target_layer.getFeatures():
        # Get the geometry of the feature
        geometry = feature.geometry()
        # Use the spatial index to find the intersecting states
        intersecting_states = [f["NAME"] for f in states_layer.getFeatures(QgsFeatureRequest().setFilterRect(geometry.boundingBox())) if f.geometry().intersects(geometry)]
        # Set the column attribute value for the feature
        if intersecting_states:
            target_layer.changeAttributeValue(feature.id(), column_index, intersecting_states[0])
        else:
            target_layer.changeAttributeValue(feature.id(), column_index, "Not in any state")

    # Commit changes and stop editing
    target_layer.commitChanges()
    target_layer.triggerRepaint()    

def check_features_within_bounds(layer1_name, layer2_name, column_name):
    """
    Function to check if features from layer1 are within the bounds of features in layer2.
    Adds a column to layer1 indicating 'y' or 'n' for each feature.
    
    :param layer1: The input vector layer to check features from
    :param layer2: The reference vector layer to check features within
    :param column_name: The name of the column to be added to layer1
    """
    
    layer1 = QgsProject.instance().mapLayersByName(layer1_name)[0]  
    layer2 = QgsProject.instance().mapLayersByName(layer2_name)[0]  

    # Ensure both layers are valid
    if not layer1.isValid() or not layer2.isValid():
        print("One or both layers are invalid")
        return

    # Start an edit session for layer1
    layer1.startEditing()
    
    # Add the new column to layer1
    if column_name not in [field.name() for field in layer1.fields()]:
        layer1.addAttribute(QgsField(column_name, QVariant.String))
    layer1.updateFields()

    # Get the index of the new column
    column_index = layer1.fields().indexFromName(column_name)
    
    # Iterate over each feature in layer1
    for feature1 in layer1.getFeatures():
        feature1_geometry = feature1.geometry()
        within = 0
        
        # Check if this feature is within any feature in layer2
        for feature2 in layer2.getFeatures():
            if feature1_geometry.within(feature2.geometry()):
                within = 1
                break
        
        # Update the feature's attribute
        layer1.changeAttributeValue(feature1.id(), column_index, within)
    
    # Commit changes to layer1
    layer1.commitChanges()

def cluster_points_with_dbscan(layer_name, eps=0.1, min_samples=5):
    """
    Perform DBSCAN clustering on points in a given QGIS layer and update the attribute table.
    """
    # Load the point layer by its name
    point_layers = QgsProject.instance().mapLayersByName(layer_name)
    if not point_layers:
        print(f"Error: Layer '{layer_name}' not found")
        return
    point_layer = point_layers[0]

    # Check if the layer is a point layer
    if point_layer.wkbType() != QgsWkbTypes.Point:
        print("Error: The layer is not a point layer.")
        return
    
    # Extract the X and Y coordinates of each point
    points = []
    feature_ids = []
    for feature in point_layer.getFeatures():
        geom = feature.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            point = geom.asPoint()
            points.append([point.x(), point.y()])
            feature_ids.append(feature.id())
    
    if not points:
        print("No points found in the layer.")
        return
    
    # Convert the list to a NumPy array
    points = np.array(points)

    # Scale the points (optional but recommended)
    scaler = StandardScaler()
    points_scaled = scaler.fit_transform(points)
    
    # Perform DBSCAN clustering on the scaled data
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(points_scaled)
    
    # Get the cluster labels
    cluster_labels = db.labels_
    #print( cluster_labels.head( 10))
    
    # Add a 'cluster_group' field to the point layer if it doesn't exist
    point_layer.startEditing()
    if point_layer.fields().indexFromName("cluster_group") == -1:
        point_layer.addAttribute(QgsField("cluster_group", QVariant.Int))
        point_layer.updateFields()

    # Get the index for the 'cluster_group' field
    cluster_group_index = point_layer.fields().indexFromName("cluster_group")
    
    # Update the 'cluster_group' field for each feature
    for feature, cluster_label in zip(feature_ids, cluster_labels):
        point_layer.changeAttributeValue(feature, cluster_group_index, int(cluster_label))
    
    # Commit the changes
    point_layer.commitChanges()
    
    print("DBSCAN clustering completed and attribute table updated.")

def convert_bbox_to_decimal_degrees(utm_bbox, source_epsg, target_epsg=4326):
    """
    Convert a 
    box from one EPSG to another (default to decimal degrees, EPSG:4326).
    
    :param utm_bbox: Tuple of (min_x, min_y, max_x, max_y)
    :param source_epsg: The source EPSG code (e.g., 26912 for UTM Zone 12N)
    :param target_epsg: The target EPSG code (default is 4326 for WGS 84 in decimal degrees)
    :return: Bounding box in decimal degrees (min_lon, min_lat, max_lon, max_lat)
    """
    # Create a transformer from the source EPSG to the target EPSG
    transformer = pyproj.Transformer.from_crs(f"EPSG:{source_epsg}", f"EPSG:{target_epsg}", always_xy=True)

    # Unpack the bounding box
    min_x, min_y, max_x, max_y = utm_bbox

    # Convert the min and max coordinates to decimal degrees
    min_lon, min_lat = transformer.transform(min_x, min_y)
    max_lon, max_lat = transformer.transform(max_x, max_y)

    # Return the converted bounding box
    return (min_lon, min_lat, max_lon, max_lat)


def create_polygon_layer_from_bbox(bounding_box, output_path, crs):
     # Create a new memory layer
    layer = QgsVectorLayer('Polygon?crs=' + crs.authid(), 'Bounding Box', 'memory')
    if not layer.isValid():
        print("Error: Failed to create vector layer")
        return

    # Add attributes
    layer.startEditing()
    layer.addAttribute(QgsField('ID', QVariant.Int))
    layer.updateFields()

    # Create feature with bounding box geometry
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromRect(bounding_box))
    feature.setAttributes([1])  # ID value, you can change this as needed

    # Add feature to layer
    layer.addFeature(feature)
    layer.commitChanges()

    # Set CRS
    layer.setCrs(crs)

    # Save the layer to disk
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"  # Change the format if needed
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    QgsVectorFileWriter.writeAsVectorFormatV2(layer, output_path, QgsCoordinateTransformContext(), options)

    # Add the layer to the project
    QgsProject.instance().addMapLayer(layer)

    print("Bounding box layer created successfully")

# Example usage:
#bounding_box = QgsRectangle(10, 20, 30, 40)  # Replace with your bounding box coordinates
#output_path = '/path/to/output_layer.shp'
#crs = QgsCoordinateReferenceSystem('EPSG:4326')  # Replace with your CRS
#
#create_polygon_layer_from_bbox(bounding_box, output_path, crs)

def detect_crossing_lines(layer1_name, layer2_name, field_name):
    # Get the layers by name
    layer1 = QgsProject.instance().mapLayersByName(layer1_name)[0]
    layer2 = QgsProject.instance().mapLayersByName(layer2_name)[0]

    # Add a new field to store the result in layer1    
    field_index = layer1.fields().indexFromName(field_name)
    if field_index == -1:
        field = QgsField(field_name, QVariant.String)
        layer1.startEditing()
        layer1.addAttribute(field)

    # Iterate through features in layer1
    for feat1 in layer1.getFeatures():
        crosses = 'n'  # Assume the line does not cross initially
        geom1 = feat1.geometry()

        # Iterate through features in layer2
        for feat2 in layer2.getFeatures():
            geom2 = feat2.geometry()

            # Check if the geometries intersect
            if geom1.intersects(geom2):
                crosses = 'y'
                break

        # Update the attribute table of layer1
        layer1.changeAttributeValue(feat1.id(), field_index, crosses)

    # Commit changes to the attribute table
    layer1.commitChanges()

def download_shapefile_from_bbox(bbox, output_folder):
    """
    Download a shapefile from an API using a bounding box.

    :param bbox: Tuple of (min_lon, min_lat, max_lon, max_lat)
    :param output_folder: Directory to save the shapefile
    :return: Path to the extracted shapefile folder or None if an error occurred
    """
    # Format the bounding box as a query parameter
    bbox_str = ",".join(map(str, bbox))
    # Build the request URL
    request_url = "https://tnmaccess.nationalmap.gov/api/v1/products?bbox=" + bbox_str + "&prodExtents=7.5%20x%207.5%20minute&prodFormats=Shapefile&start=2022-01-01&outputFormat=JSON"

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Fetch the shapefile from the API
    response = requests.get(request_url)

    # Print the response status code and a preview of the content for debugging
    print(f"Response status code: {response.status_code}")
    print(f"Response content (first 200 characters): {response.content[:200]}")  # Preview the first 200 characters
    
    # Check if the response is valid
    if response.status_code != 200:
        print(f"Error: Received response with status code {response.status_code}")
        return None
    response_json = response.json()
    if not response_json.get("items"):
        print("Error: No shapefiles found for the given bounding box.")
        return None

    # Extract the first item to find relevant information
    item = response_json["items"][0]
    if "moreInfo" in item:
        print(f"Additional information: {item['moreInfo']}")

    # Find the download link if available
    download_url = item.get("downloadURL")
    if not download_url:
        print("Error: No download URL found in the response.")
        return None

    # Create a temporary file to save the response content
    temp_zip_path = os.path.join(tempfile.gettempdir(), "downloaded_shapefile.zip")

    # Download the shapefile from the provided link
    response = requests.get(download_url, stream=True)
    
    # Write the response content to the temporary file
    with open(temp_zip_path, "wb") as f:
        f.write(response.content)

    # Check if the file is a valid zipfile
    if not zipfile.is_zipfile(temp_zip_path):
        print("Error: The downloaded file is not a valid zipfile.")
        return None

    # Extract the zipfile to the output folder
    with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
        zip_ref.extractall(output_folder)

    print("Shapefile downloaded and extracted successfully.")
    
    return output_folder

# Example usage:
#detect_crossing_lines('layer1_name', 'layer2_name')

def get_intersecting_indexes(layer1_name, layer2_name):
    """
    Find the indices of features in the first layer that intersect with features in the second layer.
    
    :param layer1_name: Name of the first line layer
    :param layer2_name: Name of the second line layer
    :return: A set of indices of features in the first layer that intersect with features in the second layer
    """
    # Load the line layers by name
    layer1 = QgsProject.instance().mapLayersByName(layer1_name)
    layer2 = QgsProject.instance().mapLayersByName(layer2_name)
    
    if not layer1 or not layer2:
        raise ValueError(f"One or both layers '{layer1_name}' or '{layer2_name}' not found")
    
    layer1 = layer1[0]
    layer2 = layer2[0]
    
    # Set to store unique indices of intersecting features in the first layer
    intersecting_indices = set()
    
    # Iterate over each feature in the first layer
    for feature1 in layer1.getFeatures():
        geom1 = feature1.geometry()
        
        # Check if this feature intersects with any feature in the second layer
        for feature2 in layer2.getFeatures():
            geom2 = feature2.geometry()
            
            if geom1.intersects(geom2):
                intersecting_indices.add(feature1.id())  # Add unique index to the set
                break  # If intersection is found, no need to check further for this feature
    
    return list(intersecting_indices)  # Return a list of unique intersecting indices


def lines_to_points(input_line_layer_name, output_point_layer_name, id_col):
    """
    Convert a line layer into a point layer with points every meter, including start and end points.

    :param input_line_layer_name: Name of the input line layer
    :param output_point_layer_name: Name of the output point layer
    :param id_col: Column name for line ID
    """
    # Load the input line layer
    input_line_layer = QgsProject.instance().mapLayersByName(input_line_layer_name)
    if not input_line_layer:
        raise ValueError(f"Layer '{input_line_layer_name}' not found.")
    input_line_layer = input_line_layer[0]

    # Create a new memory point layer
    output_point_layer = QgsVectorLayer(
        'Point?crs=' + input_line_layer.crs().authid(), output_point_layer_name, 'memory'
    )
    provider = output_point_layer.dataProvider()

    # Add fields for line ID and index
    provider.addAttributes([
        QgsField("line_id", QVariant.Int),  # Line ID from the original layer
        QgsField("index", QVariant.Int),  # Index for points along the line
    ])
    output_point_layer.updateFields()

    # Initialize the new feature with the correct fields
    new_feature = QgsFeature()
    new_feature.setFields(provider.fields())

    # Iterate over each feature in the input line layer
    for line_feature in input_line_layer.getFeatures():
        geom = line_feature.geometry()

        # Ensure the geometry is either single-line or multi-line
        if geom.isMultipart():
            parts = geom.asMultiPolyline()  # Decompose multi-line
        else:
            parts = [geom.asPolyline()]  # Treat as single-line

        # Use the ID from the specified column
        line_id = line_feature.attribute(id_col)

        # Process each part of the multi-part line or single line
        for part_index, part in enumerate(parts):
            # Reset index for each part
            index = 1

            # Add the start point
            start_point = part[0]  # First vertex in the part
            new_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(start_point.x(), start_point.y())))
            new_feature.setAttributes([line_id, index])
            provider.addFeature(new_feature)
            index += 1

            # Add points at 1-meter intervals
            current_distance = 1
            # Create a geometry from the part to interpolate points
            polyline_geom = QgsGeometry.fromPolylineXY(part)  # From PolylineXY for safety
            while current_distance < polyline_geom.length():
                point = polyline_geom.interpolate(current_distance)  # Interpolated point
                new_feature.setGeometry(QgsGeometry.fromPointXY(point.asPoint()))  # Use asPointXY
                new_feature.setAttributes([line_id, index])
                provider.addFeature(new_feature)
                current_distance += 1
                index += 1

            # Add the end point
            end_point = part[-1]  # Last vertex in the part
            new_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(end_point.x(), end_point.y())))
            new_feature.setAttributes([line_id, index])
            provider.addFeature(new_feature)

    # Commit changes to the output point layer
    output_point_layer.commitChanges()

    # Add the output point layer to QGIS
    QgsProject.instance().addMapLayer(output_point_layer)

    print("Conversion of lines to points completed successfully.")



def extract_elevation_along_lines(line_layer, contour_layer, output_field_name):    # Prepare raster layer for elevation data (if not already done)
    print( 'start')
    #print( contour_layer.name())
    contour_raster = contour_layer.name() + '_raster'
    print( contour_raster)
    processing.run("gdal:rasterize", {
        'INPUT': contour_layer,
        'FIELD': 'elevation',  # Change this to the field name containing elevation values in your contour layer
        'BURN': 0,
        'WIDTH': contour_layer.rasterUnitsPerPixelX(),
        'HEIGHT': contour_layer.rasterUnitsPerPixelY(),
        'UNITS': 1,
        'EXTENT': contour_layer.extent(),
        'NODATA': 0,
        'DATA_TYPE': 5,  # Float32
        'OUTPUT': contour_raster
    })

    # Get raster layer
    contour_raster_layer = QgsRasterLayer(contour_raster, 'Contour_Raster')
    if not contour_raster_layer.isValid():
        print("Error: Contour raster layer is not valid")
        return

    # Get elevation values along lines
    line_layer.startEditing()
    line_layer_provider = line_layer.dataProvider()
    for feat in line_layer.getFeatures():
        line_geom = feat.geometry()
        line_start_point = line_geom.vertexAt(0)
        line_end_point = line_geom.vertexAt(1)

        # Get elevation at start point
        start_elevation = get_elevation_at_point(line_start_point, contour_raster_layer)
        # Get elevation at end point
        end_elevation = get_elevation_at_point(line_end_point, contour_raster_layer)

        # Save elevation values as attributes
        line_layer_provider.changeAttributeValues({feat.id(): {f"{output_field_name}_start": start_elevation,
                                                               f"{output_field_name}_end": end_elevation}})

    line_layer.commitChanges()
    print("Elevation extraction completed.")

from qgis.core import QgsProject, QgsField, QgsFeature
from qgis.PyQt.QtCore import QVariant

def extract_lengths(layer_name, field_name='length'):
    # Get the layer by name
    layer = QgsProject.instance().mapLayersByName(layer_name)
    if not layer:
        print(f"Layer '{layer_name}' not found")
        return
    layer = layer[0]

    # Check if the layer is a line layer
    if layer.geometryType() != QgsWkbTypes.LineGeometry:
        print(f"Layer '{layer_name}' is not a line layer")
        return

    # Check if the field already exists, if not, create it
    if field_name not in [field.name() for field in layer.fields()]:
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField(field_name, QVariant.Double)])
        layer.updateFields()
    
    # Get the index of the new field
    field_index = layer.fields().indexOf(field_name)

    # Initialize a list to store lengths
    feature_lengths = []

    # Loop through each feature in the layer
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom.isMultipart():
            length = geom.length()  # length for multipart geometry
        else:
            length = geom.length()  # length for singlepart geometry
        
        # Append the length to the list
        feature_lengths.append(length)
        
        # Update the feature with the new length attribute
        layer.startEditing()
        layer.changeAttributeValue(feature.id(), field_index, length)
        layer.commitChanges()
    
    return feature_lengths


def get_bounding_box_dimensions(layer, feature_ids):
    # Initialize variables to store min/max coordinates
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    # Iterate through the features to find the bounding box
    for feature_id in feature_ids:
        feature = layer.getFeature( feature_id)
        geom = feature.geometry()
        bbox = geom.boundingBox()
        
        # Update min/max coordinates
        min_x = min(min_x, bbox.xMinimum())
        max_x = max(max_x, bbox.xMaximum())
        min_y = min(min_y, bbox.yMinimum())
        max_y = max(max_y, bbox.yMaximum())

    extended_min_x = min_x - 30
    extended_max_x = max_x + 30
    extended_min_y = min_y - 30
    extended_max_y = max_y + 30

    # Calculate height and width of the extended bounding box
    extended_height = extended_max_y - extended_min_y
    extended_width = extended_max_x - extended_min_x

    # Return the extended bounding box dimensions and coordinates
    return {
        'min_x': extended_min_x,
        'max_x': extended_max_x,
        'min_y': extended_min_y,
        'max_y': extended_max_y,
        'height': extended_height,
        'width': extended_width
    }

def get_elevation_at_point(point, raster_layer):
    x = point.x()
    y = point.y()
    # Get raster value at point location
    result = raster_layer.dataProvider().identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue)
    return result.results()[1]

def intersection_analysis(layer_a_name, layer_b_name, column_name):
    """
    Identify intersections between lines in Layer A and Layer B, then update Layer A's specified column.

    :param layer_a_name: Name of the first line layer (Layer A)
    :param layer_b_name: Name of the second line layer (Layer B)
    :param column_name: Name of the column to update in Layer A if intersections are found
    """   
    
    # Load the layers by name
    layer_a = QgsProject.instance().mapLayersByName(layer_a_name)
    layer_b = QgsProject.instance().mapLayersByName(layer_b_name)

    if not layer_a or not layer_b:
        print("Error: One or both layers not found.")
        return

    layer_a = layer_a[0]
    layer_b = layer_b[0]

    # Define a temporary memory layer to hold the intersections
    output_path = 'memory:temporary_intersections'

    try:
        # Run the "Line Intersections" tool
        result = processing.run(
            "qgis:lineintersections",
            {
                'INPUT': layer_a,
                'INTERSECT': layer_b,
                'OUTPUT': output_path,
            },
        )

        # Get the resulting intersections layer
        intersections_layer = result["OUTPUT"]

        # Get a set of IDs from layer A that have intersections
        intersecting_ids = set()
        for feature in intersections_layer.getFeatures():
            intersecting_id = feature.attribute('line_id')
            if intersecting_id is not None:
                intersecting_ids.add(int(intersecting_id)-1)

        # Add the field to layer_a if it doesn't exist
        field_index = layer_a.fields().indexFromName(column_name)
        if field_index == -1:
            layer_a.startEditing()  # Enable editing
            layer_a.dataProvider().addAttributes([QgsField(column_name, QVariant.String)])
            layer_a.updateFields()
            layer_a.commitChanges()  # Save changes

        # Update Layer A with 'y' if there are intersections
        layer_a.startEditing()
        field_index = layer_a.fields().indexFromName(column_name)  # Re-check the field index
        
        for feature in layer_a.getFeatures():
            if feature.id() in intersecting_ids:
                layer_a.changeAttributeValue(feature.id(), field_index, 1)

        layer_a.commitChanges()  # Commit the changes to persist them

        print("Intersection analysis and attribute update completed.")

    except QgsProcessingException as e:
        print(f"Error during processing: {e}")


# Example usage:
#layer1 = QgsProject.instance().mapLayersByName('Layer 1')[0]
#layer2 = QgsProject.instance().mapLayersByName('Layer 2')[0]
#intersection_analysis(layer1, layer2, "intersection")

import requests
import zipfile
import os
from io import BytesIO
import pyproj
import tempfile



def make_raster_continuous(input_raster_layer):
    input_layer_name = input_raster_layer.name()
    input_layer_path = input_raster_layer.source()

    parameters = {
        'input': input_layer_path,
        'output': 'TEMPORARY_OUTPUT',
        'GRASS_REGION_PARAMETER': None,
        'GRASS_REGION_CELLSIZE_PARAMETER': 0,
        'GRASS_RASTER_FORMAT_OPT': '',
        'GRASS_RASTER_FORMAT_META': ''
    }
    output_raster_path = processing.run("grass7:r.surf.contour", parameters)['output']

    # Remove input layer
    QgsProject.instance().removeMapLayer(input_raster_layer)

    # Add the new continuous raster layer
    continuous_raster_layer = QgsRasterLayer(output_raster_path, input_layer_name)
    QgsProject.instance().addMapLayer(continuous_raster_layer)

    return continuous_raster_layer

def merge_layers(layers_to_merge, output_layer_name):
    """
    Merge multiple contour layers into one without dissolving, ensuring each feature is kept intact.

    :param layers_to_merge: An array of the names of the contour layers to merge
    :param output_layer_name: The name for the output merged layer
    :return: The name of the output merged layer
    """
    # Get the list of layers to merge
    merge_layers = []

    for layer_name in layers_to_merge:
        layer = QgsProject.instance().mapLayersByName(layer_name)

        if not layer:
            print(f"Error: Layer '{layer_name}' not found.")
            return None
        
        merge_layers.append(layer[0])

    # Merge all specified contour layers into one without dissolving
    merged_layer = processing.run(
        "native:mergevectorlayers",
        {
            "LAYERS": merge_layers,
            "CRS": merge_layers[0].crs(),
            "OUTPUT": "memory:",
        },
        feedback=None,
    )["OUTPUT"]

    # Rename the merged layer
    merged_layer.setName(output_layer_name)

    # Add the merged layer to the project
    QgsProject.instance().addMapLayer(merged_layer)

    # Optionally remove the original layers
    for layer in merge_layers:
        QgsProject.instance().removeMapLayer(layer)

    return output_layer_name
    
    
    
#one = 'USGS Topo Map Vector Data (Vector) 45919 Tungsten, Colorado 20220512 for 7.5 x 7.5 minute Shapefile'
#two = 'USGS Topo Map Vector Data (Vector) 72681 Gold Hill, Colorado 20220512 for 7.5 x 7.5 minute Shapefile'
#iface.addVectorLayer( usgs_processed_path + one + '/Elev_Contour.shp', 'Elev_Contour1', 'ogr')
#iface.addVectorLayer( usgs_processed_path + two + '/Elev_Contour.shp', 'Elev_Contour2', 'ogr')
#merge_and_resolve_contour_layers( [ 'Elev_Contour1', 'Elev_Contour2'], 'Elev_Contour')


def rasterize_contours_within_bbox(contour_layer_path, bounding_box_layer_name, attribute_field, output_raster_path):
    # Load contour layer
    contour_layer = QgsVectorLayer(contour_layer_path, "Contours", "ogr")

    # Check if contour layer is valid
    if not contour_layer.isValid():
        print("Invalid contour layer")
        return False

    # Get bounding box layer
    bounding_box_layers = QgsProject.instance().mapLayersByName(bounding_box_layer_name)
    if not bounding_box_layers:
        print(f"Bounding box layer '{bounding_box_layer_name}' not found")
        return False
    bounding_box_layer = bounding_box_layers[0]

    # Get bounding box layer's extent
    bounding_box_extent = bounding_box_layer.extent()

    # Define rasterization parameters
    params = {
        'input': contour_layer_path,
        'type': [0, 1, 3],
        'use': 0,
        'column': attribute_field,
        'output': output_raster_path,
        'GRASS_REGION_PARAMETER': '{},{},{},{}'.format(bounding_box_extent.xMinimum(), bounding_box_extent.xMaximum(),
                                                       bounding_box_extent.yMinimum(), bounding_box_extent.yMaximum()),
        'GRASS_REGION_CELLSIZE_PARAMETER': 1,
    }

    print('Params compiled')

    # Run v.to.rast algorithm
    try:
        processing.run("grass8:v.to.rast.attr", params)
        print('Processing complete')

        # Add the resulting raster layer to the map
        output_raster = QgsRasterLayer(output_raster_path, "Rasterized Contours")
        if not output_raster.isValid():
            print("Output raster is not valid")
            return False

        QgsProject.instance().addMapLayer(output_raster)
        print("Rasterization completed successfully")
        return True

    except Exception as e:
        print(f"Error running algorithm: {e}")
        return False


def select_overlapping_features(layer_to_select_from, layer_with_extent):
    # Get the extent (bounding box) of the layer with extent
    if not compare_crs(layer_to_select_from, layer_with_extent):
        exit()  # Stop the script
    else:
        pass
    extent = layer_with_extent.extent()
    #print( extent)

    # Create a geometry from the extent
    extent_geometry = QgsGeometry.fromRect(extent)
    #print( extent_geometry)

    # Iterate over features in the layer to select from
    selected_feature_ids = []
    for feature in layer_to_select_from.getFeatures():
        # Check if the feature geometry intersects with the extent geometry
        if feature.geometry().intersects(extent_geometry):
            #print( 'feature in extent')
            #print( feature.id())
            selected_feature_ids.append(feature.id())

    # Select the features in the layer to select from
    #layer_to_select_from.selectByIds(selected_feature_ids)
    #print( selected_feature_ids)
    return selected_feature_ids

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

