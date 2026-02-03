import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from src import config
from src.reglas_favoritos import run_alert_process

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

def execute():
    """
    Función principal que ejecuta el ciclo de validación con validación de horario.
    """
    if not is_market_open():
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_str = (now_utc + datetime.timedelta(hours=config.TIMEZONE_UTC)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now_str}] Fuera de horario de mercado. Saltando...")
        return

    run_alert_process(label="validación de reglas")

def start_scheduler():
    """
    Configura e inicia el scheduler.
    """
    scheduler = BackgroundScheduler()
    # Ejecutar cada 15 minutos
    scheduler.add_job(execute, 'interval', minutes=config.HMA_B if hasattr(config, "SCHEDULER_INTERVAL") else 15, next_run_time=datetime.datetime.now())
    # NOTA: Usamos HMA_B temporalmente si no hay SCHEDULER_INTERVAL en config, 
    # pero el usuario tiene SCHEDULER_INTERVAL=15 en .env que config.py no lee aún.
    # Ajustemos config para leerlo.
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
