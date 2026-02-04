import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    print("Renaming columns in rsi_1d...")
    
    # In Postgres, we can check if columns exist before renaming
    # but for simplicity and common practice in these tasks:
    try:
        cursor.execute("ALTER TABLE rsi_1d RENAME COLUMN hma_a TO promedio_variacion_3m;")
        print("Renamed hma_a to promedio_variacion_3m")
    except Exception as e:
        print(f"Could not rename hma_a (might already be renamed or not exist): {e}")
        conn.rollback()
        
    try:
        cursor.execute("ALTER TABLE rsi_1d RENAME COLUMN hma_b TO valor_actual;")
        print("Renamed hma_b to valor_actual")
    except Exception as e:
        print(f"Could not rename hma_b (might already be renamed or not exist): {e}")
        conn.rollback()
        
    conn.commit()
    print("Migration finished.")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to Postgres: {e}")
    exit(1)
