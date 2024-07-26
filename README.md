# Methane Emission Detection System

## Overview

This project aims to develop an automated system for detecting and assessing methane emissions from garbage dumpsites using advanced image processing, geospatial analysis, and a Large Language Model (LLM). The system enhances the efficiency and accuracy of methane emission detection and provides a scalable, cost-effective method for environmental monitoring.

## Key Components

1. **Input Image Processing**: Utilizes advanced image processing techniques to analyze input images of garbage dumpsites.
2. **Geospatial Analysis**: Integrates geospatial data to assess the environmental impact and spatial distribution of methane emissions.
3. **Risk Prediction LLM Model**: Employs a Large Language Model to predict risk levels associated with detected methane emissions.
4. **Alert Mechanism**: Automates the alert system to notify relevant authorities for timely intervention.

## Impact

This solution addresses a critical environmental challenge by providing a scalable and automated method for monitoring methane emissions. By leveraging advanced AI technologies, it promotes safer and healthier communities through continuous surveillance and timely intervention.

## Features

- **Automated Methane Detection**: Detects methane emissions using image processing and geospatial analysis.
- **Risk Assessment**: Predicts risk levels with an LLM model.
- **Real-Time Alerts**: Sends automated alerts to authorities for prompt action.
- **Scalable and Cost-Effective**: Suitable for deployment across multiple dumpsites.

## Getting Started

### Prerequisites

- Python 3.x
- MongoDB
- Flask
- Requests
- GeoPandas
- GDAL
- Hugging Face Transformers

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/methane-emission-detection.git
    cd methane-emission-detection
    ```

2. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up MongoDB:
    ```bash
    sudo service mongod start
    ```

4. Set up the directories:
    ```bash
    mkdir downloads geojson_files
    ```

5. Update the OAuth credentials and API keys in `main.py`:
    ```python
    oauth_credentials = {
        'client_id': 'your_client_id',
        'client_secret': 'your_client_secret'
    }
    opencage_api_key = 'your_opencage_api_key'
    ```

### Running the Application

1. Start the Flask server:
    ```bash
    python app.py
    ```

2. Access the application at `http://localhost:5000`.

### Example Usage

1. Create a GeoJSON file:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"coordinates": [[long, lat], [long, lat], ...]}' http://localhost:5000/create_geojson
    ```

2. Fetch Sentinel-2 data:
    ```bash
    curl -X GET -H "Content-Type: application/json" -d '{"geojson_path": "path/to/geojson"}' http://localhost:5000/fetch/sentinel2
    ```

## Project Structure

- `app.py`: Flask application handling API endpoints and interactions.
- `main.py`: Script for downloading and processing geospatial data.
- `requirements.txt`: List of required Python packages.

## Future Work

- **Model Enhancement**: Improve the LLM's accuracy and contextual understanding for risk assessment.
- **Data Integration**: Incorporate more diverse geospatial and environmental data sources.
- **Real-Time Processing**: Develop capabilities for real-time image processing and analysis.
- **Scalability**: Optimize the system for large-scale deployments across multiple regions.
- **User Interface**: Enhance the user interface for better accessibility and usability.
- **Compliance and Reporting**: Integrate features for regulatory compliance and detailed reporting.
- **Community Engagement**: Implement tools for public awareness and community feedback.

