from datetime import datetime, timedelta
import os
from flask import Flask, Response, jsonify, request
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import gzip
from flask_cors import CORS
import io
import pytz  

from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
app.config['SUPABASE_KEY'] = os.getenv('SUPABASE_KEY')

CORS(app, resources={r"/*": {"origins": "*"}})
url=app.config['SUPABASE_URL']
key =app.config['SUPABASE_KEY']
supabase: Client = create_client(url, key)
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

today = datetime.now().date()

first_day_of_this_month = today.replace(day=1)

last_day_of_last_month = first_day_of_this_month - timedelta(days=1)

first_day_of_last_month = last_day_of_last_month.replace(day=1)

first_day_of_last_month_iso = first_day_of_last_month.isoformat()

response = supabase.table("appTemp") \
    .select("*") \
    .gte("createdAt", first_day_of_last_month_iso) \
    .execute()
data = response.data

df = pd.DataFrame(data)  
df['createdAt'] = pd.to_datetime(df['createdAt'])

df['coilTemp'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
df['surroundingTemp'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15

df['surroundingTemp'] = df['surroundingTemp'] + 273.15
df['Relative_COP'] = df['coilTemp']/(df['surroundingTemp'] - df['coilTemp'])

@app.route('/graph/week', methods=['POST'])
def getWeek():
    fig = go.Figure()
    df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce').dt.tz_convert('UTC')
    
    # Get the current time in UTC
    now = pd.Timestamp.now(tz='UTC')
    
    # Calculate the start and end of the week in UTC
    start_of_week = now - pd.DateOffset(days=now.weekday())
    end_of_week = start_of_week + pd.DateOffset(days=6)
    
    # Filter the DataFrame to include only data from this week
    df = df[(df['createdAt'] >= start_of_week) & (df['createdAt'] <= end_of_week)]
    
    # Set 'createdAt' as the index for correct plotting
    df.set_index('createdAt', inplace=True)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df.index, y=df['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df.index, y=df['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    fig.update_layout(
        xaxis_title='Time',
        yaxis=dict(
            title='Temperature (°C)',
        ),
        yaxis2=dict(
            title='Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )
    
    # Serialize the figure to JSON
    graph_json = pio.to_json(fig)
    
    # Compress JSON data with gzip
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(graph_json.encode('utf-8'))
    
    compressed_json = buffer.getvalue()
    
    # Create and return the Flask response
    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = str(len(compressed_json))
    
    return response


@app.route('/graph/month', methods=['POST'])
def get_graph():
    fig = go.Figure()
    
    # Ensure 'createdAt' is in datetime format
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    
    # Set 'createdAt' as the index for correct plotting
    df.set_index('createdAt', inplace=True)
    
    # Add temperature and humidity traces
    fig.add_trace(go.Scatter(x=df.index, y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df.index, y=df['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df.index, y=df['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    # Update layout for dual y-axes
    fig.update_layout(
        xaxis_title='Time',
        yaxis=dict(
            title='Temperature (°C)',
        ),
        yaxis2=dict(
            title='Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )
    
    # Serialize the figure to JSON
    graph_json = pio.to_json(fig)
    
    # Compress JSON data with gzip
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(graph_json.encode('utf-8'))
    
    compressed_json = buffer.getvalue()
    
    # Create and return the Flask response
    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = str(len(compressed_json))
    
    return response

@app.route('/categories', methods=['POST'])
def categorize_cop():
    data = request.json
    
    # Access data fields
    iot_id = data.get('iotID')
    q20 = df['Relative_COP'].quantile(0.2)
    q40 = df['Relative_COP'].quantile(0.4)
    q60 = df['Relative_COP'].quantile(0.6)
    q80 = df['Relative_COP'].quantile(0.8)

    min_value = df['Relative_COP'].min()
    max_value = df['Relative_COP'].max()
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df.set_index('createdAt', inplace=True)
    weekly_avg_cop = df.resample('W')['Relative_COP'].mean()
    weekly_avg_cop_dict = {date.isoformat(): avg for date, avg in weekly_avg_cop.items()}

    row_count = df.shape[0]
    return jsonify({
        "min_value": min_value,
        "q20": q20,
        "q40": q40,
        "q60": q60,
        "q80": q80,
        "max_value": max_value,
        "row_count": row_count,
        "week":weekly_avg_cop_dict
    })

if __name__ == '__main__':
    app.run(port=5000)  
