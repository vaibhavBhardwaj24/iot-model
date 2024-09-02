import os
from flask import Flask, Response
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import gzip
from flask_cors import CORS
import io

from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
app.config['SUPABASE_KEY'] = os.getenv('SUPABASE_KEY')

CORS(app)
url=app.config['SUPABASE_URL']
key =app.config['SUPABASE_KEY']
supabase: Client = create_client(url, key)
response = supabase.table("appTemp").select("*").execute()

data = response.data

df = pd.DataFrame(data)  

# Convert 'createdAt' to datetime format
df['createdAt'] = pd.to_datetime(df['createdAt'])

@app.route('/api/getGraph', methods=['POST'])
def get_graph():
    fig = go.Figure()

    # Add temperature trace
    fig.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))

    # Add coil temperature trace with secondary y-axis
    fig.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y2'))

    # Add humidity trace with secondary y-axis
    fig.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    # Update layout for dual y-axes
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Surrounding Temperature (°C)',
        yaxis2=dict(
            title='Coil Temperature (°C) / Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )

    # Convert figure to JSON
    graph_json = pio.to_json(fig)

    # Compress JSON data with gzip
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(graph_json.encode('utf-8'))

    compressed_json = buffer.getvalue()

    # Create the Flask response with correct headers
    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed_json)

    return response


if __name__ == '__main__':
    app.run(port=3000)  # Change 5001 to your desired port number
