import os
import requests
import zipfile
from pymongo import MongoClient
import json
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# MongoDB Client
client = MongoClient('mongodb://localhost:27017/')
db = client.geospatial_data

# Directory for storing downloaded files
download_dir = 'downloads'
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

geojson_dir = 'geojson_files'
if not os.path.exists(geojson_dir):
    os.makedirs(geojson_dir)

# Define OAuth credentials and dataset URLs
oauth_credentials = {
    'client_id': 'sh-fd24de3a-51f8-4a39-aead-da666c220e45',  # Replace with your actual Client ID
    'client_secret': 'ZuakpViWbaRsRLGFEDCeiXJVIzxyIN7D'  # Replace with your actual Client Secret
}

# OpenCage API Key
opencage_api_key = '91ba8446f8a1406cafa2a2724b3cef15'  # Replace with your actual OpenCage API key

datasets = {
    'sentinel2': {
        'url': 'https://apihub.copernicus.eu/dhus/search',
        'query': {
            'platformname': 'Sentinel-2',
            'processinglevel': 'Level-2A',
            'cloudcoverpercentage': '[0 TO 30]'
        }
    },
    'tropomi': {
        'url': 'https://apihub.copernicus.eu/dhus/search',
        'query': {
            'platformname': 'Sentinel-5P',
            'producttype': 'L2__CH4___'
        }
    },
    'dem': {
        'url': 'https://e4ftl01.cr.usgs.gov/SRTM/SRTMGL1.003/2000.02.11/N00E036.SRTMGL1.hgt.zip'
    },
    'landcover': {
        'url': 'https://maps.elie.ucl.ac.be/CCI/viewer/download/ESACCI-LC-L4-LCCS-Map-300m-P1Y-2019-v2.1.1.tif.zip'
    },
    'admin_boundaries': {
        'url': 'https://biogeo.ucdavis.edu/data/gadm3.6/gadm36_shp.zip'
    },
    'weather': {
        'url': 'https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=GHCND:USW00094728&startDate=2023-01-01&endDate=2023-12-31&format=json'
    }
}

# Function to generate coordinates from place name using OpenCage Geocoding API
def get_coordinates_from_place(place_name):
    url = f'https://api.opencagedata.com/geocode/v1/json?q={place_name}&key={opencage_api_key}'
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error: Unable to fetch coordinates for {place_name}. HTTP Status Code: {response.status_code}")
    try:
        data = response.json()
        if not data['results']:
            raise ValueError(f"No coordinates found for the place: {place_name}")
        # Get the bounding box coordinates (left, bottom, right, top)
        bounding_box = data['results'][0]['bounds']
        coordinates = [
            [bounding_box['northeast']['lng'], bounding_box['northeast']['lat']],  # top right
            [bounding_box['northeast']['lng'], bounding_box['southwest']['lat']],  # bottom right
            [bounding_box['southwest']['lng'], bounding_box['southwest']['lat']],  # bottom left
            [bounding_box['southwest']['lng'], bounding_box['northeast']['lat']],  # top left
            [bounding_box['northeast']['lng'], bounding_box['northeast']['lat']]   # closing the polygon
        ]
        return coordinates
    except json.JSONDecodeError as e:
        raise Exception(f"Error: Failed to decode JSON response. Details: {str(e)}")

# Function to create a GeoJSON file from generated coordinates
def create_geojson_file(place_name):
    coordinates = get_coordinates_from_place(place_name)
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                },
                "properties": {}
            }
        ]
    }

    geojson_path = os.path.join(geojson_dir, 'aoi.geojson')
    with open(geojson_path, 'w') as file:
        json.dump(geojson_data, file)

    return geojson_path

# Function to download and extract zip files
def download_and_extract_zip(url, output_dir):
    response = requests.get(url)
    zip_path = os.path.join(output_dir, 'temp.zip')
    with open(zip_path, 'wb') as file:
        file.write(response.content)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    os.remove(zip_path)

# Function to authenticate and get access token
def get_access_token():
    token_url = "https://apihub.copernicus.eu/dhus/oauth/token"
    auth = HTTPBasicAuth(oauth_credentials['client_id'], oauth_credentials['client_secret'])
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    response = session.post(token_url, auth=auth, data={'grant_type': 'client_credentials'})
    if response.status_code != 200:
        raise Exception(f"Error: Unable to fetch access token. HTTP Status Code: {response.status_code}")
    token = response.json().get('access_token')
    return token

