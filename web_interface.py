import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time

from config import Config
from trading_bot import TradingBot

# Initialize the bot
config = Config()
bot = TradingBot()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Gelişmiş Trading Bot"

# Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🤖 Gelişmiş Trading Bot", className="text-center mb-4"),
            html.Hr()
        ])
    ]),
    
    # Bot Status
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Bot Durumu"),
                dbc.CardBody([
                    html.Div(id="bot-status-content")
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Risk Metrikleri"),
                dbc.CardBody([
                    html.Div(id="risk-metrics-content")
                ])
            ])
        ], width=6)
    ], className="mb-4"),
    
    # Control Buttons
    dbc.Row([
        dbc.Col([
            dbc.Button("Bot Başlat", id="start-bot", color="success", className="me-2"),
            dbc.Button("Bot Durdur", id="stop-bot", color="danger", className="me-2"),
            dbc.Button("Yenile", id="refresh-data", color="primary")
        ], className="text-center")
    ], className="mb-4"),
    
    # Trading Pairs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Trading Çiftleri"),
                dbc.CardBody([
                    html.Div(id="trading-pairs-content")
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Active Positions
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Aktif Pozisyonlar"),
                dbc.CardBody([
                    html.Div(id="active-positions-content")
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Market Analysis
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Piyasa Analizi"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id="pair-selector",
                        options=[{"label": pair, "value": pair} for pair in config.TRADING_PAIRS],
                        value=config.TRADING_PAIRS[0] if config.TRADING_PAIRS else None,
                        placeholder="Trading çifti seçin"
                    ),
                    dcc.Graph(id="market-chart")
                ])
            ])
        ])
    ], className="mb-4"),
    
    # AI Model Status
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("AI Model Durumu"),
                dbc.CardBody([
                    html.Div(id="ai-model-content")
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Son Analizler"),
                dbc.CardBody([
                    html.Div(id="last-analysis-content")
                ])
            ])
        ], width=6)
    ], className="mb-4"),
    
    # Auto-refresh interval
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # 30 seconds
        n_intervals=0
    )
], fluid=True)

