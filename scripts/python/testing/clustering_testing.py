import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsWkbTypes,
)
from PyQt5.QtCore import QVariant

def cluster_points_with_dbscan(layer_name, eps=0.1, min_samples=5):
    """
    Perform DBSCAN clustering on points in a given QGIS layer and update the attribute table.
    """
    # Load the point layer by its name
    point_layers = QgsProject.instance().mapLayersByName(layer_name)
    if not point_layers:
        print(f"Error: Layer '{layer_name}' not found")
        return
    point_layer = point_layers[0]

    # Check if the layer is a point layer
    if point_layer.wkbType() != QgsWkbTypes.Point:
        print("Error: The layer is not a point layer.")
        return
    
    # Extract the X and Y coordinates of each point
    points = []
    feature_ids = []
    for feature in point_layer.getFeatures():
        geom = feature.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            point = geom.asPoint()
            points.append([point.x(), point.y()])
            feature_ids.append(feature.id())
    
    if not points:
        print("No points found in the layer.")
        return
    
    # Convert the list to a NumPy array
    points = np.array(points)

    # Scale the points (optional but recommended)
    scaler = StandardScaler()
    points_scaled = scaler.fit_transform(points)
    
    # Perform DBSCAN clustering on the scaled data
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(points_scaled)
    
    # Get the cluster labels
    cluster_labels = db.labels_
    #print( cluster_labels.head( 10))
    
    # Add a 'cluster_group' field to the point layer if it doesn't exist
    point_layer.startEditing()
    if point_layer.fields().indexFromName("cluster_group") == -1:
        point_layer.addAttribute(QgsField("cluster_group", QVariant.Int))
        point_layer.updateFields()

    # Get the index for the 'cluster_group' field
    cluster_group_index = point_layer.fields().indexFromName("cluster_group")
    
    # Update the 'cluster_group' field for each feature
    for feature, cluster_label in zip(feature_ids, cluster_labels):
        point_layer.changeAttributeValue(feature, cluster_group_index, int(cluster_label))
    
    # Commit the changes
    point_layer.commitChanges()
    
    print("DBSCAN clustering completed and attribute table updated.")


# Usage example
# Adjust the 'layer_name' with your QGIS point layer name
# You can tweak 'eps' and 'min_samples' as needed
cluster_points_with_dbscan("highline_anchors_points", eps=.08, min_samples=15)
apply_categorized_symbology("highline_anchors_points", "cluster_group")
