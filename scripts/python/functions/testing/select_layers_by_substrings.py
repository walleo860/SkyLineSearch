def select_layers_by_substrings(layer_list, substrings):
    selected_layers = []
    for layer in layer_list:
        for substring in substrings:
            if substring.lower() in layer.name().lower():
                selected_layers.append(layer)
                break  # Once a layer matches one of the substrings, move to the next layer
    return selected_layers