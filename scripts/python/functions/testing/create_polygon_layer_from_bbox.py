from qgis.core import QgsVectorLayer, QgsFeature, QgsField, QgsGeometry, QgsProject

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