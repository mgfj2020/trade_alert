import pandas as pd
import numpy as np
import math

def calcular_rsi(df, periodos=14):
    delta = df['close'].diff()
    ganancia = (delta.where(delta > 0, 0))
    perdida = (-delta.where(delta < 0, 0))
    avg_ganancia = ganancia.ewm(alpha=1/periodos, adjust=True).mean()
    avg_perdida = perdida.ewm(alpha=1/periodos, adjust=True).mean()
    rs = avg_ganancia / avg_perdida
    return 100 - (100 / (1 + rs))

def hma(series, length):
    def wma(s, l):
        l = int(l)
        weights = np.arange(1, l + 1)
        return s.rolling(l).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    
    half_length = int(length / 2)
    sqrt_length = int(math.floor(math.sqrt(length)))
    diff = 2 * wma(series, half_length) - wma(series, length)
    return wma(diff, sqrt_length)

def procesar_indicadores(df, rvol_periodos=60):
    df = df.copy()
    cols = ["open","high","low","close","volume"]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")

    # RSI + EMAs
    df["RSI"] = calcular_rsi(df)
    df["RSI_EMA_5"] = df["RSI"].ewm(span=5, adjust=False).mean()
    df["RSI_EMA_14"] = df["RSI"].ewm(span=14, adjust=False).mean()

    # HMAs
    df["hma5"] = hma(df["close"], 5)
    df["hma9"] = hma(df["close"], 9)
    df["hma90"] = hma(df["close"], 90)

    # RVOL
    vol = df["volume"].astype(float)
    vol_prom = vol.rolling(window=rvol_periodos, min_periods=1).mean()
    df["rvol"] = vol / vol_prom

    # Variación
    df["var"] = df["close"].pct_change(fill_method=None) * 100
    return df

def verificar_estado_rsi(df, limite_bajo=35, limite_techo=45, ventana=15):
    """
    Detecta candidatos basándose en el nivel de RSI, 
    sin importar si aún está bajando.
    """
    if len(df) < ventana:
        return "insuficiente_datos", {}

    serie_ventana = df['RSI'].iloc[-ventana:]
    rsi_actual = serie_ventana.iloc[-1]
    rsi_anterior = serie_ventana.iloc[-2]
    rsi_min_ventana = serie_ventana.min()
    
    esta_girando = rsi_actual > rsi_anterior
    
    if 35 <= rsi_actual <= limite_techo and rsi_min_ventana < limite_bajo:
        estado = "CUMPLE REQUISITO (Confirmado)"
    elif rsi_actual < limite_bajo:
        if esta_girando:
            estado = "CANDIDATA (Giro detectado)"
        else:
            estado = "CANDIDATA (Aún cayendo)"
    else:
        estado = "NO CUMPLE REQUISITO"

    detalles = {
        "rsi_actual": round(rsi_actual, 2),
        "rsi_anterior": round(rsi_anterior, 2),
        "rsi_min_ventana": round(rsi_min_ventana, 2),
        "tendencia": "Subiendo ↑" if esta_girando else "Bajando ↓"
    }
    
    return estado, detalles

def promedio_variacion_3m(df, meses=3):
    var = df[['var']].dropna()
    fecha_fin = var.index.max()
    fecha_inicio = fecha_fin - pd.DateOffset(months=meses)
    var_3m = var.loc[fecha_inicio:fecha_fin]
    return var_3m['var'].abs().mean()

def rvol_time_and_cumulative(df, timeframe_minutes=30, lookback_bars=5, rvol_threshold=1.0):
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("El DataFrame debe tener DatetimeIndex")

    df["hour"] = df.index.hour
    df["minute_block"] = (df.index.minute // timeframe_minutes) * timeframe_minutes
    df["time_slot"] = df["hour"].astype(str) + ":" + df["minute_block"].astype(str).str.zfill(2)

    df["avg_vol_same_slot"] = (
        df.groupby("time_slot")["volume"]
          .transform(lambda x: x.shift(1).rolling(lookback_bars, min_periods=1).mean())
    )
    df["rvol_candle"] = df["volume"] / df["avg_vol_same_slot"]

    df["rvol_candle_2bar_avg"] = (
        df.groupby("time_slot")["rvol_candle"]
          .transform(lambda x: x.shift(1).rolling(2).mean())
    )

    df["rvol_candle_confirmed"] = (
        (df["rvol_candle"] > rvol_threshold) &
        (df["rvol_candle_2bar_avg"] > rvol_threshold)
    )

    df["date"] = df.index.date
    df["cum_volume_day"] = df.groupby("date")["volume"].cumsum()

    df["avg_cum_volume"] = (
        df.groupby("time_slot")["cum_volume_day"]
          .transform(lambda x: x.shift(1).rolling(lookback_bars, min_periods=1).mean())
    )

    df["rvol_cumulative"] = df["cum_volume_day"] / df["avg_cum_volume"]
    df["rvol_day_confirmed"] = df["rvol_cumulative"] > rvol_threshold
    df["rvol_strong_signal"] = df["rvol_candle_confirmed"] & df["rvol_day_confirmed"]

    return df


def evaluar_estado_hma90(df):
    if len(df) < 2:
        return None, None

    df = df.sort_index()
    if 'hma90' not in df.columns:
        raise KeyError("Falta columna 'hma90'. Usa df_procesado.")

    close = df['close'].astype(float)
    hma90 = df['hma90'].astype(float)

    valid = hma90.notna() & close.notna()
    close = close[valid]
    hma90 = hma90[valid]

    if len(close) < 2:
        return None, None

    diff = close - hma90

    if diff.iloc[-2] <= 0 and diff.iloc[-1] > 0:
        return "Cruce sobre HMA90", 0

    if diff.iloc[-2] >= 0 and diff.iloc[-1] < 0:
        return "Cruce bajo HMA90", 0

    sobre_actual = diff.iloc[-1] > 0
    estado = "Sobre HMA90" if sobre_actual else "Bajo HMA90"

    velas = 0
    for i in range(len(diff) - 1, -1, -1):
        if sobre_actual:
            if diff.iloc[i] > 0:
                velas += 1
            else:
                break
        else:
            if diff.iloc[i] < 0:
                velas += 1
            else:
                break

    return estado, velas