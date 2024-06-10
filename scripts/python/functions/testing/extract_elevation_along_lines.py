from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

def extract_elevation_along_lines(line_layer, contour_layer, output_field_name):    # Prepare raster layer for elevation data (if not already done)
    print( 'start')
    #print( contour_layer.name())
    contour_raster = contour_layer.name() + '_raster'
    print( contour_raster)
    processing.run("gdal:rasterize", {
        'INPUT': contour_layer,
        'FIELD': 'elevation',  # Change this to the field name containing elevation values in your contour layer
        'BURN': 0,
        'WIDTH': contour_layer.rasterUnitsPerPixelX(),
        'HEIGHT': contour_layer.rasterUnitsPerPixelY(),
        'UNITS': 1,
        'EXTENT': contour_layer.extent(),
        'NODATA': 0,
        'DATA_TYPE': 5,  # Float32
        'OUTPUT': contour_raster
    })

    # Get raster layer
    contour_raster_layer = QgsRasterLayer(contour_raster, 'Contour_Raster')
    if not contour_raster_layer.isValid():
        print("Error: Contour raster layer is not valid")
        return

    # Get elevation values along lines
    line_layer.startEditing()
    line_layer_provider = line_layer.dataProvider()
    for feat in line_layer.getFeatures():
        line_geom = feat.geometry()
        line_start_point = line_geom.vertexAt(0)
        line_end_point = line_geom.vertexAt(1)

        # Get elevation at start point
        start_elevation = get_elevation_at_point(line_start_point, contour_raster_layer)
        # Get elevation at end point
        end_elevation = get_elevation_at_point(line_end_point, contour_raster_layer)

        # Save elevation values as attributes
        line_layer_provider.changeAttributeValues({feat.id(): {f"{output_field_name}_start": start_elevation,
                                                               f"{output_field_name}_end": end_elevation}})

    line_layer.commitChanges()
    print("Elevation extraction completed.")

