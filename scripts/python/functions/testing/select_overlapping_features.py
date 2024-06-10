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
    print( selected_feature_ids)
    return selected_feature_ids
