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

    # Calculate height and width
    height = max_y - min_y
    width = max_x - min_x

    # Return bounding box dimensions and coordinates
    return {
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y,
        'height': height,
        'width': width
    }


# Example usage:
#layer = QgsProject.instance().mapLayersByName('your_layer_name')[0]  # Replace 'your_layer_name' with the actual layer name
#feature_ids = [1, 2, 3]  # List of feature IDs for which you want to calculate the bounding box
#