# Callbacks
@app.callback(
    Output("bot-status-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_bot_status(n_intervals, n_clicks):
    try:
        status = bot.get_bot_status()
        
        return [
            html.P(f"🟢 Çalışıyor" if status.get('is_running', False) else "🔴 Durdu"),
            html.P(f"💰 Bakiye: {status.get('balance', 0):.2f} USDT"),
            html.P(f"📊 Aktif Pozisyon: {status.get('active_positions', 0)}"),
            html.P(f"🤖 AI Model: {'✅ Yüklü' if status.get('ai_model_loaded', False) else '❌ Yüklenmedi'}")
        ]
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("risk-metrics-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_risk_metrics(n_intervals, n_clicks):
    try:
        risk_metrics = bot.risk_manager.get_risk_metrics()
        
        return [
            html.P(f"📉 Günlük Kayıp: {risk_metrics.get('daily_loss', 0):.4f}"),
            html.P(f"🎯 Kayıp Limiti: {risk_metrics.get('daily_loss_limit', 0):.4f}"),
            html.P(f"📈 Günlük P&L: {risk_metrics.get('daily_pnl', 0):.2f} USDT"),
            html.P(f"🏆 Kazanma Oranı: {risk_metrics.get('daily_win_rate', 0):.1%}"),
            html.P(f"📊 Günlük İşlem: {risk_metrics.get('daily_trades_count', 0)}")
        ]
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("trading-pairs-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_trading_pairs(n_intervals, n_clicks):
    try:
        pairs = config.TRADING_PAIRS
        
        return [
            html.Div([
                html.Span(f"🪙 {pair}", className="badge bg-primary me-2 mb-2")
                for pair in pairs
            ])
        ]
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("active-positions-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_active_positions(n_intervals, n_clicks):
    try:
        positions = bot.active_positions
        
        if not positions:
            return [html.P("Aktif pozisyon yok")]
        
        position_cards = []
        for pair, position in positions.items():
            current_price = bot.exchange_client.get_current_price(pair)
            pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
            
            color = "success" if pnl_percent > 0 else "danger"
            
            card = dbc.Card([
                dbc.CardBody([
                    html.H6(f"📈 {pair}"),
                    html.P(f"Giriş: {position['entry_price']:.4f}"),
                    html.P(f"Güncel: {current_price:.4f}"),
                    html.P(f"P&L: {pnl_percent:.2f}%", className=f"text-{color}"),
                    html.P(f"Strateji: {position['strategy']}"),
                    html.Small(f"Güven: {position['confidence']:.2f}")
                ])
            ], className="mb-2")
            
            position_cards.append(card)
        
        return position_cards
        
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("market-chart", "figure"),
    [Input("pair-selector", "value"),
     Input("interval-component", "n_intervals")]
)
def update_market_chart(selected_pair, n_intervals):
    try:
        if not selected_pair:
            return go.Figure()
        
        # Get market data
        market_data = bot.exchange_client.get_ohlcv(selected_pair, '5m', 100)
        
        if market_data.empty:
            return go.Figure()
        
        # Create candlestick chart
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{selected_pair} Fiyat Grafiği', 'Hacim'),
            row_width=[0.7, 0.3]
        )
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=market_data.index,
            open=market_data['open'],
            high=market_data['high'],
            low=market_data['low'],
            close=market_data['close'],
            name='OHLC'
        ), row=1, col=1)
        
        # Volume
        fig.add_trace(go.Bar(
            x=market_data.index,
            y=market_data['volume'],
            name='Hacim'
        ), row=2, col=1)
        
        # Update layout
        fig.update_layout(
            title=f"{selected_pair} Market Analizi",
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        return fig
        
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Hata: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

@app.callback(
    Output("ai-model-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_ai_model_status(n_intervals, n_clicks):
    try:
        ai_model = bot.ai_model
        
        return [
            html.P(f"🤖 Model Durumu: {'✅ Yüklü' if ai_model.model is not None else '❌ Yüklenmedi'}"),
            html.P(f"📅 Son Eğitim: {ai_model.last_training.strftime('%Y-%m-%d %H:%M') if ai_model.last_training else 'Hiç eğitilmedi'}"),
            html.P(f"🔄 Yeniden Eğitim: {'✅ Gerekli' if ai_model.should_retrain() else '❌ Gerekli değil'}")
        ]
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("last-analysis-content", "children"),
    [Input("interval-component", "n_intervals"),
     Input("refresh-data", "n_clicks")]
)
def update_last_analysis(n_intervals, n_clicks):
    try:
        last_analysis = bot.last_analysis
        
        if not last_analysis:
            return [html.P("Henüz analiz yapılmadı")]
        
        analysis_list = []
        for pair, analysis in list(last_analysis.items())[:5]:  # Son 5 analiz
            timestamp = analysis['timestamp'].strftime('%H:%M:%S')
            signal = analysis['combined_signal'].get('signal', 'none')
            confidence = analysis['combined_signal'].get('combined_confidence', 0)
            
            signal_icon = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
            
            analysis_list.append(
                html.Div([
                    html.Small(f"{timestamp} - {pair} {signal_icon} ({confidence:.2f})")
                ], className="mb-1")
            )
        
        return analysis_list
        
    except Exception as e:
        return [html.P(f"Hata: {str(e)}")]

@app.callback(
    Output("start-bot", "disabled"),
    [Input("start-bot", "n_clicks")]
)
def start_bot(n_clicks):
    if n_clicks:
        try:
            if not bot.is_running:
                # Start bot in a separate thread
                bot_thread = threading.Thread(target=bot.start, daemon=True)
                bot_thread.start()
                return True
        except Exception as e:
            print(f"Bot başlatma hatası: {e}")
    return False

@app.callback(
    Output("stop-bot", "disabled"),
    [Input("stop-bot", "n_clicks")]
)
def stop_bot(n_clicks):
    if n_clicks:
        try:
            bot.stop()
            return True
        except Exception as e:
            print(f"Bot durdurma hatası: {e}")
    return False

if __name__ == '__main__':
    app.run_server(
        debug=True,
        host=config.WEB_HOST,
        port=config.WEB_PORT
    )