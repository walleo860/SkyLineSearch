def save_layer(layer, output_path, file_format):
    # Define the output options
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = file_format
    options.layerName = layer.name()  # Use the original layer name
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    # Save the layer to the specified output path
    result = QgsVectorFileWriter.writeAsVectorFormat(layer, output_path, QgsCoordinateTransformContext(), options)
    
    # Check if the layer was saved successfully
    if result[0] != QgsVectorFileWriter.NoError:
        print(f"Error: Unable to save layer '{layer.name()}' to '{output_path}'")
    else:
        print(f"Layer '{layer.name()}' saved successfully to '{output_path}'")
