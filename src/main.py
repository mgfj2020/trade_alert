import os
import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.models import SessionLocal, init_db, StockList, RSI_4H, RSI_1D, StockTracking, Favorite
from src.core.polygon_client import obtener_velas_polygon
from src.core.indicators import calcular_rsi, procesar_indicadores, promedio_variacion_3m
from src.core.regla_cruce_hma import regla_cruce_hma
from src.config import LIMITE_RSI_1D, TIMEZONE_UTC, API_KEY
from src import config
import datetime
from contextlib import asynccontextmanager
from sqlalchemy import func
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos
    init_db()
    
    yield

app = FastAPI(lifespan=lifespan)

# Usar la raíz como directorio de los HTML solicitados
templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favoritos", response_class=HTMLResponse)
async def read_favoritos(request: Request):
    return templates.TemplateResponse("favoritos.html", {"request": request})

@app.get("/track", response_class=HTMLResponse)
async def read_track(request: Request):
    return templates.TemplateResponse("track.html", {"request": request})

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Normalizar nombres de columnas a minúsculas para facilitar búsqueda
        df.columns = [c.lower() for c in df.columns]
        
        # Determinar la columna de símbolo (puede ser 'symbol' o 'stock')
        symbol_col = next((c for c in df.columns if c in ['symbol', 'stock']), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="El CSV debe contener una columna 'symbol' o 'stock'")
        
        db = SessionLocal()
        new_symbols_count = 0
        try:
            # Eliminar duplicados en el CSV y valores nulos
            symbols = df[symbol_col].dropna().unique()
            
            for symbol in symbols:
                symbol = str(symbol).strip().upper()
                if not symbol:
                    continue
                # Verificar si ya existe
                exists = db.query(StockList).filter(StockList.symbol == symbol).first()
                if not exists:
                    db.add(StockList(symbol=symbol))
                    new_symbols_count += 1
            db.commit()
            return {"message": f"Se procesaron los símbolos. {new_symbols_count} nuevos agregados."}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en base de datos: {str(e)}")
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando el archivo: {str(e)}")

