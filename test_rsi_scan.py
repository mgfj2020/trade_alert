import os
import pandas as pd
import datetime
from src.core.polygon_client import obtener_velas_polygon, aplicar_utc_local, filtrar_horario_mercado
from src.core.indicators import procesar_indicadores
from src.config import LIMITE_RSI_1D


def regla_cruce_hma(symbol):


        # 1. Obtener data 15min para el precio actual (simulado)
        df_15m = obtener_velas_polygon(symbol, "15min")
        if df_15m.empty:
            print("Error: No se pudo obtener datos 15min.")
            return
        
        last_15m_price = float(df_15m["close"].iloc[-1])
        last_15m_datetime = pd.to_datetime(df_15m["datetime"].iloc[-1])
        today_date = last_15m_datetime.date()

        # 2. Obtener data 1D (histórica)
        df_1d = obtener_velas_polygon(symbol, "1D")
        if df_1d.empty:
            print("Error: No se pudo obtener datos 1D.")
            return

        print(df_1d.tail(1))
        print(df_15m.tail(1))

        # 3. Simular el día actual en el set 1D
        last_1d_row = df_1d.iloc[-1]
        last_1d_date = pd.to_datetime(last_1d_row["datetime"]).date()
        
        if last_1d_date == today_date:
            print(f"Actualizando vela 1D de hoy ({today_date}) con el precio actual {last_15m_price}")
            df_1d.loc[df_1d.index[-1], "close"] = last_15m_price

        else:
            print(f"Agregando nueva vela simulada para hoy ({today_date}) con precio {last_15m_price}")
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
        
        # 3. Extraer métricas (última vela)
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
        
        # Mostrar resultados
        print(f"\nResultados para {symbol}:")
        print(f"  Precio Actual:  {last_close:.2f}")
        print(f"  RSI 1D:         {rsi:.2f} {'(HIT!)' if rsi <= LIMITE_RSI_1D else ''}")
        print(f"  Variación:      {variation:.2f}%")
        print(f"  RVOL 1 (Hoy):   {rvol_1:.2f}")
        print(f"  RVOL 2 (Ayer):  {rvol_2:.2f}")
        print(f"  HMA_A:          {hma_a:.2f}")
        print(f"  HMA_B:          {hma_b:.2f}")
        print(f"  Límite RSI:     {LIMITE_RSI_1D}")
        print(f"  Estado:         {estado}")
        
    

def test_rsi_tsla():

    symbol = "ONDS"
    print(f"--- Iniciando cálculo de RSI 1D para {symbol} ---")
    
    
    try:
        regla_cruce_hma(symbol)

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    test_rsi_tsla()
