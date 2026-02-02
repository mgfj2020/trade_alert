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
                print("Recreando stock_tracking para ajustar al nuevo esquema...")
                conn.execute(text("DROP TABLE stock_tracking"))

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
