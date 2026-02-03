from src.reglas_favoritos import run_alert_process

def execute():
    """
    Función principal que ejecuta el ciclo de validación (Cronjob Mode).
    Sin validación de horarios ni scheduler.
    """
    run_alert_process(label="ejecución cronjob")

if __name__ == "__main__":
    print("--- Proceso de Alertas de Stock (Cronjob Mode) ---")
    execute()
    print("--- Proceso Finalizado ---")
