import sqlite3
import os

db_path = "trade_alert.db" 
# Intentamos detectar la ruta desde src.config si fuera posible, 
# pero trade_alert.db suele estar en la raíz o en databases/

if not os.path.exists(db_path):
    # Probar en databases/ si no está en la raíz
    db_path = os.path.join("databases", "trade_alert.db")

if os.path.exists(db_path):
    print(f"Migrando base de datos en: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lista de columnas a agregar (si no existen)
    columns_to_add = [
        ("StockTracking", "alert_alcista", "INTEGER DEFAULT 1"),
        ("StockTracking", "alert_bajista", "INTEGER DEFAULT 1"),
    ]
    
    for table, col, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            print(f"Columna {col} agregada a la tabla {table}.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"La columna {col} ya existe en la tabla {table}.")
            else:
                print(f"Error al agregar {col} a {table}: {e}")
                
    conn.commit()
    conn.close()
    print("Migración completada.")
else:
    print("No se encontró el archivo trade_alert.db para migrar. Se creará automáticamente con el nuevo esquema al iniciar la app.")
