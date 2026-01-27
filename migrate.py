import sqlite3
import os

db_path = 'databases/trade_alert.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lista de columnas a verificar/añadir
    columns_to_add = [
        ("variation", "FLOAT DEFAULT 0.0"),
        ("rvol_1", "FLOAT DEFAULT 0.0"),
        ("rvol_2", "FLOAT DEFAULT 0.0"),
        ("alert_direction", "VARCHAR DEFAULT 'debajo'")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            # Primero verificamos si rsi_4h existe (para variation, rvol)
            if col_name in ["variation", "rvol_1", "rvol_2"]:
                table = "rsi_4h"
            else:
                table = "favorites"
                
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            print(f"Columna '{col_name}' añadida exitosamente a {table}.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"La columna '{col_name}' ya existe.")
            else:
                print(f"Error al añadir columna {col_name}: {e}")
            
    conn.commit()
    conn.close()

from src.models import init_db
init_db()
print("Sincronización de modelos completada.")
