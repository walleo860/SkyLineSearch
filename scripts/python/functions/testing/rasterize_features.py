def rasterize_topo_layer_with_bbox(pdf_path, layer_name, bounding_box_layer_name, output_raster_path):
    # Find bounding box layer
    bounding_box_layer = QgsProject.instance().mapLayersByName(bounding_box_layer_name)
    if not bounding_box_layer:
        print(f"Bounding box layer '{bounding_box_layer_name}' not found")
        return

    # Check if the bounding box layer contains any features
    if bounding_box_layer[0].featureCount() == 0:
        print(f"Bounding box layer '{bounding_box_layer_name}' contains no features")
        return

    # Get bounding box geometry
    bounding_box_feature = next(bounding_box_layer[0].getFeatures())
    bounding_box_geometry = bounding_box_feature.geometry()

    # Clip and rasterize the topo layer within the bounding box extent
    output_extent = f'{bounding_box_geometry.boundingBox().xMinimum()} {bounding_box_geometry.boundingBox().yMinimum()} {bounding_box_geometry.boundingBox().xMaximum()} {bounding_box_geometry.boundingBox().yMaximum()}'
    command = f'gdalwarp -cutline "{bounding_box_layer[0].dataProvider().dataSourceUri()}" -crop_to_cutline -dstnodata 0 -of GTiff "{pdf_path}" "{output_raster_path}" -te {output_extent}'
    os.system(command)