import sys
import os

# Añadir el directorio actual al path para importar desde src
sys.path.append(os.getcwd())

from src.models import engine
from sqlalchemy import text

def migrate():
    print("Iniciando migración de PostgreSQL...")
    cols = ["alert_alcista", "alert_bajista"]
    for col in cols:
        with engine.begin() as connection:
            try:
                connection.execute(text(f"ALTER TABLE stock_tracking ADD COLUMN {col} INTEGER DEFAULT 1"))
                print(f"Columna '{col}' agregada.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"La columna '{col}' ya existe.")
                else:
                    print(f"Error al agregar '{col}': {e}")
    print("Migración completada.")
    print("Migración completada con éxito.")

if __name__ == "__main__":
    migrate()
