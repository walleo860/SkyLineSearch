def compare_crs(layer1, layer2):
    crs1 = layer1.crs()
    crs2 = layer2.crs()

    if crs1 != crs2:
        print("Error: CRS of the two layers is different.")
        return False
    else:
        return True