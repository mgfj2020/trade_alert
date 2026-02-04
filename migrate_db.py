import sqlite3
import os

base_dir = r"d:\antigravity-project\trade_alert"
db_path = os.path.join(base_dir, "databases", "trade_alert.db")

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(rsi_1d)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'hma_a' in columns:
        print("Renaming hma_a to promedio_variacion_3m...")
        cursor.execute("ALTER TABLE rsi_1d RENAME COLUMN hma_a TO promedio_variacion_3m")
    else:
        print("hma_a not found or already renamed.")
        
    if 'hma_b' in columns:
        print("Renaming hma_b to valor_actual...")
        cursor.execute("ALTER TABLE rsi_1d RENAME COLUMN hma_b TO valor_actual")
    else:
        print("hma_b not found or already renamed.")
        
    conn.commit()
    print("Migration successful.")
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
    exit(1)
