def export_pdf_layer_to_shp(pdf_path, layer_name, output_shp_path):
    parameters = {
        'INPUT': pdf_path,
        'LAYERS': layer_name,
        'FORMAT': 1,  # 1 for ESRI Shapefile
        'OPTIONS': '',
        'OUTPUT': output_shp_path
    }
    processing.run("gdal:translate", parameters)

# Example usage:
#pdf_path = '/path/to/your/geopdf.pdf'
#layer_name = 'Layer_Name'  # Replace with the name of the layer you want to export
#output_shp_path = '/path/to/output_shapefile.shp'
#
#export_pdf_layer_to_shp(pdf_path, layer_name, output_shp_path)