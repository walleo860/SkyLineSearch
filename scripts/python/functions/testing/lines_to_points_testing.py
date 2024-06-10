from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
)
from PyQt5.QtCore import QVariant

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




lines_to_points('highline_anchors', 'highline_anchors_points', 'line_id')

# Usage example
# duplicate_lines_and_add_points("input_line_layer_name", "output_point_layer_name")
