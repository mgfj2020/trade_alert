import requests
import datetime
from src.models import SessionLocal, StockTracking
from src.core.regla_cruce_hma import regla_cruce_hma
from src import config

def evaluate_tracking_rules():
    """
    Consulta la tabla stock_tracking, actualiza métricas HMA y valida cambios de estado.
    """
    db = SessionLocal()
    alertas_mensajes = []
    try:
        tracked_list = db.query(StockTracking).all()
        print(f"Analizando {len(tracked_list)} stocks en seguimiento (HMA)...")
        
        for stock in tracked_list:
            try:
                old_estado = stock.estado
                metrics = regla_cruce_hma(stock.symbol)
                
                if metrics:
                    # Actualizar campos
                    stock.current_price = metrics["current_price"]
                    stock.rsi_value = metrics["rsi_value"]
                    stock.variation = metrics["variation"]
                    stock.rvol_1 = metrics["rvol_1"]
                    stock.rvol_2 = metrics["rvol_2"]
                    stock.hma_a = metrics["hma_a"]
                    stock.hma_b = metrics["hma_b"]
                    stock.estado = metrics["estado"]
                    stock.timestamp = datetime.datetime.utcnow()
                    
                    new_estado = metrics["estado"]
                    
                    # Alertar si el estado es Cruce Alcista
                    if new_estado == "cruce_alcista":
                        msg = f"{stock.symbol} ({stock.current_price})"
                        alertas_mensajes.append(msg)
                        print(f"  [!] {msg}")
                    else:
                        print(f"  [-] {stock.symbol}: {new_estado}")

            except Exception as e:
                print(f"❌ Error evaluando HMA para {stock.symbol}: {e}")
        
        db.commit()
    finally:
        db.close()
    return alertas_mensajes

def send_tracking_alert(messages):
    """
    Envía una notificación vía POST con los mensajes detallados.
    """
    if not messages:
        return

    message_body = "\n".join(messages)
    
    try:
        response = requests.post(
            config.HMA_ALERT,
            data=message_body.encode("utf-8"),
            headers={
                "Title": "HMA Tracking Alert",
                "Priority": "high",
                "Tags": "chart_with_upwards_trend,rocket"
            }
        )
        if response.status_code == 200:
            print(f"🚀 Alertas tracking enviadas:\n{message_body}")
        else:
            print(f"⚠️ Alerta enviada pero el servidor respondió {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error enviando alerta tracking: {e}")

def run_tracking_process(label="validación de tracking HMA"):
    """
    Encapsula el flujo completo de evaluación y envío de alertas de tracking.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).replace(tzinfo=None)
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"[{now_str}] Ejecutando {label}...")
    alertas = evaluate_tracking_rules()
    
    if alertas:
        send_tracking_alert(alertas)
    else:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_str = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now_str}] ✅ No se detectaron cruces alcistas en HMA.")
