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
one_week_ago = today - timedelta(weeks=1)

# Calculate the date 1 day ago
one_day_ago = today - timedelta(days=1)

# Format the dates as ISO strings
one_week_ago_iso = one_week_ago.isoformat()
one_day_ago_iso = one_day_ago.isoformat()


@app.route('/graph/week', methods=['POST'])
def get_latest_week_data():
    req_data = request.get_json()
    iot_id = req_data.get('id')
    response = supabase.table("appTemp") \
    .select("*") \
    .eq("iotID", iot_id) \
    .gte("createdAt", one_week_ago_iso) \
    .order("createdAt", desc=True) \
    .execute()
    data = response.data

    df = pd.DataFrame(data)  
    df['createdAt'] = pd.to_datetime(df['createdAt'])

    df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
    df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15
    df['outsideTemp_k']=pd.to_numeric(df['outsideTemp'], errors='coerce') + 273.15
    df['outsideCoilTemp_k']=pd.to_numeric(df['outsideCoilTemp'], errors='coerce') + 273.15
    # df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])
    df['Relative_COP'] =( (df['coilTemp_k']-df['surroundingTemp_k'])+(df['outsideHumidity']-df['surroundingHumidity']))/((df['outsideCoilTemp_k']-df['outsideTemp_k'])+(df['coilTemp_k']-df['surroundingTemp_k']))
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='COndenser Coil Temperature (°C)', yaxis='y1'))
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature (°C)', yaxis='y1'))
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
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
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature',yaxis='y1'))
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    fig4=go.Figure()
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig4.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    # fig5=go.Figure()
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    # fig5.update_layout(
    #     xaxis_title='Time',
    #     yaxis_title='Temperature (°C)',
    #     legend_title='Variables'
    # )

    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    graph_json4 = pio.to_json(fig4)
    # graph_json5=pio.to_json(fig5)
    combined_json = json.dumps({
        'coilDiff': graph_json1,
        'efficencyTime': graph_json2,
        'indoorTempDiff':graph_json3,
        'outdoorTempDiff':graph_json4

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
    req_data = request.get_json()
    iot_id = req_data.get('id')
    response = supabase.table("appTemp") \
        .select("*") \
        .eq("iotID", iot_id) \
        .gte("createdAt", one_day_ago_iso) \
        .order("createdAt", desc=True) \
        .execute()
    
    data = response.data

    # Check if there's data
    if not data:
        # Return a response indicating no data or handle accordingly
        empty_response = json.dumps({"message": "No data available"})
        return Response(empty_response, content_type='application/json')

    # Convert data to DataFrame
    df = pd.DataFrame(data)  
    
    # Ensure 'createdAt' column exists before processing
    if 'createdAt' not in df.columns:
        return Response(json.dumps({"message": "'createdAt' column is missing in the data"}), content_type='application/json')

    df['createdAt'] = pd.to_datetime(df['createdAt'])

    # Ensure columns exist before processing
    if 'coilTemp' not in df.columns or 'surroundingTemp' not in df.columns:
        return Response(json.dumps({"message": "Required columns are missing"}), content_type='application/json')

    df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
    df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15
    df['outsideTemp_k']=pd.to_numeric(df['outsideTemp'], errors='coerce') + 273.15
    df['outsideCoilTemp_k']=pd.to_numeric(df['outsideCoilTemp'], errors='coerce') + 273.15
    # df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])
    df['Relative_COP'] =( (df['coilTemp_k']-df['surroundingTemp_k'])+(df['outsideHumidity']-df['surroundingHumidity']))/((df['outsideCoilTemp_k']-df['outsideTemp_k'])+(df['coilTemp_k']-df['surroundingTemp_k']))
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='COndenser Coil Temperature (°C)', yaxis='y1'))
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature (°C)', yaxis='y1'))
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
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
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature',yaxis='y1'))
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    fig4=go.Figure()
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig4.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    # fig5=go.Figure()
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    # fig5.update_layout(
    #     xaxis_title='Time',
    #     yaxis_title='Temperature (°C)',
    #     legend_title='Variables'
    # )

    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    graph_json4 = pio.to_json(fig4)
    # graph_json5=pio.to_json(fig5)
    combined_json = json.dumps({
        'coilDiff': graph_json1,
        'efficencyTime': graph_json2,
        'indoorTempDiff':graph_json3,
        'outdoorTempDiff':graph_json4

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
    req_data = request.get_json()
    iot_id = req_data.get('id')
    response = supabase.table("appTemp") \
    .select("*") \
    .eq("iotID", iot_id) \
    .gte("createdAt", first_day_of_last_month_iso) \
    .order("createdAt", desc=True) \
    .execute()
    data = response.data

    df = pd.DataFrame(data)  
    df['createdAt'] = pd.to_datetime(df['createdAt'])

    
    df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
    df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15
    df['outsideTemp_k']=pd.to_numeric(df['outsideTemp'], errors='coerce') + 273.15
    df['outsideCoilTemp_k']=pd.to_numeric(df['outsideCoilTemp'], errors='coerce') + 273.15
    # df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])
    df['Relative_COP'] =( (df['coilTemp_k']-df['surroundingTemp_k'])+(df['outsideHumidity']-df['surroundingHumidity']))/((df['outsideCoilTemp_k']-df['outsideTemp_k'])+(df['coilTemp_k']-df['surroundingTemp_k']))
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='COndenser Coil Temperature (°C)', yaxis='y1'))
    fig1.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature (°C)', yaxis='y1'))
    fig1.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
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
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Evaporator Coil Temperature',yaxis='y1'))
    fig3.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig3.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    fig4=go.Figure()
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideCoilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    fig4.add_trace(go.Scatter(x=df['createdAt'], y=df['outsideTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    fig4.update_layout(
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Variables'
    )
    # fig5=go.Figure()
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['coilTemp'], mode='lines', name='Condenser Coil Temperature',yaxis='y1'))
    # fig5.add_trace(go.Scatter(x=df['createdAt'], y=df['surroundingTemp'], mode='lines', name='Surrounding Temperature',yaxis='y1'))
    # fig5.update_layout(
    #     xaxis_title='Time',
    #     yaxis_title='Temperature (°C)',
    #     legend_title='Variables'
    # )

    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    graph_json4 = pio.to_json(fig4)
    # graph_json5=pio.to_json(fig5)
    combined_json = json.dumps({
        'coilDiff': graph_json1,
        'efficencyTime': graph_json2,
        'indoorTempDiff':graph_json3,
        'outdoorTempDiff':graph_json4

    })

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as file:
        file.write(combined_json.encode('utf-8'))

    compressed_json = buffer.getvalue()

    response = Response(compressed_json, content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed_json)

    return response

