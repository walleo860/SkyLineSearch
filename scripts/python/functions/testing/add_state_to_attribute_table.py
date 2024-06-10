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

# Usage example:
# Replace 'point_line_layer' and 'polygon_layer' with your actual QgsVectorLayer objects
# point_line_layer = QgsProject.instance().mapLayersByName('point_line_layer_name')[0]
# polygon_layer = QgsProject.instance().mapLayersByName('polygon_layer_name')[0]
# add_intersecting_polygon_ids(point_line_layer, polygon_layer)


