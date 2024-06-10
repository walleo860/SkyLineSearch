from qgis.core import QgsVectorLayer, QgsProject
import os

def check_inputs(contour_layer_path, bounding_box_layer_name, attribute_field, output_raster_path):
    # Check if contour layer exists
    if not os.path.exists(contour_layer_path):
        print("Contour Layer Path does not exist:", contour_layer_path)
        return False
    
    # Check if output directory is valid
    output_directory = os.path.dirname(output_raster_path)
    if not os.path.exists(output_directory):
        print("Output directory does not exist:", output_directory)
        return False
    
    # Check if attribute field exists in contour layer
    contour_layer = QgsVectorLayer(contour_layer_path, "Contours", "ogr")
    if not contour_layer.isValid():
        print("Invalid contour layer:", contour_layer_path)
        return False
    if not attribute_field in contour_layer.fields().names():
        print("Attribute field not found in contour layer:", attribute_field)
        return False
    
    # Check if bounding box layer exists
    bounding_box_layer = QgsProject.instance().mapLayersByName(bounding_box_layer_name)
    if not bounding_box_layer:
        print("Bounding Box Layer not found in the project:", bounding_box_layer_name)
        return False
    
    # All checks passed
    return True

# Example usage
contour_layer_path = processed + 'mineral_basin_contours.shp'
bounding_box_layer_name = 'Bounding Box'  # Name of the bounding box layer in the GUI
attribute_field = 'ContourEle'
output_raster_path = 'C:/Users/Walte/Documents/github/highline_search/shapefiles/contour_raster.tif'

if check_inputs(contour_layer_path, bounding_box_layer_name, attribute_field, output_raster_path):
    print("All checks passed. Ready to proceed with rasterization.")
else:
    print("Checks failed. Please correct the input parameters.")


check_inputs(contour_layer_path, bounding_box_layer_name, attribute_field, output_raster_path)
