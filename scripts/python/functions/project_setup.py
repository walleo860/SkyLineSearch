import processing
import os
import time
import zipfile
from osgeo import gdal
from qgis.core import (QgsVectorLayer, QgsCoordinateReferenceSystem, QgsProject,
                       QgsField, QgsFeature, edit, QgsVectorFileWriter,
                       QgsFeatureRequest, QgsExpression, QgsCategorizedSymbolRenderer,
                       QgsRendererCategory,QgsSymbol,QgsWkbTypes, QgsMapLayer,
                       QgsNetworkAccessManager, QgsApplication)

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtNetwork import QNetworkDiskCache
from PyQt5.QtGui import QColor
import random
import numpy as np
import requests
from io import BytesIO
import pyproj
import tempfile
import shutil
import errno
import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd
import logging
import re
import csv

def add_id_column(layer_name, id_column_name):
    # Load the layer
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]

    # Check if the ID column already exists, if so, delete it
    if id_column_name in layer.fields().names():
        layer.dataProvider().deleteAttributes([layer.fields().indexFromName(id_column_name)])

    # Add the new ID column
    layer.dataProvider().addAttributes([QgsField(id_column_name, QVariant.Int)])
    layer.updateFields()

    # Get the number of features in the layer
    feature_count = layer.featureCount()

    # Update the attribute table with IDs
    with edit(layer):
        for i, feature in enumerate(layer.getFeatures()):
            layer.changeAttributeValue(feature.id(), layer.fields().indexFromName(id_column_name), i + 1)

    print("ID column '{}' added to layer '{}' with values from 1 to {}.".format(id_column_name, layer_name, feature_count))



def open_grass_mapset(mapset_path):
    # Initialize QGIS application
    qgs = QgsApplication([], False)
    qgs.initQgis()

    # Load GRASS plugin
    qgs.processingRegistry().addProvider(QgsGrassProvider())

    # Set GRASS environment
    QgsApplication.processingRegistry().addProvider(QgsGrassProvider())
    QgsApplication.processingRegistry().addProvider(QgsGrassProvider())
    QgsApplication.processingRegistry().addProvider(QgsGrassProvider())
    QgsApplication.processingRegistry().addProvider(QgsGrassProvider())

    # Set up the GRASS environment
    QgsApplication.processingRegistry().addProvider(QgsGrassProvider())

    # Load the project
    project = QgsProject.instance()
    project.read(mapset_path)

    # Get list of layers
    layers = project.mapLayers()

    # Do something with the layers if needed

    # Return the project instance for further manipulation if needed
    return project

def apply_categorized_symbology(layer_name, attribute_name, color_map=None):
    """
    Apply categorized symbology to a point layer based on a specified attribute column.

    :param layer_name: Name of the QGIS layer
    :param attribute_name: Name of the attribute column to use for categorization
    :param color_map: Optional dictionary mapping attribute values to colors (as QColor or RGB hex strings)
    """
    # Get the point layer by name
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if not layers:
        print(f"Error: Layer '{layer_name}' not found")
        return
    point_layer = layers[0]

    # Check if the layer has the specified attribute
    field_index = point_layer.fields().indexFromName(attribute_name)
    if field_index == -1:
        print(f"Error: Attribute '{attribute_name}' not found in the layer")
        return
    
    # Get unique values from the attribute column
    unique_values = set()
    for feature in point_layer.getFeatures():
        unique_values.add(feature[attribute_name])

    if not unique_values:
        print("No unique values found in the attribute column.")
        return
    
    # Create a list of renderer categories
    categories = []

    # Default color map if none is provided
    if color_map is None:
        # Generate default color map with random colors
        random.seed(42)  # for consistent color mapping
        for value in unique_values:
            random_color = QColor(
                random.randint(0, 255), 
                random.randint(0, 255), 
                random.randint(0, 255)
            )
            # Create a default point symbol and set its color
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
            symbol.setColor(random_color)
            categories.append(
                QgsRendererCategory(
                    value,
                    symbol,
                    str(value)
                )
            )
    else:
        # Use the provided color map
        for value in unique_values:
            if value in color_map:
                color = color_map[value]
                if isinstance(color, str):
                    color = QColor(color)  # Convert hex string to QColor
                # Create a default point symbol and set its color
                symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
                symbol.setColor(color)
                categories.append(
                    QgsRendererCategory(
                        value,
                        symbol,
                        str(value)
                    )
                )
    
    # Apply categorized renderer to the layer
    renderer = QgsCategorizedSymbolRenderer(attribute_name, categories)
    point_layer.setRenderer(renderer)

    # Refresh the layer to apply changes
    point_layer.triggerRepaint()

    print(f"Categorized symbology applied to '{layer_name}' based on '{attribute_name}'.")

