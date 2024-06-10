from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsProcessingException,
)
from PyQt5.QtCore import QVariant
import processing


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
                layer_a.changeAttributeValue(feature.id(), field_index, 'y')

        layer_a.commitChanges()  # Commit the changes to persist them

        print("Intersection analysis and attribute update completed.")

    except QgsProcessingException as e:
        print(f"Error during processing: {e}")
