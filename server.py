import pandas as pd
import random
from flask import Flask, jsonify

# Initialize the web server
app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def serve_html():
    # Serves your main index.html[cite: 4]
    return app.send_static_file('index.html')

@app.route('/simulate')
def simulate_gps():
    try:
        # 1. Read your exact coordinate file
        df = pd.read_csv('distance_to_meter and utm_x utm_y.csv')
        
        # 2. Pick 30 random readings from your dataset
        sample = df.sample(n=30)
        
        # 3. Calculate the average of those 30 readings
        avg_lon = sample['longitude'].mean()
        avg_lat = sample['latitude'].mean()
        
        # 4. Send the result back to your JavaScript
        return jsonify({
            'avg_lon': float(avg_lon),
            'avg_lat': float(avg_lat)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Server running at http://127.0.0.1:8000")
    app.run(port=8000, debug=True)