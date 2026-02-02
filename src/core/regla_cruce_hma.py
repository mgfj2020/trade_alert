import pandas as pd
from src.core.polygon_client import obtener_velas_polygon
from src.core.indicators import procesar_indicadores
from src.config import LIMITE_RSI_1D

def regla_cruce_hma(symbol):
    # 1. Obtener data 15min para el precio actual (simulado o tiempo real)
    df_15m = obtener_velas_polygon(symbol, "15min")
    if df_15m.empty:
        # print("Error: No se pudo obtener datos 15min.")
        return None
    
    last_15m_price = float(df_15m["close"].iloc[-1])
    last_15m_datetime = pd.to_datetime(df_15m["datetime"].iloc[-1])
    today_date = last_15m_datetime.date()

    # 2. Obtener data 1D (histórica)
    df_1d = obtener_velas_polygon(symbol, "1D")
    if df_1d.empty:
        # print("Error: No se pudo obtener datos 1D.")
        return None

    # print(df_1d.tail(1))
    # print(df_15m.tail(1))

    # 3. Simular el día actual en el set 1D
    last_1d_row = df_1d.iloc[-1]
    last_1d_date = pd.to_datetime(last_1d_row["datetime"]).date()
    
    if last_1d_date == today_date:
        # print(f"Actualizando vela 1D de hoy ({today_date}) con el precio actual {last_15m_price}")
        df_1d.loc[df_1d.index[-1], "close"] = last_15m_price
    else:
        # print(f"Agregando nueva vela simulada para hoy ({today_date}) con precio {last_15m_price}")
        # Creamos una nueva fila basada en la última conocida
        new_row = {
            "datetime": last_15m_datetime,
            "open": last_15m_price,
            "high": last_15m_price,
            "low": last_15m_price,
            "close": last_15m_price,
            "volume": 0 # Volumen simplificado
        }
        df_1d = pd.concat([df_1d, pd.DataFrame([new_row])], ignore_index=True)

    # 4. Procesar indicadores sobre el dataset aumentado
    df_proc = procesar_indicadores(df_1d)
    
    # 5. Extraer métricas (última vela)
    if len(df_proc) < 2:
        return None
        
    last_row = df_proc.iloc[-1]
    prev_row = df_proc.iloc[-2]
    
    rsi = last_row["RSI"]
    last_close = last_row["close"]
    prev_close = prev_row["close"]
    variation = ((last_close - prev_close) / prev_close) * 100
    
    rvol_1 = last_row["rvol"]
    rvol_2 = prev_row["rvol"]
    
    hma_a = last_row["hma_a"]
    hma_b = last_row["hma_b"]

    if hma_a >= hma_b:
        estado = "cruce_alcista"
    else:
        estado = "cruce_bajista"
    
    return {
        "symbol": symbol,
        "current_price": float(round(last_close, 2)),
        "rsi_value": float(round(rsi, 2)),
        "variation": float(round(variation, 2)),
        "rvol_1": float(round(rvol_1, 2)),
        "rvol_2": float(round(rvol_2, 2)),
        "hma_a": float(round(hma_a, 2)),
        "hma_b": float(round(hma_b, 2)),
        "estado": estado
    }
