from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
)
import processing


def merge_layers(layers_to_merge, output_layer_name):
    """
    Merge multiple contour layers into one without dissolving, ensuring each feature is kept intact.

    :param layers_to_merge: An array of the names of the contour layers to merge
    :param output_layer_name: The name for the output merged layer
    :return: The name of the output merged layer
    """
    # Get the list of layers to merge
    merge_layers = []

    for layer_name in layers_to_merge:
        layer = QgsProject.instance().mapLayersByName(layer_name)

        if not layer:
            print(f"Error: Layer '{layer_name}' not found.")
            return None
        
        merge_layers.append(layer[0])

    # Merge all specified contour layers into one without dissolving
    merged_layer = processing.run(
        "native:mergevectorlayers",
        {
            "LAYERS": merge_layers,
            "CRS": merge_layers[0].crs(),
            "OUTPUT": "memory:",
        },
        feedback=None,
    )["OUTPUT"]

    # Rename the merged layer
    merged_layer.setName(output_layer_name)

    # Add the merged layer to the project
    QgsProject.instance().addMapLayer(merged_layer)

    # Optionally remove the original layers
    for layer in merge_layers:
        QgsProject.instance().removeMapLayer(layer)

    return output_layer_name
    
    
    
#one = 'USGS Topo Map Vector Data (Vector) 45919 Tungsten, Colorado 20220512 for 7.5 x 7.5 minute Shapefile'
#two = 'USGS Topo Map Vector Data (Vector) 72681 Gold Hill, Colorado 20220512 for 7.5 x 7.5 minute Shapefile'
#iface.addVectorLayer( usgs_processed_path + one + '/Elev_Contour.shp', 'Elev_Contour1', 'ogr')
#iface.addVectorLayer( usgs_processed_path + two + '/Elev_Contour.shp', 'Elev_Contour2', 'ogr')
#merge_and_resolve_contour_layers( [ 'Elev_Contour1', 'Elev_Contour2'], 'Elev_Contour')