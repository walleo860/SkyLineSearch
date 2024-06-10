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

# Example usage:
#detect_crossing_lines('layer1_name', 'layer2_name')