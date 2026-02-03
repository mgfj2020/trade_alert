import requests
import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from src.models import SessionLocal, Favorite
from src.core.polygon_client import obtener_velas_polygon
from src.core.indicators import procesar_indicadores, evaluar_estado_hma90
from src import config

def is_market_open():
    """
    Valida si el mercado está abierto según la configuración en config.py
    y el offset de TIMEZONE_UTC.
    """
    # Usar UTC y aplicar el offset
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now = now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)
    
    # Quitar info de timezone para un log más limpio
    now_clean = now.replace(tzinfo=None)
    
    # Verificar día de la semana
    if now_clean.weekday() not in config.ALERT_DAYS:
        return False
    
    # Verificar rango horario
    current_time = now_clean.strftime("%H:%M")
    print(f"[{now_clean.strftime('%Y-%m-%d %H:%M:%S')}] Verificando horario: {current_time}")
    print(f"{config.ALERT_TIME_START} <= {current_time} <= {config.ALERT_TIME_END}")
    return config.ALERT_TIME_START <= current_time <= config.ALERT_TIME_END

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
                # si la direccion == 'encima' && valor_actual >= valor_alerta, entonces cumple
                # si la direccion == 'debajo' && valor_actual < valor_alerta, entonces cumple
                
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

def execute():
    """
    Función principal que ejecuta el ciclo de validación.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).replace(tzinfo=None)
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    if not is_market_open():
        print(f"[{now_str}] Fuera de horario de mercado. Saltando...")
        return

    print(f"[{now_str}] Ejecutando validación de reglas...")
    alertas = evaluate_rules()
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).strftime('%Y-%m-%d %H:%M:%S')
    
    if alertas:
        send_alert(alertas)
    else:
        print(f"[{now_str}] ✅ No se detectaron alertas de precio.")

def start_scheduler():
    """
    Configura e inicia el scheduler.
    """
    scheduler = BackgroundScheduler()
    # Ejecutar cada 15 minutos
    scheduler.add_job(execute, 'interval', minutes=15, next_run_time=datetime.datetime.now())
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    import os
    # Modo script independiente
    print("--- Proceso de Alertas de Stock ---")
    
    # Si detectamos que es una ejecución de una sola vez (Cloud Run Job)
    if os.getenv("RUN_ONCE", "false").lower() == "true":
        print("Ejecutando escaneo único...")
        execute()
        print("Escaneo completado. Saliendo.")
    else:
        # Modo tradicional de scheduler en segundo plano
        sched = start_scheduler()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            print("Deteniendo scheduler...")
            sched.shutdown()