@app.route("/dashboard",methods=['POST'])
def dashboard():
    req_data = request.get_json()
    iot_id = req_data.get('id')
    response = supabase.table("appTemp") \
    .select("*") \
    .eq("iotID", iot_id) \
    .gte("createdAt", first_day_of_last_month_iso) \
    .order("createdAt", desc=True) \
    .execute()
    data = response.data

    df = pd.DataFrame(data)  
    df['createdAt'] = pd.to_datetime(df['createdAt'])

    df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
    df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15
    df['outsideTemp_k']=pd.to_numeric(df['outsideTemp'], errors='coerce') + 273.15
    df['outsideCoilTemp_k']=pd.to_numeric(df['outsideCoilTemp'], errors='coerce') + 273.15
    # df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])
    df['Relative_COP'] =( (df['coilTemp_k']-df['surroundingTemp_k'])+(df['outsideHumidity']-df['surroundingHumidity']))/((df['outsideCoilTemp_k']-df['outsideTemp_k'])+(df['coilTemp_k']-df['surroundingTemp_k']))
    
    # df['createdAt'] = pd.to_datetime(df['createdAt'])
    df.set_index('createdAt', inplace=True)
    weekly_avg_cop = df.resample('W')['Relative_COP'].mean()
    weekly_avg_cop = weekly_avg_cop.fillna(0)
    weekly_avg_cop_dict = {date.isoformat(): avg for date, avg in weekly_avg_cop.items()}
    
    first_row = df.head(1).to_dict(orient='records')[0] if not df.empty else {}
    monthly_avg_cop = df['Relative_COP'].mean()
    # Prepare JSON response
    response_data = {
        "week": weekly_avg_cop_dict,
        # "surroundingTemp": first_row_surrounding_temp,
        "monthlyAvgCOP": monthly_avg_cop,
        "latest_entry":first_row
    }

    return jsonify(response_data)


@app.route('/categories', methods=['POST'])
def categorize_cop():
    req_data = request.get_json()
    iot_id = req_data.get('id')
    response = supabase.table("appTemp") \
    .select("*") \
    .eq("iotID", iot_id) \
    .gte("createdAt", first_day_of_last_month_iso) \
    .order("createdAt", desc=True) \
    .execute()
    data = response.data

    df = pd.DataFrame(data)  
    df['createdAt'] = pd.to_datetime(df['createdAt'])

    df['coilTemp_k'] = pd.to_numeric(df['coilTemp'], errors='coerce') + 273.15
    df['surroundingTemp_k'] = pd.to_numeric(df['surroundingTemp'], errors='coerce') + 273.15

# df['surroundingTemp'] = df['surroundingTemp'] + 273.15
    # df['Relative_COP'] = df['coilTemp_k']/(df['surroundingTemp_k'] - df['coilTemp_k'])
    df['Relative_COP'] =( (df['coilTemp_k']-df['surroundingTemp_k'])+(df['outsideHumidity']-df['surroundingHumidity']))/((df['outsideCoilTemp_k']-df['outsideTemp_k'])+(df['coilTemp_k']-df['surroundingTemp_k']))
    
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
        
    })

if __name__ == '__main__':
    app.run(port=5000)  