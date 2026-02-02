import traceback
from sqlalchemy import create_engine, inspect, text
from src.config import DATABASE_URL
from src.models import init_db

def fix_schema():
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        with engine.begin() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # --- STOCK_TRACKING ---
            if 'stock_tracking' in tables:
                columns = [c['name'] for c in inspector.get_columns('stock_tracking')]
                new_cols = [
                    ("rsi_value", "FLOAT"), ("variation", "FLOAT"), ("rvol_1", "FLOAT"), ("rvol_2", "FLOAT"),
                    ("hma_a", "FLOAT"), ("hma_b", "FLOAT"), ("min_price", "FLOAT"), ("candles_since_min", "INTEGER"),
                    ("entry_date", "TIMESTAMP"), ("timestamp", "TIMESTAMP"), ("current_value", "FLOAT DEFAULT 0.0"),
                    ("alert_value", "FLOAT DEFAULT -1.0"), ("alert_direction", "VARCHAR DEFAULT 'debajo'")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in columns:
                        print(f"Añadiendo '{col_name}' a stock_tracking...")
                        conn.execute(text(f"ALTER TABLE stock_tracking ADD COLUMN {col_name} {col_type}"))

            # --- FAVORITES ---
            if 'favorites' in tables:
                columns = [c['name'] for c in inspector.get_columns('favorites')]
                new_cols_fav = [
                    ("current_value", "FLOAT DEFAULT 0.0"),
                    ("alert_value", "FLOAT DEFAULT -1.0"),
                    ("alert_direction", "VARCHAR DEFAULT 'debajo'"),
                    ("timestamp", "TIMESTAMP")
                ]
                for col_name, col_type in new_cols_fav:
                    if col_name not in columns:
                        print(f"Añadiendo '{col_name}' a favorites...")
                        conn.execute(text(f"ALTER TABLE favorites ADD COLUMN {col_name} {col_type}"))

        init_db()
        print("Sincronización técnica completada.")
    except Exception as e:
        print("ERROR DURANTE LA MIGRACIÓN:")
        traceback.print_exc()

if __name__ == "__main__":
    fix_schema()
