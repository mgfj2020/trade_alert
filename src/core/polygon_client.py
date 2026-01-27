import requests
import pandas as pd
from datetime import datetime, timedelta
from src.config import API_KEY

# Configuración específica de Polygon
INTERVAL_MAP = {
    "5min":  (5,  "minute"),
    "15min": (15, "minute"),
    "30min": (30, "minute"),
    "1H":    (1,  "hour"),
    "4H":    (4,  "hour"),
    "1D":    (1,  "day"),
}

LOOKBACK_DAYS = {
    "5min":  7,
    "15min": 14,
    "30min": 21,
    "1H":    30,
    "4H":    60,
    "1D":    300,
}

def obtener_velas_polygon(stock, intervalo, fecha_inicio=None, fecha_fin=None):
    """
    Descarga velas de Polygon. Maneja internamente el lookback por TF si no se pasan fechas.
    """
    if intervalo not in INTERVAL_MAP:
        raise ValueError("Intervalo inválido.")
    
    mult, unidad = INTERVAL_MAP[intervalo]

    if not fecha_fin:
        fecha_fin = datetime.utcnow().strftime("%Y-%m-%d")
    
    if not fecha_inicio:
        if intervalo not in LOOKBACK_DAYS:
            raise ValueError("No hay lookback definido para este intervalo y no se proveyó fecha_inicio.")
        dias_atras = LOOKBACK_DAYS[intervalo]
        fecha_inicio = (datetime.utcnow() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")

    url = f"https://api.polygon.io/v2/aggs/ticker/{stock}/range/{mult}/{unidad}/{fecha_inicio}/{fecha_fin}"
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY}

    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise Exception(f"Error {r.status_code}: {r.text[:200]}")

    data = r.json()
    if "results" not in data or not data["results"]:
        print(f"DEBUG: URL utilizada: {url}")
        raise Exception(f"No se encontraron datos para {stock} en el rango {fecha_inicio} a {fecha_fin}. Respuesta: {data}")

    df = pd.DataFrame(data["results"]).rename(
        columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"}
    )

    df["datetime"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    return df[["datetime","open","high","low","close","volume"]].copy()

def convertir_a_local_y_filtrar(df, utc_offset=3, market_open="11:30", market_close="18:00"):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["datetime"] = df["datetime"] - pd.Timedelta(hours=utc_offset)
    df["datetime"] = df["datetime"].dt.tz_localize(None)
    df = df.set_index("datetime").sort_index()
    return df.between_time(market_open, market_close).copy()
