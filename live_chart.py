import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import MetaTrader5 as mt5
import math

import config

# Initialize Dash application
app = dash.Dash(__name__, title="PRO Trend Pullback Live Chart")

app.layout = html.Div(style={'backgroundColor': '#111111', 'color': 'white', 'fontFamily': 'sans-serif', 'padding': '20px'}, children=[
    html.H2(f"Live Chart (Updates PER TICK) - {config.SYMBOLS[0]} (M5 Timeframe from bot)", style={'textAlign': 'center', 'color': '#00ffcc'}),
    dcc.Graph(id='live-trading-chart', style={'height': '85vh', 'animate': False}),
    dcc.Interval(
        id='chart-update-interval',
        interval=500,  # 500 ms = updates roughly per tick seamlessly
        n_intervals=0
    )
])

def fetch_and_prepare_data():
    if not mt5.initialize(path=config.MT5_PATH, login=config.MT5_ACCOUNT, server=config.MT5_SERVER, password=config.MT5_PASSWORD):
        return None, None

    symbol = config.SYMBOLS[0]
    timeframe = mt5.TIMEFRAME_M5 # Matching your main.py bot explicitly
    
    # Get current tick for the precise exact real-time price
    tick = mt5.symbol_info_tick(symbol)
    
    # Fetch bars
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 150)
    if rates is None or len(rates) == 0:
        return None, None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # -----------------------------
    # Apply EXACT logic from main.py
    # -----------------------------
    # MEDIAN PRICE (HL/2)
    df['median'] = (df['high'] + df['low']) / 2

    # LWMA (Period 1)
    df['lwma'] = df['median']

    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df, tick

@app.callback(
    Output('live-trading-chart', 'figure'),
    [Input('chart-update-interval', 'n_intervals')]
)
def update_chart_live(n):
    df, tick = fetch_and_prepare_data()
    
    if df is None:
        return go.Figure()

    # Create subplots (Main chart + RSI below)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.75, 0.25],
                        subplot_titles=("Price & LWMA (HL/2)", "RSI (14) - Oversold <30, Overbought >67"))
    
    # ---- 1. Candlestick Main Chart ----
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='M5 Candles',
        increasing_line_color='#00ff00', decreasing_line_color='#ff0000'
    ), row=1, col=1)
    
    # Plot LWMA
    fig.add_trace(go.Scatter(x=df['time'], y=df['lwma'], line=dict(color='#00bfff', width=2), name='LWMA (Median)'), row=1, col=1)

    # Plot exact Tick (Bid/Ask) as dots on the leading edge
    if tick:
        last_time = df['time'].iloc[-1]
        fig.add_trace(go.Scatter(x=[last_time, last_time], y=[tick.bid, tick.ask], 
                                 mode='markers+text',
                                 marker=dict(color=['red', 'green'], size=10),
                                 text=[f"Bid: {tick.bid}", f"Ask: {tick.ask}"],
                                 textposition="middle right",
                                 name='Real-time Tick'), row=1, col=1)

    # ---- 2. RSI Sub Chart ----
    fig.add_trace(go.Scatter(x=df['time'], y=df['rsi'], line=dict(color='#ff00ff', width=2), name='RSI(14)'), row=2, col=1)
    
    # Add Oversold / Overbought Lines (30 and 67 from your main.py)
    fig.add_hline(y=67, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Overbought (67)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1, annotation_text="Oversold (30)")

    # Layout configuration
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#111111',
        plot_bgcolor='#111111',
        margin=dict(l=40, r=40, t=30, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uirevision='constant' # Prevents zoom reset on update
    )
    
    # Remove empty gaps for weekends/nights in time-series
    fig.update_xaxes(rangebreaks=[
        dict(bounds=["sat", "mon"]), # hide weekends
    ])
    
    # Fix RSI axes
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    
    return fig

if __name__ == '__main__':
    print("Starting Live Visual Chart Dashboard...")
    print("Access it in your browser at: http://127.0.0.1:8050")
    # Run the server. It won't interfere with your MT5 bot.
    app.run(debug=False, port=8050)
