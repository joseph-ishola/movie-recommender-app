from flask import Flask, request, render_template, jsonify, send_file
import requests
import os
import io
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure application
app.config['API_URL'] = os.getenv('API_URL', 'http://localhost:5000/api')

@app.route('/')
def home():
    # Check if the API is ready by pinging the status endpoint
    try:
        response = requests.get(f"{app.config['API_URL']}/status", timeout=5)
        if response.status_code == 200 and response.json().get('status') == 'ok':
            api_ready = True
        else:
            api_ready = False
    except Exception:
        api_ready = False
    
    # Render the search page
    return render_template('index.html', api_ready=api_ready)

@app.route('/api/search', methods=['POST'])
def search():
    """Proxy the search request to the API"""
    movie_title = request.form.get('movie_title', '')
    
    try:
        # Forward the request to the API
        response = requests.post(
            f"{app.config['API_URL']}/search",
            data={'movie_title': movie_title}
        )
        
        # Make sure we're returning the raw JSON
        return response.text, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        app.logger.error(f"Error searching for movie: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error contacting recommendation service: {str(e)}'
        }), 500

@app.route('/api/recommendations/<int:movie_id>', methods=['GET'])
def get_recommendations(movie_id):
    """Proxy the recommendations request to the API"""
    try:
        # Forward the request to the API
        response = requests.get(
            f"{app.config['API_URL']}/recommendations/{movie_id}",
            params=request.args
        )
        
        # Return the raw JSON
        return response.text, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        app.logger.error(f"Error getting recommendations: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error contacting recommendation service: {str(e)}'
        }), 500
        
@app.route('/api/visualization/<string:viz_type>/<int:movie_id>', methods=['GET'])
def get_visualization(viz_type, movie_id):
    """Proxy the visualization request to the API"""
    try:
        # Forward the request to the API
        response = requests.get(
            f"{app.config['API_URL']}/visualization/{viz_type}/{movie_id}",
            stream=True
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving visualization: {response.text}'
            }), response.status_code
        
        # Return the image
        return send_file(
            io.BytesIO(response.content),
            mimetype='image/png',
            as_attachment=False,
            download_name=f'{viz_type}_{movie_id}.png'
        )
    except Exception as e:
        app.logger.error(f"Error getting visualization: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error contacting recommendation service: {str(e)}'
        }), 500

if __name__ == '__main__':
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the movie recommender web app')
    parser.add_argument('--port', type=int, default=int(os.getenv('WEBAPP_PORT', 80)),
                        help='Port to run the web app on')
    args = parser.parse_args()
    
    # Use the port from command line arguments
    port = args.port
    
    print(f"Starting web app on port {port}")
    
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )