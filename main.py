import os
import pandas as pd
import yfinance as yf
import requests
import google.generativeai as genai
import json

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# --- FUNCIONES ---

def get_market_data(csv_path="portfolio.csv"):
    """Lee el portfolio y obtiene precios actuales de Yahoo Finance"""
    df = pd.read_csv(csv_path)
    portfolio_data = []
    
    tickers = df['Ticker'].tolist()
    # Descarga masiva de datos para optimizar
    data = yf.download(tickers, period="1d", progress=False)['Close']
    
    # Si descargamos un solo ticker, data es una Series, si son varios es un DataFrame
    # Ajuste para consistencia
    if len(tickers) == 1:
        current_price = data.iloc[-1] # Último precio
        row = df.iloc[0]
        portfolio_data.append({
            "ticker": row['Ticker'],
            "qty": row['Shares'],
            "buy_price": row['Avg_Price'],
            "current_price": round(float(current_price), 2),
            "total_value": round(float(current_price * row['Shares']), 2)
        })
    else:
        for index, row in df.iterrows():
            ticker = row['Ticker']
            try:
                # data.iloc[-1] da el precio de cierre más reciente
                current_price = data[ticker].iloc[-1]
                portfolio_data.append({
                    "ticker": ticker,
                    "qty": row['Shares'],
                    "buy_price": row['Avg_Price'],
                    "current_price": round(float(current_price), 2),
                    "total_value": round(float(current_price * row['Shares']), 2)
                })
            except Exception as e:
                print(f"Error obteniendo datos para {ticker}: {e}")
                
    return portfolio_data

def analyze_with_ai(portfolio_data):
    """Envía los datos a Gemini para análisis"""
    model = genai.GenerativeModel('gemini-2.0-flash') # Modelo rápido y eficiente
    
    prompt = f"""
    Eres un analista financiero senior experto en gestión de riesgos.
    
    MI PORTFOLIO ACTUAL:
    {json.dumps(portfolio_data, indent=2)}
    
    TAREA:
    1. Calcula el rendimiento diario aproximado basado en los datos.
    2. Analiza riesgos potenciales (volatilidad tech, reportes de ganancias próximos, etc).
    3. Dame una recomendación clara: VENDER, MANTENER o COMPRAR para cada activo crítico.
    
    FORMATO DE RESPUESTA (JSON):
    Debes responder ÚNICAMENTE un JSON con esta estructura (sin markdown ```json):
    {{
      "resumen_dia": "Texto breve del rendimiento general (ej: +1.2%)",
      "alerta_clave": "La alerta más importante del mercado hoy (ej: NVDA reporta earnings)",
      "analisis": "Un párrafo breve con tu visión técnica.",
      "acciones_sugeridas": ["Texto 1", "Texto 2"]
    }}
    """
    
    response = model.generate_content(prompt)
    
    # Limpieza básica por si el modelo pone markdown
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def send_telegram_message(analysis_json):
    """Formatea el JSON y lo envía a Telegram"""
    
    # Construimos un mensaje bonito con Emojis
    message = f"""
📊 **REPORTE DIARIO DE PORTFOLIO**

📈 **Rendimiento:** {analysis_json.get('resumen_dia', 'N/A')}

⚠️ **Alerta Clave:** {analysis_json.get('alerta_clave', 'Sin alertas críticas')}

🧠 **Análisis IA:**
{analysis_json.get('analisis', 'No disponible')}

👉 **Acciones Recomendadas:**
"""
    for action in analysis_json.get('acciones_sugeridas', []):
        message += f"- {action}\n"

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    requests.post(url, json=payload)

# --- EJECUCIÓN ---
if __name__ == "__main__":
    print("Iniciando agente...")
    try:
        data = get_market_data()
        print("Datos de mercado obtenidos.")
        
        analysis = analyze_with_ai(data)
        print("Análisis de IA completado.")
        
        send_telegram_message(analysis)
        print("Notificación enviada.")
        
    except Exception as e:
        print(f"Error crítico: {e}")
        # Opcional: Enviarte un mensaje de error a Telegram