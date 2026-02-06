import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY", "YOUR_DEFAULT_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("FATAL: No se encontró DATABASE_URL. Abortando programa...", flush=True)
    sys.exit(1)



# Si detectamos que estamos en la nube (Postgres), ajustamos el protocolo si es necesario
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

LIMITE_RSI_1D = float(os.getenv("LIMITE_RSI_1D", 30))

STOCK_ALERT = str(os.getenv("STOCK_ALERT", "https://ntfy.sh/mg_alert_2026"))
HMA_ALERT = str(os.getenv("HMA_ALERT", "https://ntfy.sh/mg_regla1_2026"))
HMA_ALCISTA = str(os.getenv("HMA_ALCISTA", "ntfy.sh/mg_hma_alcista"))
HMA_BAJISTA = str(os.getenv("HMA_BAJISTA", "ntfy.sh/mg_hma_bajista"))


TIMEZONE_UTC = int(os.getenv("TIMEZONE_UTC", 0))
HMA_A = int(os.getenv("HMA_A", 10))
HMA_B = int(os.getenv("HMA_B", 20))

# Horarios de alerta (Días de la semana 0-4 es Lunes-Viernes)
ALERT_DAYS = [0, 1, 2, 3, 4]

# Usar horas de .env si están disponibles, de lo contrario usar default
START_HOUR = os.getenv("SCHEDULER_START_HOUR", "09")
END_HOUR = os.getenv("SCHEDULER_END_HOUR", "16")

# Asegurar formato HH:MM
if ":" not in START_HOUR:
    START_HOUR = f"{int(START_HOUR):02d}:00"
if ":" not in END_HOUR:
    END_HOUR = f"{int(END_HOUR):02d}:00"

ALERT_TIME_START = os.getenv("ALERT_TIME_START", START_HOUR)
ALERT_TIME_END = os.getenv("ALERT_TIME_END", END_HOUR)

PRINT_OUTPUT = os.getenv("PRINT_OUTPUT", "FALSE").upper() == "TRUE"

