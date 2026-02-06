import os
import sys
import datetime
import requests

# Añadir el directorio actual al path para importar desde src
sys.path.append(os.getcwd())

from src.models import SessionLocal, init_db, StockTracking
from src.core.regla_cruce_hma import regla_cruce_hma
from src import config

def send_alert(messages):
    """
    Envía una notificación vía POST con los mensajes detallados.
    """
    if not messages:
        return

    # Usamos la URL HMA_BAJISTA del config
    url = config.HMA_BAJISTA
    if not url.startswith("http"):
        url = "https://" + url

    message_body = "\n".join(messages)
    
    try:
        response = requests.post(
            url,
            data=message_body.encode("utf-8"),
            headers={
                "Title": "HMA Bearish Alert",
                "Priority": "high",
                "Tags": "warning,chart_with_downwards_trend"
            }
        )
        if response.status_code == 200:
            if config.PRINT_OUTPUT:
                print(f"📉 Alertas enviadas (Bearish):\n{message_body}")
        else:
            print(f"⚠️ Alerta enviada pero el servidor respondió {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")

def run_bearish_scan():
    init_db()
    db = SessionLocal()
    
    alerts_to_send = []
    
    try:
        # 1. Obtener todos los stocks que están actualmente en seguimiento (StockTracking)
        tracked_stocks = db.query(StockTracking).all()
        total_tracked = len(tracked_stocks)
        
        print(f"[{datetime.datetime.now()}] Inicio ejecución | Total a procesar: {total_tracked}")
        
        if not tracked_stocks:
            if config.PRINT_OUTPUT:
                print("No hay stocks en seguimiento activo para analizar.")
            print(f"[{datetime.datetime.now()}] Finalización ejecución")
            return
            
        bearish_alerts_count = 0
        
        if config.PRINT_OUTPUT:
            print(f"Monitoreando {total_tracked} activos en seguimiento activo...\n")
        
        for stock in tracked_stocks:
            symbol = stock.symbol.strip().upper()
            try:
                metrics = regla_cruce_hma(symbol)
                if not metrics:
                    continue
                
                # Actualizamos los valores en la DB siempre
                stock.current_price = metrics["current_price"]
                stock.rsi_value = metrics["rsi_value"]
                stock.variation = metrics["variation"]
                stock.rvol_1 = metrics["rvol_1"]
                stock.rvol_2 = metrics["rvol_2"]
                stock.hma_a = metrics["hma_a"]
                stock.hma_b = metrics["hma_b"]
                stock.estado = metrics["estado"]
                stock.timestamp = datetime.datetime.utcnow()
                
                # REGLA: Detectar tendencia bajista (Cruce Bajista)
                if metrics["hma_a"] < metrics["hma_b"]:
                    if config.PRINT_OUTPUT:
                        print(f" [ALERTA BAJISTA] {symbol}: Tendencia negativa detectada.")
                    
                    # Alerta si está habilitada en la base de datos
                    if stock.alert_bajista == 1:
                        alert_message = f"🔴 {symbol}: HMA_A:{metrics['hma_a']}, HMA_B:{metrics['hma_b']}) | Var:{metrics['variation']}%"
                        alerts_to_send.append(alert_message)
                        bearish_alerts_count += 1
                
            except Exception as inner_e:
                print(f"Error monitoreando {symbol}: {inner_e}")
                continue
        
        db.commit()
        
        # Enviar alertas colectivas
        if alerts_to_send:
            send_alert(alerts_to_send)

        print(f"[{datetime.datetime.now()}] Finalización ejecución")
        if config.PRINT_OUTPUT:
            print(f"Resumen: {total_tracked} activos revisados, {bearish_alerts_count} alertas disparadas.")
        
    except Exception as e:
        db.rollback()
        print(f"Error fatal en el monitoreo de caídas: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_bearish_scan()
