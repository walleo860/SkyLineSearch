#a function that loads geopdfs
def load_geopdf( path, pdf):
    region= pdf.replace( '.pdf', '')
    
    pdf_path = path + pdf
    
    # Open the GeoPDF file
    ds = gdal.Open(pdf_path)
    
    # Get the number of layers in the GeoPDF
    num_layers = ds.GetLayerCount()
    
    # Loop through each layer and add it to the QGIS project
    for i in range(num_layers):
        layer_name = ds.GetLayerByIndex(i).GetName()
        
        full_name = region + ' — ' + layer_name
        layer = QgsVectorLayer(pdf_path + "|layername=" + layer_name , full_name, "ogr")
        print( layer_name)    
        QgsProject.instance().addMapLayer(layer) 
    ds = None

    


#pdf = 'UT_Moab_20240312_174123218000_TM_geo.pdf'
#path = ''