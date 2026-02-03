import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from src import config
from src.reglas_tracking import run_tracking_process

def is_market_open():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now = now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)
    now_clean = now.replace(tzinfo=None)
    
    if now_clean.weekday() not in config.ALERT_DAYS:
        return False
    
    current_time = now_clean.strftime("%H:%M")
    return config.ALERT_TIME_START <= current_time <= config.ALERT_TIME_END

def execute():
    if not is_market_open():
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_str = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now_str}] Fuera de horario de mercado (Tracking). Saltando...")
        return

    run_tracking_process(label="validación de tracking HMA")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Ejecutar cada 60 minutos (1 hora) como solicitó el usuario
    scheduler.add_job(execute, 'interval', minutes=60, next_run_time=datetime.datetime.now())
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    print("--- Proceso de Alertas de HMA Tracking ---")
    sched = start_scheduler()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Deteniendo scheduler...")
        sched.shutdown()
