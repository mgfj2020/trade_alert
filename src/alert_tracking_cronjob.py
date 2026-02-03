from src.reglas_tracking import run_tracking_process

def execute():
    """
    Función principal que ejecuta el ciclo de actualización de tracking (Cronjob Mode).
    """
    run_tracking_process(label="ejecución cronjob tracking HMA")

if __name__ == "__main__":
    print("--- Proceso de Alertas HMA Tracking (Cronjob Mode) ---")
    execute()
    print("--- Proceso Finalizado ---")
