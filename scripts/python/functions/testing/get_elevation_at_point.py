def get_elevation_at_point(point, raster_layer):
    x = point.x()
    y = point.y()
    # Get raster value at point location
    result = raster_layer.dataProvider().identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue)
    return result.results()[1]

