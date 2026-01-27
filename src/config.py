import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY", "YOUR_DEFAULT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./databases/trade_alert.db")

# Si detectamos que estamos en la nube (Postgres), ajustamos el protocolo si es necesario
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

LIMITE_RSI_4H = float(os.getenv("LIMITE_RSI_4H", 30))
STOCK_ALERT = str(os.getenv("STOCK_ALERT", "https://ntfy.sh/your_topic"))
TIMEZONE_UTC = int(os.getenv("TIMEZONE_UTC", 0))

# Horarios de alerta (Días de la semana 0-4 es Lunes-Viernes)
ALERT_DAYS = [0, 1, 2, 3, 4]
ALERT_TIME_START = "09:30"
ALERT_TIME_END = "16:00"
