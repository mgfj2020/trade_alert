import requests
import datetime
from src.models import SessionLocal, Favorite
from src.core.polygon_client import obtener_velas_polygon
from src import config

def evaluate_rules():
    """
    Consulta la tabla favorites y valida las condiciones (Precio y Dirección).
    """
    db = SessionLocal()
    alertas_mensajes = []
    try:
        favorites_list = db.query(Favorite).all()
        print(f"Analizando {len(favorites_list)} stocks en favoritos...")
        
        for fav in favorites_list:
            try:
                # Obtener velas diarias para calcular precio actual
                df = obtener_velas_polygon(fav.symbol, "1D")
                if df.empty:
                    continue
                
                # Precio actual
                current_price = float(df["close"].iloc[-1])
                fav.current_value = current_price
                fav.timestamp = datetime.datetime.utcnow()
                
                # Reglas de Alerta
                triggered = False
                if fav.alert_direction == "encima" and current_price >= fav.alert_value:
                    triggered = True
                elif fav.alert_direction == "debajo" and current_price < fav.alert_value:
                    triggered = True
                
                if triggered:
                    msg = f"🔔 ALERT: {fav.symbol} está a {current_price} ({fav.alert_direction} de {fav.alert_value})"
                    alertas_mensajes.append(msg)
                    print(f"  [!] {msg}")
                else:
                    print(f"  [-] {fav.symbol}: {current_price} no cumple {fav.alert_direction} {fav.alert_value}")

            except Exception as e:
                print(f"❌ Error evaluando {fav.symbol}: {e}")
        
        db.commit() # Guardar precios actualizados y timestamps
    finally:
        db.close()
    return alertas_mensajes

def send_alert(messages):
    """
    Envía una notificación vía POST con los mensajes detallados.
    """
    if not messages:
        return

    message_body = "\n".join(messages)
    
    try:
        response = requests.post(
            config.STOCK_ALERT,
            data=message_body.encode("utf-8"),
            headers={
                "Title": "Stock Alert",
                "Priority": "high",
                "Tags": "bell,chart_with_upwards_trend"
            }
        )
        if response.status_code == 200:
            print(f"🚀 Alertas enviadas (Stock Alert):\n{message_body}")
        else:
            print(f"⚠️ Alerta enviada pero el servidor respondió {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")

def run_alert_process(label="validación de reglas"):
    """
    Encapsula el flujo completo de evaluación y envío de alertas.
    Mismo código para alert_favoritos.py y alert_favoritos_cronjob.py.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).replace(tzinfo=None)
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"[{now_str}] Ejecutando {label}...")
    alertas = evaluate_rules()
    
    # Actualizar now_str para el log final
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).strftime('%Y-%m-%d %H:%M:%S')
    
    if alertas:
        send_alert(alertas)
    else:
        print(f"[{now_str}] ✅ No se detectaron alertas de precio.")
