import requests
import zipfile
import os
from io import BytesIO
import pyproj
import tempfile

def convert_bbox_to_decimal_degrees(utm_bbox, source_epsg, target_epsg=4326):
    """
    Convert a bounding box from one EPSG to another (default to decimal degrees, EPSG:4326).
    
    :param utm_bbox: Tuple of (min_x, min_y, max_x, max_y)
    :param source_epsg: The source EPSG code (e.g., 26912 for UTM Zone 12N)
    :param target_epsg: The target EPSG code (default is 4326 for WGS 84 in decimal degrees)
    :return: Bounding box in decimal degrees (min_lon, min_lat, max_lon, max_lat)
    """
    # Create a transformer from the source EPSG to the target EPSG
    transformer = pyproj.Transformer.from_crs(f"EPSG:{source_epsg}", f"EPSG:{target_epsg}", always_xy=True)

    # Unpack the bounding box
    min_x, min_y, max_x, max_y = utm_bbox

    # Convert the min and max coordinates to decimal degrees
    min_lon, min_lat = transformer.transform(min_x, min_y)
    max_lon, max_lat = transformer.transform(max_x, max_y)

    # Return the converted bounding box
    return (min_lon, min_lat, max_lon, max_lat)
 

def download_shapefile_from_bbox(bbox, output_folder):
    """
    Download a shapefile from an API using a bounding box.

    :param bbox: Tuple of (min_lon, min_lat, max_lon, max_lat)
    :param output_folder: Directory to save the shapefile
    :return: Path to the extracted shapefile folder or None if an error occurred
    """
    #bbox = converted_bbox 
    #output_folder = usgs_path
    
    # Format the bounding box as a query parameter
    bbox_str = ",".join(map(str, bbox))
    # Build the request URL
    request_url = "https://tnmaccess.nationalmap.gov/api/v1/products?bbox=" + bbox_str + "&prodExtents=7.5%20x%207.5%20minute&prodFormats=Shapefile&start=2022-01-01&outputFormat=JSON"

    # Fetch the response from the API
    response = requests.get(request_url)

    # Check the response status code
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return None

    # Check the content type
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        print("Error: Response content type is not JSON")
        print("Response content (first 200 characters):", response.content[:200])
        return None

    # Try to parse the response as JSON
    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Unable to parse response as JSON")
        print("Response content (first 200 characters):", response.content[:200])
        return None

    # Check if the response contains data to process
    if "items" not in response_json:
        print("Error: No items found in the response")
        return None

    # Parse the response JSON to get the items
    items = response_json.get("items", [])
    
    if not items:
        print("Error: No shapefiles found for the given bounding box.")
        return None

    extracted_folders = []

    # Process each item to download and extract its shapefile
    for item in items:
        title = item.get("title", "default_folder")
        download_url = item.get("downloadURL", None)
        
        if not download_url:
            print(f"Error: No download URL found for item '{title}'.")
            continue

        # Create a new folder based on the item's title
        specific_output_folder = os.path.join(output_folder, title)
        
        if not os.path.exists(specific_output_folder):
            os.makedirs(specific_output_folder, exist_ok=True)

        # Check if the shapefile has already been downloaded
        if os.listdir(specific_output_folder):
            print(f"Shapefile '{title}' already exists in '{specific_output_folder}'. Skipping download.")
            extracted_folders.append(specific_output_folder)
            continue

        # Create a temporary file to save the response content
        temp_zip_path = os.path.join(tempfile.gettempdir(), "downloaded_shapefile.zip")

        # Download the shapefile from the provided link
        response = requests.get(download_url, stream=True)

        # Write the response content to the temporary file
        with open(temp_zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        # Check if the file is a valid zipfile
        if not zipfile.is_zipfile(temp_zip_path):
            print(f"Error: The downloaded file '{title}' is not a valid zipfile.")
            continue

        # Extract the zipfile to the specific output folder
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            zip_ref.extractall(specific_output_folder)

        print(f"Shapefile '{title}' downloaded and extracted successfully.")
        extracted_folders.append(specific_output_folder)

    return extracted_folders   


#utm_bbox = bb['min_x'],bb['min_y'], bb['max_x'],  bb['max_y']
#converted_bbox = convert_bbox_to_decimal_degrees( utm_bbox, '26912')
## Download a shapefile from the National Map
#download_shapefile_from_bbox( converted_bbox, usgs_path+'api_download')