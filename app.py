from flask import Flask, jsonify, request, send_file
from pymongo import MongoClient
import requests
from sentinelsat import SentinelAPI, geojson_to_wkt, read_geojson
import geopandas as gpd
from shapely.geometry import Polygon
import os
import zipfile

app = Flask(__name__)

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

@app.route('/')
def home():
    return "Welcome to the Geospatial Data API"

@app.route('/create_geojson', methods=['POST'])
def create_geojson():
    data = request.json
    coordinates = data.get('coordinates')

    if not coordinates:
        return jsonify({'error': 'Coordinates not provided'}), 400

    polygon = Polygon(coordinates)
    gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs="EPSG:4326")

    file_name = f"geojson_{len(os.listdir(geojson_dir)) + 1}.geojson"
    file_path = os.path.join(geojson_dir, file_name)
    gdf.to_file(file_path, driver="GeoJSON")

    return jsonify({'message': 'GeoJSON file created', 'file_path': file_path, 'download_link': f'/download_geojson/{file_name}'})

@app.route('/download_geojson/<file_name>', methods=['GET'])
def download_geojson(file_name):
    file_path = os.path.join(geojson_dir, file_name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/fetch/sentinel2', methods=['GET'])
def fetch_sentinel2():
    data = request.json
    geojson_path = data.get('geojson_path')
    if not geojson_path or not os.path.exists(geojson_path):
        return jsonify({'error': 'Valid GeoJSON path not provided'}), 400

    api = SentinelAPI('your_email@example.com', 'your_password', 'https://scihub.copernicus.eu/dhus')
    footprint = geojson_to_wkt(read_geojson(geojson_path))
    products = api.query(footprint,
                         date=('20230101', '20231231'),
                         platformname='Sentinel-2',
                         processinglevel='Level-2A',
                         cloudcoverpercentage=(0, 30))

    for product_id, product_info in products.items():
        api.download(product_id, directory_path=download_dir)
        db.satellite_imagery.insert_one({
            'source': 'Sentinel-2',
            'product_id': product_id,
            'title': product_info['title'],
            'file_path': os.path.join(download_dir, f"{product_info['title']}.zip")
        })

    return jsonify({'message': 'Sentinel-2 imagery downloaded and stored.'})

@app.route('/fetch/tropomi', methods=['GET'])
def fetch_tropomi():
    data = request.json
    geojson_path = data.get('geojson_path')
    if not geojson_path or not os.path.exists(geojson_path):
        return jsonify({'error': 'Valid GeoJSON path not provided'}), 400

    api = SentinelAPI('your_email@example.com', 'your_password', 'https://s5phub.copernicus.eu/dhus')
    footprint = geojson_to_wkt(read_geojson(geojson_path))
    products = api.query(footprint,
                         date=('20230101', '20231231'),
                         platformname='Sentinel-5P',
                         producttype='L2__CH4___')

    for product_id, product_info in products.items():
        api.download(product_id, directory_path=download_dir)
        db.satellite_imagery.insert_one({
            'source': 'TROPOMI',
            'product_id': product_id,
            'title': product_info['title'],
            'file_path': os.path.join(download_dir, f"{product_info['title']}.zip")
        })

    return jsonify({'message': 'TROPOMI data downloaded and stored.'})

@app.route('/fetch/dem', methods=['GET'])
def fetch_dem():
    dem_url = 'https://e4ftl01.cr.usgs.gov/SRTM/SRTMGL1.003/2000.02.11/N00E036.SRTMGL1.hgt.zip'
    response = requests.get(dem_url)
    zip_path = os.path.join(download_dir, 'SRTM_DEM.zip')
    with open(zip_path, 'wb') as file:
        file.write(response.content)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)
    db.geospatial_data.insert_one({
        'source': 'SRTM DEM',
        'file_path': os.path.join(download_dir, 'N00E036.SRTMGL1.hgt')
    })

    return jsonify({'message': 'DEM data downloaded and stored.'})

@app.route('/fetch/landcover', methods=['GET'])
def fetch_landcover():
    landcover_url = 'https://maps.elie.ucl.ac.be/CCI/viewer/download/ESACCI-LC-L4-LCCS-Map-300m-P1Y-2019-v2.1.1.tif.zip'
    response = requests.get(landcover_url)
    zip_path = os.path.join(download_dir, 'ESA_LandCover.zip')
    with open(zip_path, 'wb') as file:
        file.write(response.content)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)
    db.geospatial_data.insert_one({
        'source': 'ESA Land Cover',
        'file_path': os.path.join(download_dir, 'landcover_data')
    })

    return jsonify({'message': 'Land Cover data downloaded and stored.'})

@app.route('/fetch/admin_boundaries', methods=['GET'])
def fetch_admin_boundaries():
    admin_boundaries_url = 'https://biogeo.ucdavis.edu/data/gadm3.6/gadm36_shp.zip'
    response = requests.get(admin_boundaries_url)
    zip_path = os.path.join(download_dir, 'admin_boundaries.zip')
    with open(zip_path, 'wb') as file:
        file.write(response.content)

    with zipfile.ZipFile(os.path.join(download_dir, 'admin_boundaries.zip'), 'r') as zip_ref:
        zip_ref.extractall(download_dir)
    db.geospatial_data.insert_one({
        'source': 'GADM',
        'file_path': os.path.join(download_dir, 'gadm36_levels_shp')
    })

    return jsonify({'message': 'Administrative boundaries data downloaded and stored.'})

@app.route('/fetch/weather', methods=['GET'])
def fetch_weather():
    weather_url = 'https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=GHCND:USW00094728&startDate=2023-01-01&endDate=2023-12-31&format=json'
    response = requests.get(weather_url)
    weather_data = response.json()
    db.weather_data.insert_many(weather_data)

    return jsonify({'message': 'Weather data downloaded and stored.'})

@app.route('/fetch/ground_truth', methods=['POST'])
def fetch_ground_truth():
    ground_truth_data = request.json
    db.ground_truth_data.insert_many(ground_truth_data)

    return jsonify({'message': 'Ground truth data stored.'})

@app.route('/fetch/geo_info', methods=['POST'])
def fetch_geo_info():
    geo_info_data = request.json
    db.geo_info.insert_many(geo_info_data)

    return jsonify({'message': 'Geographical area information stored.'})

if __name__ == '__main__':
    app.run(debug=True)
