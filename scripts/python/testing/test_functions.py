from sklearn.cluster import DBSCAN

def cluster_analysis(input_layer, epsilon, min_samples):
    # Initialize an empty list to store cluster group numbers
    cluster_groups = []
    
    # Iterate over each feature in the input layer
    for feature in input_layer.getFeatures():
        # Extract the geometry (point) from the feature
        geom = feature.geometry()
        print( geom)
        # Extract the GPS coordinates from the point geometry
        coordinates = [(geom.x(), geom.y())]
        
        # Perform DBSCAN clustering on the coordinates
        dbscan = DBSCAN(eps=epsilon, min_samples=min_samples)
        labels = dbscan.fit_predict(coordinates)
        
        # Add cluster group numbers to the list
        cluster_groups.append(labels)
    
    # Return the list of cluster group numbers
    return cluster_groups

# Example usag
input_layer = QgsProject.instance().mapLayersByName('highline_anchors_points')[0]
epsilon = 0.1  # Maximum distance between two samples for them to be considered as in the same neighborhood
min_samples = 2  # The number of samples (or total weight) in a neighborhood for a point to be considered as a core point
clusters = cluster_analysis(input_layer, epsilon, min_samples)

