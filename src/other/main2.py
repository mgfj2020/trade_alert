import os
import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.models import SessionLocal, init_db, StockList, RSI_4H, Favorite
from src.core.polygon_client import obtener_velas_polygon
from src.core.indicators import calcular_rsi, procesar_indicadores
from src.config import TIMEZONE_UTC
from src import config
import datetime
from contextlib import asynccontextmanager
from src.alert_scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos
    init_db()
    # Iniciar el scheduler de alertas
    scheduler = start_scheduler()
    yield
    # Apagar el scheduler al cerrar la app
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Usar la raíz como directorio de los HTML solicitados
templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favoritos", response_class=HTMLResponse)
async def read_favoritos(request: Request):
    return templates.TemplateResponse("favoritos.html", {"request": request})

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Normalizar nombres de columnas a minúsculas para facilitar búsqueda
        df.columns = [c.lower() for c in df.columns]
        
        if 'symbol' not in df.columns:
            raise HTTPException(status_code=400, detail="El CSV debe contener una columna 'symbol'")
        
        db = SessionLocal()
        new_symbols_count = 0
        try:
            # Eliminar duplicados en el CSV y valores nulos
            symbols = df['symbol'].dropna().unique()
            
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
        results = db.query(RSI_4H).order_by(RSI_4H.timestamp.desc()).limit(100).all()
        # Formato esperado por index.html: [symbol, var, rsi, date, rvol1, rvol2]
        # Ajustamos el retorno para incluir los RVOLs
        return [
            [
                r.symbol, 
                r.rvol_1, 
                r.rvol_2, 
                r.variation, 
                r.rsi_value, 
                (r.timestamp + datetime.timedelta(hours=TIMEZONE_UTC)).strftime("%Y-%m-%d %H:%M")
            ] 
            for r in results
        ]
    finally:
        db.close()

@app.post("/api/add_favoritos")
async def add_to_favorites(symbols: list[str]):
    db = SessionLocal()
    try:
        for symbol in symbols:
            # Evitar duplicados
            exists = db.query(Favorite).filter(Favorite.symbol == symbol).first()
            if not exists:
                db.add(Favorite(symbol=symbol))
        db.commit()
        return {"message": "Símbolos agregados a favoritos"}
    finally:
        db.close()

@app.get("/api/favoritos_data")
async def get_favorites():
    db = SessionLocal()
    try:
        favs = db.query(Favorite).all()
        # [symbol, current_value, alert_value, alert_direction]
        return [[f.symbol, f.current_value, f.alert_value, f.alert_direction] for f in favs]
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

@app.delete("/api/favoritos/{symbol}")
async def delete_favorite(symbol: str):
    db = SessionLocal()
    try:
        fav = db.query(Favorite).filter(Favorite.symbol == symbol).first()
        if fav:
            db.delete(fav)
            db.commit()
            return {"message": "Eliminado"}
        raise HTTPException(status_code=404, detail="No encontrado")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
