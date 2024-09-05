from datetime import datetime, timedelta
import json
import os
from flask import Flask, Response, jsonify, request
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import gzip
from flask_cors import CORS
import io

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

df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15

# df['surroundingTemp'] = df['surroundingTemp'] + 273.15
df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])


@app.route('/graph/week', methods=['POST'])
def get_latest_week_data():
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['createdAt_naive'] = df['createdAt'].dt.tz_localize(None)
    current_datetime = np.datetime64('today')
    one_week_ago = current_datetime - np.timedelta64(7, 'D')
    latest_week_data = df[df['createdAt_naive'] >= one_week_ago]
    fig1 = go.Figure()

    # Add temperature trace
    fig1.add_trace(go.Scatter(x=latest_week_data['createdAt'], y=latest_week_data['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))

    # Add coil temperature trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=latest_week_data['createdAt'], y=latest_week_data['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y2'))

    # Add humidity trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=latest_week_data['createdAt'], y=latest_week_data['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    # Update layout for dual y-axes
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Surrounding Temperature (°C)',
        yaxis2=dict(
            title='Coil Temperature (°C) / Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=latest_week_data['createdAt'], y=latest_week_data['Relative_COP'], mode='lines', name='COP'))
    fig2.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=latest_week_data['coilTemp'], y=latest_week_data['Relative_COP'], mode='lines', name='COP'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    combined_json = json.dumps({
        'coilSurrHumi': graph_json1,
        'efficencyTime': graph_json2,
        'efficencyTemp':graph_json3
    })

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(combined_json.encode('utf-8'))

    compressed_json = buffer.getvalue()

    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed_json)

    return response

@app.route('/graph/day', methods=['POST'])
def get_latest_day_data():
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['createdAt_naive'] = df['createdAt'].dt.tz_localize(None)
    current_datetime = np.datetime64('today')
    one_day_ago = current_datetime - np.timedelta64(1, 'D')
    latest_day_data = df[df['createdAt_naive'] >= one_day_ago]
    fig1 = go.Figure()

    # Add temperature trace
    fig1.add_trace(go.Scatter(x=latest_day_data['createdAt'], y=latest_day_data['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))

    # Add coil temperature trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=latest_day_data['createdAt'], y=latest_day_data['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y2'))

    # Add humidity trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=latest_day_data['createdAt'], y=latest_day_data['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    # Update layout for dual y-axes
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Surrounding Temperature (°C)',
        yaxis2=dict(
            title='Coil Temperature (°C) / Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=latest_day_data['createdAt'], y=latest_day_data['Relative_COP'], mode='lines', name='COP'))
    fig2.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=latest_day_data['coilTemp'], y=latest_day_data['Relative_COP'], mode='lines', name='COP'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    combined_json = json.dumps({
        'coilSurrHumi': graph_json1,
        'efficencyTime': graph_json2,
        'efficencyTemp':graph_json3
    })

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(combined_json.encode('utf-8'))

    compressed_json = buffer.getvalue()

    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed_json)

    return response

@app.route('/graph/month', methods=['POST'])
def get_graph():
    # Create first figure
    fig1 = go.Figure()

    # Add temperature trace
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature (°C)', yaxis='y1'))

    # Add coil temperature trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Coil Temperature (°C)', yaxis='y2'))

    # Add humidity trace with secondary y-axis
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingHumidity'], mode='lines', name='Surrounding Humidity (%)', yaxis='y2'))

    # Update layout for dual y-axes
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Surrounding Temperature (°C)',
        yaxis2=dict(
            title='Coil Temperature (°C) / Humidity (%)',
            overlaying='y',
            side='right'
        ),
        legend_title='Variables'
    )
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['createdAt'], y=df['Relative_COP'], mode='lines', name='COP'))
    fig2.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df['coilTemp'], y=df['Relative_COP'], mode='lines', name='COP'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='COP',
        legend_title='Variables'
    )
    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    combined_json = json.dumps({
        'coilSurrHumi': graph_json1,
        'efficencyTime': graph_json2,
        'efficencyTemp':graph_json3
    })

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(combined_json.encode('utf-8'))

    compressed_json = buffer.getvalue()

    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed_json)

    return response

# @app.route("/dashboard",methods=['POST'])
# def dashboard():


@app.route('/categories', methods=['POST'])
def categorize_cop():
    data = request.json
    
    # Access data fields
    iot_id = data.get('iotID')
    print(iot_id,'qwertyuio')
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
    supabase.table("efficiencyPoint").insert({
        "iotID": iot_id,
        "minVal": min_value,
        "q20": q20,
        "q40": q40,
        "q60": q60,
        "q80": q80,
        "maxVal": max_value
    }).execute()
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