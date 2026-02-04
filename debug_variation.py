import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def promedio_variacion_3m_debug(df, meses=3):
    print(f"Index type: {type(df.index)}")
    try:
        var = df[['var']].dropna()
        fecha_fin = var.index.max()
        print(f"Index max: {fecha_fin}")
        fecha_inicio = fecha_fin - pd.DateOffset(months=meses)
        print(f"Fecha inicio: {fecha_inicio}")
        var_3m = var.loc[fecha_inicio:fecha_fin]
        print(f"Rows found: {len(var_3m)}")
        return var_3m['var'].abs().mean()
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test 1: Int Index
data = {
    'datetime': pd.date_range(end=datetime.now(), periods=100),
    'var': np.random.randn(100)
}
df_int = pd.DataFrame(data)
print("--- Test 1: Numeric Index ---")
val1 = promedio_variacion_3m_debug(df_int)
print(f"Result: {val1}")

# Test 2: Datetime Index
df_dt = df_int.set_index('datetime')
print("\n--- Test 2: Datetime Index ---")
val2 = promedio_variacion_3m_debug(df_dt)
print(f"Result: {val2}")
