import os
import sys
import datetime
import pandas as pd

# Añadir el directorio actual al path para importar desde src
sys.path.append(os.getcwd())

from src.models import SessionLocal, init_db, StockList, RSI_1D
from src.core.polygon_client import obtener_velas_polygon
from src.core.indicators import procesar_indicadores, promedio_variacion_3m
from src import config
from src.config import LIMITE_RSI_1D, TIMEZONE_UTC

def recalculate_rsi_1d_stats(entry, df_1d_proc):
    """
    Recalcula min_price y candles_since_min basado en entry_date.
    Lógica extraída de src/main.py
    """
    df = df_1d_proc.copy()
    if "datetime" in df.columns:
        df = df.set_index("datetime")
    
    entry_date = entry.entry_date
    # Filtrar datos desde la fecha de entrada
    df_hist = df[df.index.date >= entry_date.date()]
    
    if not df_hist.empty:
        min_row = df_hist.loc[df_hist['close'].idxmin()]
        min_val = float(min_row['close'])
        min_date = min_row.name
        
        # Contar velas desde el mínimo hasta el final
        candles_count = len(df_hist.loc[min_date:]) - 1
        if candles_count < 0: candles_count = 0
        
        entry.min_price = min_val
        entry.candles_since_min = int(candles_count)
        
        # También recalculamos el promedio_variacion_3m y valor_actual
        entry.promedio_variacion_3m = float(round(promedio_variacion_3m(df_1d_proc), 2))
        entry.valor_actual = float(round(df_1d_proc["close"].iloc[-1], 2))

def run_scan():
    init_db()
    db = SessionLocal()
    
    try:
        stocks = db.query(StockList).all()
        total_stocks = len(stocks)
        
        print(f"[{datetime.datetime.now()}] Inicio ejecución | Total a procesar: {total_stocks}")
        
        if not stocks:
            if config.PRINT_OUTPUT:
                print("No hay stocks en la lista para escanear.")
            print(f"[{datetime.datetime.now()}] Finalización ejecución")
            return
            
        processed_count = 0
        rsi_hits = 0
        
        for stock in stocks:
            symbol = stock.symbol.strip().upper()
            try:
                # 1. Obtener data 1D para Variación y RVOL
                df_1d = obtener_velas_polygon(symbol, "1D")
                if df_1d.empty or len(df_1d) < 20: 
                    if config.PRINT_OUTPUT:
                        print(f"Skipping {symbol}: insuficiente data.")
                    continue
                
                df_1d_proc = procesar_indicadores(df_1d)
                
                # Variación 1D (último vs penúltimo)
                last_close = df_1d_proc["close"].iloc[-1]
                prev_close = df_1d_proc["close"].iloc[-2]
                last_var = ((last_close - prev_close) / prev_close) * 100
                
                # RVOLs 1D
                rvol_1 = df_1d_proc["rvol"].iloc[-1]
                rvol_2 = df_1d_proc["rvol"].iloc[-2]
 
                rsi = df_1d_proc["RSI"].iloc[-1]
                prom_var_3m = promedio_variacion_3m(df_1d_proc)
 
                existing_rsi1d = db.query(RSI_1D).filter(RSI_1D.symbol == symbol).first()
 
                if existing_rsi1d:
                    # Ya existe, ACTUALIZAMOS sus campos
                    existing_rsi1d.rsi_value = float(round(rsi, 2))
                    existing_rsi1d.variation = float(round(last_var, 2))
                    existing_rsi1d.rvol_1 = float(round(rvol_1, 2))
                    existing_rsi1d.rvol_2 = float(round(rvol_2, 2))
                    existing_rsi1d.promedio_variacion_3m = float(round(prom_var_3m, 2))
                    existing_rsi1d.valor_actual = float(round(last_close, 2))
                    existing_rsi1d.timestamp = datetime.datetime.utcnow()
                    
                    # Recalculamos estadísticas basadas en su fecha de entrada original
                    recalculate_rsi_1d_stats(existing_rsi1d, df_1d_proc)
                    processed_count += 1
                    if config.PRINT_OUTPUT:
                        print(f"Actualizado: {symbol} (RSI: {rsi:.2f})")
                elif rsi <= LIMITE_RSI_1D:
                    # Nueva entrada
                    new_rsi1d = RSI_1D(
                        symbol=symbol,
                        rsi_value=float(round(rsi, 2)),
                        variation=float(round(last_var, 2)),
                        rvol_1=float(round(rvol_1, 2)),
                        rvol_2=float(round(rvol_2, 2)),
                        promedio_variacion_3m=float(round(prom_var_3m, 2)),
                        valor_actual=float(round(last_close, 2)),
                        entry_date=datetime.datetime.utcnow(),
                        min_price=float(last_close),
                        candles_since_min=0,
                        timestamp=datetime.datetime.utcnow()
                    )
                    db.add(new_rsi1d)
                    rsi_hits += 1
                    processed_count += 1
                    if config.PRINT_OUTPUT:
                        print(f"HURRA! Nuevo hit: {symbol} (RSI: {rsi:.2f})")
                else:
                    processed_count += 1
                    
            except Exception as inner_e:
                print(f"Error procesando {symbol}: {inner_e}")
                continue
        
        db.commit()
        print(f"[{datetime.datetime.now()}] Finalización ejecución")
        if config.PRINT_OUTPUT:
            print(f"Resumen: {processed_count} stocks analizados, {rsi_hits} registros nuevos en RSI_1D (Límite RSI: {LIMITE_RSI_1D})")
        
    except Exception as e:
        db.rollback()
        print(f"Error fatal en el escaneo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_scan()
