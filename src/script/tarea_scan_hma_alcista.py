import os
import sys
import datetime
import requests

# Añadir el directorio actual al path para importar desde src
sys.path.append(os.getcwd())

from src import config
from src.models import SessionLocal, init_db, StockTracking, RSI_1D
from src.core.regla_cruce_hma import regla_cruce_hma
from src.config import LIMITE_RSI_1D

def send_alert(messages):
    """
    Envía una notificación vía POST con los mensajes detallados.
    """
    if not messages:
        return

    # Usamos la URL HMA_ALCISTA del config ya que este es el script alcista
    # Si no tiene el protocolo, se lo agregamos
    url = config.HMA_ALCISTA
    if not url.startswith("http"):
        url = "https://" + url

    message_body = "\n".join(messages)
    
    try:
        response = requests.post(
            url,
            data=message_body.encode("utf-8"),
            headers={
                "Title": "HMA Bullish Alert",
                "Priority": "high",
                "Tags": "rocket,chart_with_upwards_trend"
            }
        )
        if response.status_code == 200:
            if config.PRINT_OUTPUT:
                print(f"🚀 Alertas enviadas (Bullish):\n{message_body}")
        else:
            print(f"⚠️ Alerta enviada pero el servidor respondió {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")

def run_hma_scan():
    init_db()
    db = SessionLocal()
    
    alerts_to_send = []
    
    try:
        # 1. Obtener todos los stocks de la tabla RSI_1D
        rsi_stocks = db.query(RSI_1D).all()
        total_rsi_stocks = len(rsi_stocks)
        
        print(f"[{datetime.datetime.now()}] Inicio ejecución | Total a procesar: {total_rsi_stocks}")
        
        if not rsi_stocks:
            if config.PRINT_OUTPUT:
                print("No hay stocks en RSI_1D para analizar.")
            print(f"[{datetime.datetime.now()}] Finalización ejecución")
            return
            
        updated_count = 0
        added_count = 0
        
        if config.PRINT_OUTPUT:
            print(f"Analizando {total_rsi_stocks} candidatos de la tabla RSI_1D...\n")
        
        for rsi_stock in rsi_stocks:
            symbol = rsi_stock.symbol.strip().upper()
            try:
                metrics = regla_cruce_hma(symbol)
                if not metrics:
                    continue
                
                # REGLA: Solo guardamos/actualizamos si HMA_A >= HMA_B (Cruce Alcista)
                if metrics["hma_a"] >= metrics["hma_b"]:
                    # Buscar si ya existe en stock_tracking
                    track_entry = db.query(StockTracking).filter(StockTracking.symbol == symbol).first()
                    
                    alert_message = f"🟢 {symbol}: HMA_A: {metrics['hma_a']} >= HMA_B: {metrics['hma_b']}"
                    
                    if track_entry:
                        # Actualizar registro existente
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
                        if config.PRINT_OUTPUT:
                            print(f" [ACTUALIZADO] {symbol}: Cruce alcista detectado.")
                        
                        # Alerta si está habilitada
                        if track_entry.alert_alcista == 1:
                            alerts_to_send.append(alert_message)
                    else:
                        # Crear nuevo registro en stock_tracking
                        new_track = StockTracking(
                            symbol=symbol,
                            current_price=metrics["current_price"],
                            rsi_value=metrics["rsi_value"],
                            variation=metrics["variation"],
                            rvol_1=metrics["rvol_1"],
                            rvol_2=metrics["rvol_2"],
                            hma_a=metrics["hma_a"],
                            hma_b=metrics["hma_b"],
                            rsi_limit=LIMITE_RSI_1D,
                            estado=metrics["estado"],
                            alert_alcista=1, # Default activado
                            alert_bajista=1
                        )
                        db.add(new_track)
                        added_count += 1
                        if config.PRINT_OUTPUT:
                            print(f" [NUEVO TRACK] {symbol}: Agregado a seguimiento.")
                        
                        # Alertas para nuevos registros están habilitadas por defecto (alert_alcista=1)
                        alerts_to_send.append(alert_message)
                else:
                    # Opcional: Podrías imprimir los que no cruzan para debug
                    # print(f" [ESPERANDO] {symbol}: Aún en tendencia bajista (HMA_A < HMA_B)")
                    pass
                
            except Exception as inner_e:
                print(f"Error procesando {symbol}: {inner_e}")
                continue
        
        db.commit()
        
        # Enviar alertas colectivas
        if alerts_to_send:
            send_alert(alerts_to_send)

        print(f"[{datetime.datetime.now()}] Finalización ejecución")
        if config.PRINT_OUTPUT:
            print(f"Resumen: {added_count} nuevos en seguimiento activo, {updated_count} actualizados.")
        
    except Exception as e:
        db.rollback()
        print(f"Error fatal en el proceso HMA: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_hma_scan()