@app.post("/scan-rsi")
async def scan_rsi():
    db = SessionLocal()
    try:
        stocks = db.query(StockList).all()
        if not stocks:
            return {"message": "No hay stocks en la lista para escanear."}
            
        processed_count = 0
        rsi_hits = 0
        
        for stock in stocks:
            try:
                # 1. Obtener data 1D para Variación y RVOL
                df_1d = obtener_velas_polygon(stock.symbol, "1D")
                if df_1d.empty or len(df_1d) < 20: 
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

                clean_symbol = stock.symbol.strip().upper()
                existing_rsi1d = db.query(RSI_1D).filter(RSI_1D.symbol == clean_symbol).first()

                if existing_rsi1d:
                    # Ya existe, ACTUALIZAMOS sus campos (independiente del RSI actual)
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
                elif rsi <= LIMITE_RSI_1D:
                    # Nueva entrada (solo si rompe el límite)
                    new_rsi1d = RSI_1D(
                        symbol=clean_symbol,
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
            except Exception as inner_e:
                print(f"Error procesando {stock.symbol}: {inner_e}")
                continue
        
        db.commit()
        return {
            "message": f"Escaneo completado. {processed_count} stocks analizados, {rsi_hits} registros nuevos en RSI_1D (RSI <= {LIMITE_RSI_1D})"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en el escaneo: {str(e)}")
    finally:
        db.close()

@app.get("/api/data")
async def get_results():
    db = SessionLocal()
    try:
        results = db.query(RSI_1D).order_by(RSI_1D.timestamp.desc()).limit(100).all()
        # [symbol, rvol1, rvol2, var, rsi, hma10, hma20, min_price, candles, date]
        return [
            [
                r.symbol, 
                r.rvol_1, 
                r.rvol_2, 
                r.variation, 
                r.rsi_value, 
                r.promedio_variacion_3m,
                r.valor_actual,
                r.min_price,
                r.candles_since_min,
                (r.entry_date + datetime.timedelta(hours=TIMEZONE_UTC)).strftime("%Y-%m-%d"),
                (r.timestamp + datetime.timedelta(hours=TIMEZONE_UTC)).strftime("%Y-%m-%d %H:%M")
            ] 
            for r in results
        ]
    finally:
        db.close()

@app.post("/api/add_track")
async def add_to_track(symbols: list[str]):
    db = SessionLocal()
    try:
        from src.config import LIMITE_RSI_1D
        for symbol in symbols:
            source = db.query(RSI_1D).filter(RSI_1D.symbol == symbol).first()
            if not source: continue
            exists = db.query(StockTracking).filter(StockTracking.symbol == symbol).first()
            if not exists:
                db.add(StockTracking(
                    symbol=source.symbol, 
                    current_price=source.min_price, # Usamos el precio que disparó como inicial
                    rsi_value=source.rsi_value, 
                    variation=source.variation,
                    rvol_1=source.rvol_1, 
                    rvol_2=source.rvol_2, 
                    hma_a=0.0, # RSI_1D ya no tiene HMA, pondremos 0 o podríamos recalcular si fuera crítico
                    hma_b=0.0,
                    rsi_limit=LIMITE_RSI_1D,
                    estado=None
                ))
        db.commit()
        return {"message": "Símbolos agregados a Track Stock"}
    finally:
        db.close()

@app.post("/api/add_favoritos")
async def add_to_favorites(symbols: list[str]):
    db = SessionLocal()
    try:
        for symbol in symbols:
            exists = db.query(Favorite).filter(Favorite.symbol == symbol).first()
            if not exists:
                db.add(Favorite(symbol=symbol))
        db.commit()
        return {"message": "Símbolos agregados a Favoritos"}
    finally:
        db.close()

@app.get("/api/track_data")
async def get_track_data():
    db = SessionLocal()
    try:
        favs = db.query(StockTracking).all()
        # Orden: symbol, current_price, rsi_value, variation, rvol_1, rvol_2, hma_a, hma_b, alert_alcista, alert_bajista, estado
        return [
            [
                f.symbol, 
                f.current_price,
                f.rsi_value, 
                f.variation, 
                f.rvol_1, 
                f.rvol_2, 
                f.hma_a, 
                f.hma_b, 
                f.alert_alcista,
                f.alert_bajista,
                f.estado
            ] for f in favs
        ]
    finally:
        db.close()

@app.get("/api/favoritos_data")
async def get_favorites():
    db = SessionLocal()
    try:
        favs = db.query(Favorite).all()
        # [symbol, current_value, alert_value, alert_direction, timestamp]
        return [
            [
                f.symbol, 
                f.current_value, 
                f.alert_value, 
                f.alert_direction,
                (f.timestamp + datetime.timedelta(hours=TIMEZONE_UTC)).strftime("%Y-%m-%d %H:%M") if f.timestamp else "-"
            ] 
            for f in favs
        ]
    finally:
        db.close()

@app.post("/api/refresh_favorites")
async def refresh_favorites():
    db = SessionLocal()
    try:
        favs = db.query(Favorite).all()
        updated_count = 0
        for fav in favs:
            try:
                df = obtener_velas_polygon(fav.symbol, "1D")
                if not df.empty:
                    fav.current_value = float(df["close"].iloc[-1])
                    updated_count += 1
            except Exception as e:
                print(f"Error actualizando {fav.symbol}: {e}")
                continue
        db.commit()
        return {"message": f"Precios actualizados para {updated_count} símbolos"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/add_manual_favorite")
async def add_manual_favorite(data: dict):
    # data: { "symbol": "TSLA", "alert_value": 130.44, "direction": "encima" }
    db = SessionLocal()
    try:
        symbol = data["symbol"].strip().upper()
        # Obtener precio actual de Polygon 1D
        df = obtener_velas_polygon(symbol, "1D")
        current_price = 0.0
        if not df.empty:
            current_price = float(df["close"].iloc[-1])
            
        exists = db.query(Favorite).filter(Favorite.symbol == symbol).first()
        if exists:
            exists.current_value = current_price
            exists.alert_value = float(data["alert_value"])
            exists.alert_direction = data["direction"]
        else:
            db.add(Favorite(
                symbol=symbol,
                current_value=current_price,
                alert_value=float(data["alert_value"]),
                alert_direction=data["direction"]
            ))
        db.commit()
        return {"message": f"{symbol} agregado/actualizado manualmente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/update_favorite_values")
async def update_favorite_values(data: dict):
    # data: { "symbol": "AAPL", "current_value": 150.0, "alert_value": 140.0, "alert_direction": "debajo" }
    db = SessionLocal()
    try:
        fav = db.query(Favorite).filter(Favorite.symbol == data["symbol"]).first()
        if fav:
            fav.current_value = float(data["current_value"])
            fav.alert_value = float(data["alert_value"])
            fav.alert_direction = data["alert_direction"]
            db.commit()
            return {"message": "Actualizado"}
        raise HTTPException(status_code=404, detail="No encontrado")
    finally:
        db.close()

@app.post("/api/add_manual_track")
async def add_manual_track(data: dict):
    # data: { "symbol": "TSLA" }
    db = SessionLocal()
    try:
        symbol = data["symbol"].strip().upper()
        if not symbol:
            raise HTTPException(status_code=400, detail="Símbolo inválido")
            
        metrics = regla_cruce_hma(symbol)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"No se pudo obtener datos para {symbol}")
            
        exists = db.query(StockTracking).filter(StockTracking.symbol == symbol).first()
        if exists:
            exists.current_price = metrics["current_price"]
            exists.rsi_value = metrics["rsi_value"]
            exists.variation = metrics["variation"]
            exists.rvol_1 = metrics["rvol_1"]
            exists.rvol_2 = metrics["rvol_2"]
            exists.hma_a = metrics["hma_a"]
            exists.hma_b = metrics["hma_b"]
            exists.estado = metrics["estado"]
            exists.timestamp = datetime.datetime.utcnow()
        else:
            db.add(StockTracking(
                symbol=symbol,
                current_price=metrics["current_price"],
                rsi_value=metrics["rsi_value"],
                variation=metrics["variation"],
                rvol_1=metrics["rvol_1"],
                rvol_2=metrics["rvol_2"],
                hma_a=metrics["hma_a"],
                hma_b=metrics["hma_b"],
                rsi_limit=LIMITE_RSI_1D,
                estado=metrics["estado"]
            ))
        db.commit()
        return {"message": f"{symbol} agregado/actualizado en seguimiento"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/track_values")
async def update_track_values(data: dict):
    db = SessionLocal()
    try:
        fav = db.query(StockTracking).filter(StockTracking.symbol == data["symbol"]).first()
        if fav:
            if "current_price" in data:
                fav.current_price = float(data["current_price"])
            if "estado" in data:
                fav.estado = data["estado"]
            db.commit()
            return {"message": "Actualizado"}
        raise HTTPException(status_code=404, detail="No encontrado")
    finally:
        db.close()

@app.post("/api/track/toggle_alert")
async def toggle_alert(data: dict):
    # data: { "symbol": "AAPL", "field": "alert_alcista", "value": true }
    db = SessionLocal()
    try:
        stock = db.query(StockTracking).filter(StockTracking.symbol == data["symbol"]).first()
        if not stock:
            raise HTTPException(status_code=404, detail="Stock no encontrado en seguimiento")
        
        field = data["field"]
        value = 1 if data["value"] else 0
        
        if field == "alert_alcista":
            stock.alert_alcista = value
        elif field == "alert_bajista":
            stock.alert_bajista = value
        else:
            raise HTTPException(status_code=400, detail="Campo inválido")
            
        db.commit()
        return {"message": f"Alerta {field} actualizada para {data['symbol']}"}
    finally:
        db.close()

@app.post("/api/recalculate_hma")
async def recalculate_hma():
    db = SessionLocal()
    try:
        # 1. Obtener todos los stocks de la tabla RSI_1D
        rsi_stocks = db.query(RSI_1D).all()
        if not rsi_stocks:
            return {"message": "No hay stocks en RSI_1D para analizar."}
            
        updated_count = 0
        added_count = 0
        
        for rsi_stock in rsi_stocks:
            symbol = rsi_stock.symbol
            try:
                metrics = regla_cruce_hma(symbol)
                if not metrics:
                    continue
                
                # REGLA: Solo guardamos/actualizamos si HMA_A >= HMA_B
                if metrics["hma_a"] >= metrics["hma_b"]:
                    # Buscar si ya existe en stock_tracking
                    track_entry = db.query(StockTracking).filter(StockTracking.symbol == symbol).first()
                    
                    if track_entry:
                        # Actualizar existente
                        track_entry.current_price = metrics["current_price"]
                        track_entry.rsi_value = metrics["rsi_value"]
                        track_entry.variation = metrics["variation"]
                        track_entry.rvol_1 = metrics["rvol_1"]
                        track_entry.rvol_2 = metrics["rvol_2"]
                        track_entry.hma_a = metrics["hma_a"]
                        track_entry.hma_b = metrics["hma_b"]
                        track_entry.estado = metrics["estado"]
                        track_entry.timestamp = datetime.datetime.utcnow()
                        updated_count += 1
                    else:
                        # Crear nuevo registro en stock_tracking
                        db.add(StockTracking(
                            symbol=symbol,
                            current_price=metrics["current_price"],
                            rsi_value=metrics["rsi_value"],
                            variation=metrics["variation"],
                            rvol_1=metrics["rvol_1"],
                            rvol_2=metrics["rvol_2"],
                            hma_a=metrics["hma_a"],
                            hma_b=metrics["hma_b"],
                            rsi_limit=LIMITE_RSI_1D, # Usamos el límite global
                            estado=metrics["estado"]
                        ))
                        added_count += 1
                
            except Exception as e:
                print(f"Error recalculando HMA para {symbol}: {e}")
                continue
        
        db.commit()
        return {"message": f"Proceso HMA completado. {added_count} nuevos en seguimiento, {updated_count} actualizados."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error recalculando HMA: {str(e)}")
    finally:
        db.close()

@app.delete("/api/favoritos/{symbol}")
async def delete_favorite(symbol: str):
    db = SessionLocal()
    try:
        fav = db.query(Favorite).filter(Favorite.symbol == symbol).first()
        if fav:
            db.delete(fav)
            db.commit()
            return {"message": "Eliminado de Favoritos"}
        raise HTTPException(status_code=404, detail="No encontrado")
    finally:
        db.close()

@app.delete("/api/track/{symbol}")
async def delete_track(symbol: str):
    db = SessionLocal()
    try:
        fav = db.query(StockTracking).filter(StockTracking.symbol == symbol).first()
        if fav:
            db.delete(fav)
            db.commit()
            return {"message": "Eliminado de Track Stock"}
        raise HTTPException(status_code=404, detail="No encontrado")
    finally:
        db.close()

@app.delete("/api/rsi_1d/{symbol}")
async def delete_rsi_1d(symbol: str):
    db = SessionLocal()
    try:
        entry = db.query(RSI_1D).filter(RSI_1D.symbol == symbol.upper()).first()
        if entry:
            db.delete(entry)
            db.commit()
            return {"message": f"{symbol} eliminado de RSI_1D"}
        raise HTTPException(status_code=404, detail="Símbolo no encontrado")
    finally:
        db.close()

@app.post("/api/rsi_1d/update_date")
async def update_rsi_1d_date(data: dict):
    # data: { "symbol": "AAPL", "new_date": "2023-10-27" }
    db = SessionLocal()
    try:
        symbol = data["symbol"].upper()
        new_date_str = data["new_date"]
        new_date = datetime.datetime.strptime(new_date_str, "%Y-%m-%d")
        
        entry = db.query(RSI_1D).filter(RSI_1D.symbol == symbol).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Símbolo no encontrado")
        
        entry.entry_date = new_date
        
        # Obtener data 1D para recálculo
        df_1d = obtener_velas_polygon(symbol, "1D")
        if not df_1d.empty:
            df_1d_proc = procesar_indicadores(df_1d)
            recalculate_rsi_1d_stats(entry, df_1d_proc)
        
        db.commit()
        return {"message": f"Fecha actualizada para {symbol} y estadísticas recalculadas"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usar YYYY-MM-DD")
    finally:
        db.close()

def recalculate_rsi_1d_stats(entry, df_1d_proc):
    """
    Recalcula min_price y candles_since_min basado en entry_date.
    """
    # Aseguramos que trabajamos con DatetimeIndex para poder usar .index.date
    df = df_1d_proc.copy()
    if "datetime" in df.columns:
        df = df.set_index("datetime")
    
    entry_date = entry.entry_date
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

@app.get("/api/config")
async def get_config():
    from src.config import HMA_A, HMA_B
    return {"HMA_A": HMA_A, "HMA_B": HMA_B}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
