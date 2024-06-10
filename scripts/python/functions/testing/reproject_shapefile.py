import processing
def reproject_shapefile(input_shapefile, output_shapefile, target_crs):
    parameters = {
        'INPUT': input_shapefile,
        'TARGET_CRS': QgsCoordinateReferenceSystem(target_crs),
        'OUTPUT': output_shapefile
    }
    processing.run("native:reprojectlayer", parameters)