def export_attribute_table_to_csv(layer_name, output_csv_path):
    """
    Export the attribute table of a specified layer to a CSV file.

    :param layer_name: The name of the layer to export.
    :param output_csv_path: The path where the CSV file will be saved.
    """
    # Get the layer by name
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    
    # Ensure the layer is valid
    if not layer.isValid():
        print(f"Layer {layer_name} is not valid.")
        return
    
    # Open the CSV file for writing
    with open(output_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write the header
        writer.writerow([field.name() for field in layer.fields()])
        
        # Write the attributes for each feature
        for feature in layer.getFeatures():
            writer.writerow([feature[field.name()] for field in layer.fields()])
    
    print(f"Attribute table of layer {layer_name} has been exported to {output_csv_path}")


def clear_cache():
    """
    Clears various QGIS caches to ensure no lingering data is being held.
    """
    try:
        # Get the network access manager instance
        nam = QgsNetworkAccessManager.instance()

        # Clear the disk cache used by the network access manager
        network_cache = nam.cache()
        if network_cache:
            network_cache.clear()
            print("Network disk cache has been cleared.")

        print("All QGIS caches have been cleared.")
    except Exception as e:
        print(f"An error occurred while clearing caches: {e}")


def compare_crs(layer1, layer2):
    crs1 = layer1.crs()
    crs2 = layer2.crs()

    if crs1 != crs2:
        print("Error: CRS of the two layers is different.")
        return False
    else:
        return True
        
def convert_csv_to_shapefile(csv_file, shapefile_path):
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    # Create a list of LineString objects
    geometries = [
        LineString([(row['home_longitude'], row['home_latitude']),
                    (row['far_longitude'], row['far_latitude'])])
        for _, row in df.iterrows()
    ]
    
    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")
    
    # Write the GeoDataFrame to a shapefile
    gdf.to_file(shapefile_path, driver='ESRI Shapefile')    
    
def get_attribute_table_names(layer_name):
    """
    Returns the attribute table field names for a specific layer in QGIS.

    :param layer_name: The name of the layer for which to get attribute table names.
    :type layer_name: str
    :return: A list of attribute table field names.
    :rtype: list
    """
    # Get the layer by name from the current project
    layer = QgsProject.instance().mapLayersByName(layer_name)
    
    if not layer:
        raise ValueError(f"No layer found with the name: {layer_name}")
    
    layer = layer[0]  # Assuming the first layer with the given name is the one desired

    # Retrieve the fields from the layer
    fields = layer.fields()

    # Extract field names
    field_names = [field.name() for field in fields]

    return field_names

def get_column_values(layer_name, column_name):
    """
    Retrieve all unique values from a specified column in the attribute table of a given layer.

    :param layer_name: The name of the layer
    :param column_name: The name of the column from which to extract values
    :return: A set of unique values from the specified column
    """
    # Get the specified layer by name
    layer = QgsProject.instance().mapLayersByName(layer_name)
    
    if not layer:
        print(f"Error: Layer '{layer_name}' not found.")
        return None
    
    layer = layer[0]

    # Check if the column exists in the layer
    field_names = [field.name() for field in layer.fields()]
    
    if column_name not in field_names:
        print(f"Error: Column '{column_name}' does not exist in layer '{layer_name}'.")
        return None

    # Extract all values from the specified column
    column_values = set()  # Use a set to get unique values
    for feature in layer.getFeatures():
        value = feature.attribute(column_name)
        column_values.add(value)

    return column_values  # Return unique values

def get_file_modification_time(file_path):
    return os.path.getmtime(file_path)

def get_last_run_time(log_file):
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                if line.startswith('(last_run_time ='):
                    match = re.search(r'\(last_run_time = (\d+\.\d+)\)', line)
                    if match:
                        return float(match.group(1))
    return 0

def delete_folder(folder_path):
    """
    Delete a folder and all its contents, with error handling for files in use.

    :param folder_path: The path to the folder to be deleted.
    """
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Folder '{folder_path}' and its contents have been deleted.")
        except PermissionError as e:
            print(f"Permission error: Cannot delete '{folder_path}'. {e}")
        except OSError as e:
            # Handle specific error codes, e.g., when a file is in use
            if e.errno == errno.EBUSY:
                print(f"Cannot delete '{folder_path}'. One or more files are in use: {e}")
            else:
                print(f"An error occurred while deleting '{folder_path}': {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    else:
        print(f"Folder '{folder_path}' does not exist.")


def download_shapefile_from_bbox(bbox, output_folder):
    """
    Download a shapefile from an API using a bounding box.

    :param bbox: Tuple of (min_lon, min_lat, max_lon, max_lat)
    :param output_folder: Directory to save the shapefile
    :return: Path to the extracted shapefile folder or None if an error occurred
    """
    #bbox = converted_bbox 
    #output_folder = usgs_path
    
    # Format the bounding box as a query parameter
    bbox_str = ",".join(map(str, bbox))
    # Build the request URL
    request_url = "https://tnmaccess.nationalmap.gov/api/v1/products?bbox=" + bbox_str + "&prodExtents=7.5%20x%207.5%20minute&prodFormats=Shapefile&start=2022-01-01&outputFormat=JSON"

    # Fetch the response from the API
    response = requests.get(request_url)

    # Check the response status code
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return None

    # Check the content type
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        print("Error: Response content type is not JSON")
        print("Response content (first 200 characters):", response.content[:200])
        return None

    # Try to parse the response as JSON
    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Unable to parse response as JSON")
        print("Response content (first 200 characters):", response.content[:200])
        return None

    # Check if the response contains data to process
    if "items" not in response_json:
        print("Error: No items found in the response")
        return None

    # Parse the response JSON to get the items
    items = response_json.get("items", [])
    
    if not items:
        print("Error: No shapefiles found for the given bounding box.")
        return None

    extracted_folders = []

    # Process each item to download and extract its shapefile
    for item in items:
        title = item.get("title", "default_folder")
        download_url = item.get("downloadURL", None)
        
        if not download_url:
            print(f"Error: No download URL found for item '{title}'.")
            continue

        # Create a new folder based on the item's title
        specific_output_folder = os.path.join(output_folder, title)
        
        if not os.path.exists(specific_output_folder):
            os.makedirs(specific_output_folder, exist_ok=True)

        # Check if the shapefile has already been downloaded
        if os.listdir(specific_output_folder):
            print(f"Shapefile '{title}' already exists in '{specific_output_folder}'. Skipping download.")
            extracted_folders.append(specific_output_folder)
            continue

        # Create a temporary file to save the response content
        temp_zip_path = os.path.join(tempfile.gettempdir(), "downloaded_shapefile.zip")

        # Download the shapefile from the provided link
        response = requests.get(download_url, stream=True)

        # Write the response content to the temporary file
        with open(temp_zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        # Check if the file is a valid zipfile
        if not zipfile.is_zipfile(temp_zip_path):
            print(f"Error: The downloaded file '{title}' is not a valid zipfile.")
            continue

        # Extract the zipfile to the specific output folder
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            zip_ref.extractall(specific_output_folder)

        print(f"Shapefile '{title}' downloaded and extracted successfully.")
        extracted_folders.append(specific_output_folder)

    return extracted_folders   




#utm_bbox = bb['min_x'],bb['min_y'], bb['max_x'],  bb['max_y']
#converted_bbox = convert_bbox_to_decimal_degrees( utm_bbox, '26912')
## Download a shapefile from the National Map
#download_shapefile_from_bbox( converted_bbox, usgs_path+'api_download')

def reproject_shapefile(input_file, output_file, epsg_code):
    """
    Reproject a shapefile to a specified CRS and save it to a new location.

    :param input_file: Path to the input shapefile
    :param output_file: Path to save the reprojected shapefile
    :param epsg_code: EPSG code for the target CRS
    """
    
    #input_file = shp_path + 'Trans_TrailSegment.shp'
    #output_file = reprojected_shp
    #epsg_code = epsg_code
    
    # Load the input layer into QGIS
    input_layer = QgsVectorLayer(input_file, 'input_layer', 'ogr')
    if not input_layer.isValid():
        print("Error: Invalid input layer")
        return

    # Create a QgsCoordinateReferenceSystem object using the EPSG code
    crs = QgsCoordinateReferenceSystem(epsg_code)
    
    # Get the output directory and ensure it exists
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # Save the reprojected layer to a new file
    error = QgsVectorFileWriter.writeAsVectorFormat(input_layer, output_file, 'UTF-8', crs, 'ESRI Shapefile')
    
    if error == QgsVectorFileWriter.NoError or error == (0, ''):
        print("Reprojection completed successfully")
    else:
        print(f"Error: Reprojection failed with error code {error}")

def list_contents(folder_path):
    files_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            files_list.append(os.path.join(root, file))
    return files_list

def load_geopdf(path, pdf):
    region = os.path.splitext(pdf)[0]  # Extracting region name from PDF filename
    
    pdf_path = os.path.join(path, pdf)  # Full path to the GeoPDF file
    
    # Open the GeoPDF file
    ds = gdal.Open(pdf_path)
    
    if ds is not None:
        # Get the number of layers in the GeoPDF
        num_layers = ds.GetLayerCount()
        
        # Loop through each layer and add it to the QGIS project
        for i in range(num_layers):
            layer = ds.GetLayerByIndex(i)
            layer_name = layer.GetName()
            full_name = f"{region} — {layer_name}"
            
            if 'contours' in layer_name:
                # Explicitly load layer with name "x" as topo layer with XYZ coordinates
                layer = QgsVectorLayer(f"{pdf_path}|layername={layer_name}", full_name, "ogr")
                # Set additional properties for topo layer with XYZ coordinates
                layer.setDataSource(pdf_path, f"layername={layer_name}", "ogr")
                layer.setProviderEncoding("UTF-8")
                layer.setCoordinateSystem()
                layer.setLayerOptions(["SHPT=POINT", "CRS=EPSG:4326", "COORDINATE_PRECISION=6"])
            else:
                # Load other layers normally
                layer = QgsVectorLayer(f"{pdf_path}|layername={layer_name}", full_name, "ogr")
            
            QgsProject.instance().addMapLayer(layer)
        
        ds = None
    else:
        print(f"Failed to open GeoPDF file: {pdf_path}")
        
    
def remove_layer(layer_name):
    """
    Remove a layer from the QGIS project by its name.

    :param layer_name: The name of the layer to remove.
    """
    project = QgsProject.instance()
    layers = project.mapLayersByName(layer_name)
    
    if not layers:
        print(f"Layer '{layer_name}' not found in the project.")
        return
    
    layer = layers[0]
    
    # Check if the layer is valid before removing
    if isinstance(layer, QgsMapLayer) and layer.isValid():
        try:
            project.removeMapLayer(layer.id())
            print(f"Layer '{layer_name}' has been removed.")
        except Exception as e:
            print(f"Error removing layer '{layer_name}': {str(e)}")
    else:
        print(f"Layer '{layer_name}' is not valid or has already been deleted.")
    

def save_layer(layer, output_path, file_format):
    # Define the output options
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = file_format
    options.layerName = layer.name()  # Use the original layer name
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    # Save the layer to the specified output path
    result = QgsVectorFileWriter.writeAsVectorFormat(layer, output_path, QgsCoordinateTransformContext(), options)
    
    # Check if the layer was saved successfully
    if result[0] != QgsVectorFileWriter.NoError:
        print(f"Error: Unable to save layer '{layer.name()}' to '{output_path}'")
    else:
        print(f"Layer '{layer.name()}' saved successfully to '{output_path}'")

from qgis.core import QgsProject, QgsFeatureRequest, QgsField, QgsExpression

def select_attribute_values(layer_name, column_name):
    """
    Retrieve all values from a specific column in a layer's attribute table.

    :param layer_name: The name of the layer
    :param column_name: The name of the column to retrieve values from
    :return: A list of values from the specified column
    """
    # Load the layer by its name
    layer = QgsProject.instance().mapLayersByName(layer_name)

    if not layer:
        print(f"Error: Layer '{layer_name}' not found.")
        return None
    
    layer = layer[0]

    # Ensure the column exists in the layer
    if layer.fields().indexFromName(column_name) == -1:
        print(f"Error: Column '{column_name}' not found in the layer.")
        return None

    # Collect all values from the specified column
    attribute_values = []
    for feature in layer.getFeatures():
        attribute_values.append(feature[column_name])

    return attribute_values
        
def select_features_by_index(layer_name, feature_indexes):
    """
    Select features from a QGIS vector layer based on a list of feature indexes.

    :param layer_name: The name of the vector layer
    :param feature_indexes: A list of feature indexes (feature IDs) to select
    :return: None
    """
    # Load the vector layer
    layer = QgsProject.instance().mapLayersByName(layer_name)
    if not layer:
        print(f"Error: Layer '{layer_name}' not found")
        return
    layer = layer[0]

    # Start editing the layer to select features
    layer.startEditing()

    # Clear any existing selection
    layer.removeSelection()

    # Select features based on the given feature indexes
    request = QgsFeatureRequest().setFilterFids(feature_indexes)
    selected_features = [feature.id() for feature in layer.getFeatures(request)]

    # Apply the selection to the layer
    layer.selectByIds(selected_features)

    # Commit the changes
    layer.commitChanges()

    print(f"Selected {len(selected_features)} features in '{layer_name}' based on given indexes.")


def select_layers_by_substrings(layer_list, substrings):
    selected_layers = []
    for layer in layer_list:
        for substring in substrings:
            if substring.lower() in layer.name().lower():
                selected_layers.append(layer)
                break  # Once a layer matches one of the substrings, move to the next layer
    return selected_layers


def select_indexes_from_values(layer_name, column_name, values):
    """
    Select feature indexes from a QGIS vector layer where a specific column has one of the given values.

    :param layer_name: The name of the vector layer
    :param column_name: The name of the column to apply the condition on
    :param values: An iterable of values to match in the specified column
    :return: A list of feature IDs (indexes) where the condition is true
    """
    # Load the vector layer
    layer = QgsProject.instance().mapLayersByName(layer_name)
    if not layer:
        print(f"Error: Layer '{layer_name}' not found")
        return None
    layer = layer[0]

    # Ensure the column exists
    field_index = layer.fields().indexFromName(column_name)
    if field_index == -1:
        print(f"Error: Column '{column_name}' not found")
        return None

    # Create an expression that checks if the column matches any of the values
    values_str = ', '.join([f"'{v}'" for v in values])  # Join values with quotes for SQL
    expression_str = f'"{column_name}" IN ({values_str})'
    expression = QgsExpression(expression_str)
    request = QgsFeatureRequest(expression)

    # Collect feature IDs that meet the condition
    matching_indexes = []
    for feature in layer.getFeatures(request):
        matching_indexes.append(feature.id())

    return matching_indexes


def select_values_from_index(layer_name, indexes, column_name):
    """
    Select features from a QGIS vector layer based on a list of indexes (feature IDs) and 
    return the unique values from a specific attribute.

    :param layer_name: The name of the vector layer
    :param indexes: A list of feature IDs to select
    :param column_name: The name of the column to extract unique values from
    :return: A set of unique values from the specified column
    """
    # Load the vector layer
    layer = QgsProject.instance().mapLayersByName(layer_name)
    if not layer:
        print(f"Error: Layer '{layer_name}' not found")
        return None
    layer = layer[0]

    # Ensure the column exists
    field_index = layer.fields().indexFromName(column_name)
    if field_index == -1:
        print(f"Error: Column '{column_name}' not found")
        return None

    # Create a feature request to filter based on feature IDs
    request = QgsFeatureRequest().setFilterFids(indexes)

    # Extract unique values from the specified column
    to_return = []
    for feature in layer.getFeatures(request):
        value = feature[column_name]
        to_return.append(value)

    return to_return
    
def save_temp_layer_as_permanent(layer_name, save_path):
    # Find the layer by name
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    #print( layer)
    QgsVectorFileWriter.writeAsVectorFormat(layer, save_path, "utf-8", layer.crs(), "ESRI Shapefile")

def setup_logging(logfile_name):
    # Check if the logfile exists
    if not os.path.exists(logfile_name):
        # Create the logfile
        open(logfile_name, 'w').close()
    
    # Configure logging
    logging.basicConfig(
        filename=logfile_name,
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add a console handler as well
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logging.getLogger().addHandler(console_handler)

def unzip_folder(zip_file_path, extract_to):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
        
def update_last_run_time(log_file):
    # Read the existing log file if it exists
    lines = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
    
    # Update or add the last run time
    found = False
    for i, line in enumerate(lines):
        if line.startswith('(last_run_time ='):
            lines[i] = '(last_run_time = ' + str(time.time()) + ')\n'
            found = True
            break
    
    if not found:
        lines.append('(last_run_time = ' + str(time.time()) + ')\n')
    
    # Write back the updated log file
    with open(log_file, 'w') as f:
        f.writelines(lines)