from qgis.core import QgsProject, QgsField, QgsFeature

def intersection_analysis(layer1, layer2, new_column_name):
    # Check if both layers are valid
    if not layer1.isValid() or not layer2.isValid():
        print("Error: One or both layers are invalid!")
        return

    # Create a new field in the first layer for storing intersection information
    layer1_provider = layer1.dataProvider()
    layer1_provider.addAttributes([QgsField(new_column_name, QVariant.String)])
    layer1.updateFields()

    # Perform intersection analysis
    for feature1 in layer1.getFeatures():
        geom1 = feature1.geometry()
        for feature2 in layer2.getFeatures():
            geom2 = feature2.geometry()
            if geom1.intersects(geom2):
                
                feature1[new_column_name] = 'y'
                break

    # Save the changes to the first layer
    layer1.updateFields()
    layer1.commitChanges()

    print("Intersection analysis completed.")

# Example usage:
#layer1 = QgsProject.instance().mapLayersByName('Layer 1')[0]
#layer2 = QgsProject.instance().mapLayersByName('Layer 2')[0]
#intersection_analysis(layer1, layer2, "intersection")