# Function to download Sentinel-2 data
def download_sentinel2(geojson_path, access_token):
    with open(geojson_path, 'r') as f:
        geojson = json.load(f)
    coordinates = geojson['features'][0]['geometry']['coordinates'][0]
    bbox = f"{coordinates[0][1]},{coordinates[0][0]},{coordinates[2][1]},{coordinates[2][0]}"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'q': f'footprint:"Intersects(POLYGON(({bbox})))"',
        'platformname': datasets['sentinel2']['query']['platformname'],
        'processinglevel': datasets['sentinel2']['query']['processinglevel'],
        'cloudcoverpercentage': datasets['sentinel2']['query']['cloudcoverpercentage'],
        'start': '2023-01-01T00:00:00Z',
        'end': '2023-12-31T23:59:59Z',
        'rows': 5
    }
    
    response = requests.get(datasets['sentinel2']['url'], headers=headers, params=params)
    products = response.json().get('feed', {}).get('entry', [])
    
    for product in products:
        product_id = product['id']
        download_url = f"https://apihub.copernicus.eu/dhus/odata/v1/Products('{product_id}')/$value"
        response = requests.get(download_url, headers=headers)
        file_path = os.path.join(download_dir, f"{product_id}.zip")
        with open(file_path, 'wb') as file:
            file.write(response.content)
        db.satellite_imagery.insert_one({
            'source': 'Sentinel-2',
            'product_id': product_id,
            'file_path': file_path
        })

# Function to download TROPOMI data
def download_tropomi(geojson_path, access_token):
    with open(geojson_path, 'r') as f:
        geojson = json.load(f)
    coordinates = geojson['features'][0]['geometry']['coordinates'][0]
    bbox = f"{coordinates[0][1]},{coordinates[0][0]},{coordinates[2][1]},{coordinates[2][0]}"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'q': f'footprint:"Intersects(POLYGON(({bbox})))"',
        'platformname': datasets['tropomi']['query']['platformname'],
        'producttype': datasets['tropomi']['query']['producttype'],
        'start': '2023-01-01T00:00:00Z',
        'end': '2023-12-31T23:59:59Z',
        'rows': 5
    }
    
    response = requests.get(datasets['tropomi']['url'], headers=headers, params=params)
    products = response.json().get('feed', {}).get('entry', [])
    
    for product in products:
        product_id = product['id']
        download_url = f"https://apihub.copernicus.eu/dhus/odata/v1/Products('{product_id}')/$value"
        response = requests.get(download_url, headers=headers)
        file_path = os.path.join(download_dir, f"{product_id}.zip")
        with open(file_path, 'wb') as file:
            file.write(response.content)
        db.satellite_imagery.insert_one({
            'source': 'TROPOMI',
            'product_id': product_id,
            'file_path': file_path
        })

# Download DEM data
def download_dem():
    download_and_extract_zip(datasets['dem']['url'], download_dir)
    db.geospatial_data.insert_one({
        'source': 'SRTM DEM',
        'file_path': os.path.join(download_dir, 'N00E036.SRTMGL1.hgt')
    })

# Download Land Cover data
def download_landcover():
    download_and_extract_zip(datasets['landcover']['url'], download_dir)
    db.geospatial_data.insert_one({
        'source': 'ESA Land Cover',
        'file_path': os.path.join(download_dir, 'landcover_data')
    })

# Download Administrative Boundaries data
def download_admin_boundaries():
    download_and_extract_zip(datasets['admin_boundaries']['url'], download_dir)
    db.geospatial_data.insert_one({
        'source': 'GADM',
        'file_path': os.path.join(download_dir, 'gadm36_levels_shp')
    })

# Download Weather data
def download_weather():
    response = requests.get(datasets['weather']['url'])
    weather_data = response.json()
    db.weather_data.insert_many(weather_data)

# Main function to download and store all datasets
def main():
    place_name = input("Enter the name of the place: ")
    geojson_path = create_geojson_file(place_name)
    access_token = get_access_token()
    print("Downloading and storing datasets...")
    download_sentinel2(geojson_path, access_token)
    download_tropomi(geojson_path, access_token)
    download_dem()
    download_landcover()
    download_admin_boundaries()
    download_weather()
    print("All datasets downloaded and stored successfully.")

if __name__ == '__main__':
    main()
