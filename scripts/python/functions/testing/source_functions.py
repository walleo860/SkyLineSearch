import os
import importlib.util

def source_functions( directory_path):
    # Check if the directory exists
    if not os.path.isdir(directory_path):
        print(f"Error: '{directory_path}' is not a valid directory.")
        return
    # List all files in the directory
    files = os.listdir(directory_path)
    # Iterate over the files
    for file in files:
        # Check if the file is a Python file
        if file.endswith('.py'):
            # Construct the full path to the Python file
            file_path = os.path.join(directory_path, file)

            # Import the module from the file
            module_name = file[:-3]  # Remove the .py extension
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Print the functions defined in the module
            print(f"Functions in {module_name}:")
            for name, obj in module.__dict__.items():
                if callable(obj):
                    print(f"- {name}")

