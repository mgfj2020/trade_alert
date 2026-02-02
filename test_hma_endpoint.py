import requests
import json

BASE_URL = "http://localhost:8000"

def test_recalculate_hma():
    print("--- Probando endpoint /api/recalculate_hma ---")
    try:
        # 1. Verificar si hay stocks en track_data
        r_data = requests.get(f"{BASE_URL}/api/track_data")
        stocks = r_data.json()
        print(f"Stocks en seguimiento antes: {len(stocks)}")
        
        if not stocks:
            print("Agregando stock de prueba (ONDS)...")
            # Esto depende de que ONDS esté en RSI_1D. 
            # Como no sabemos, intentaremos llamar al scan primero o simplemente asumir que hay algo.
            # Mejor vemos qué hay en /api/data
            r_all = requests.get(f"{BASE_URL}/api/data")
            all_data = r_all.json()
            if all_data:
                sym = all_data[0][0]
                requests.post(f"{BASE_URL}/api/add_track", json=[sym])
                print(f"Agregado {sym} a track.")
            else:
                print("No hay stocks en RSI_1D para agregar a track.")
                return

        # 2. Llamar a recalculate_hma
        print("Llamando a /api/recalculate_hma...")
        r_calc = requests.post(f"{BASE_URL}/api/recalculate_hma")
        print(f"Respuesta: {r_calc.status_code} - {r_calc.json()}")
        
        # 3. Verificar resultados
        r_data_after = requests.get(f"{BASE_URL}/api/track_data")
        stocks_after = r_data_after.json()
        for s in stocks_after:
            print(f"Stock: {s[0]}, HMA_A: {s[6]}, HMA_B: {s[7]}, Estado: {s[9]}")
            if s[9] is None:
                print(f"AVISO: {s[0]} sigue con estado None.")
            else:
                print(f"ÉXITO: {s[0]} tiene estado {s[9]}")

    except Exception as e:
        print(f"Error en el test: {e}")

if __name__ == "__main__":
    test_recalculate_hma()
