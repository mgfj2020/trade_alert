import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from src.core.polygon_client import obtener_velas_polygon, convertir_a_local_y_filtrar
from src.core.indicators import hma

def main():
    stock = "NVDA"
    timeframes = ["15min", "30min", "1H", "4H"]
    dfs = {}

    print(f"Descargando datos para {stock}...")
    for tf in timeframes:
        try:
            df = obtener_velas_polygon(stock, tf)
            # Usar rango de mercado completo para visualizar mejor
            df = convertir_a_local_y_filtrar(df, market_open="09:00", market_close="20:00")
            dfs[tf] = df
            print(f" - {tf}: {len(df)} velas descargadas.")
        except Exception as e:
            print(f" - Error descargando {tf}: {e}")
            return

    # Calcular HMAs específicas según la imagen de referencia
    print("Calculando HMAs multi-timeframe...")
    dfs["15min"]["hma_15min"] = hma(dfs["15min"]["close"], 30) # HMA 15 30 close logic
    dfs["30min"]["hma_30min"] = hma(dfs["30min"]["close"], 90) # HMA 30 90 close logic
    dfs["1H"]["hma_1h"] = hma(dfs["1H"]["close"], 90) # HMA 1H 90 close logic
    dfs["4H"]["hma_4h"] = hma(dfs["4H"]["close"], 90) # HMA 4H 90 close logic

    # Alinear todo al timeframe de 1H (base del gráfico solicitado)
    base_df = dfs["1H"].copy()
    
    for tf, col in [("15min", "hma_15min"), ("30min", "hma_30min"), ("4H", "hma_4h")]:
        temp_df = dfs[tf][[col]]
        base_df = pd.merge_asof(base_df.sort_index(), temp_df.sort_index(), left_index=True, right_index=True)

    # Preparar el estilo de mplfinance
    print("Generando gráfico estilo TradingView...")
    
    # Colores exactos de la imagen (aproximados por HEX)
    # HMA 15 (30): Negro -> #000000
    # HMA 30 (90): Rojo -> #ff1100
    # HMA 1H (90): Verde Esmeralda -> #00a651
    # HMA 4H (90): Naranja -> #f7941d

    colors = [
        {"data": base_df["hma_15min"], "color": "#000000", "width": 1.2, "label": "HMA 15 30"},
        {"data": base_df["hma_30min"], "color": "#ff1100", "width": 1.5, "label": "HMA 30 90"},
        {"data": base_df["hma_1h"], "color": "#00a651", "width": 1.5, "label": "HMA 1H 90"},
        {"data": base_df["hma_4h"], "color": "#f7941d", "width": 1.5, "label": "HMA 4H 90"},
    ]

    add_plots = []
    for c in colors:
        add_plots.append(mpf.make_addplot(c["data"].values, color=c["color"], width=c["width"]))

    # Crear el gráfico
    output_file = "hma_analysis_plot.png"
    
    # Estilo personalizado para parecerse a TD (fondo blanco, grilla tenue, eje derecha)
    mc = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit', volume='in', ohlc='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', gridcolor='#e0e0e0', facecolor='white', edgecolor='#e0e0e0')

    mpf.plot(base_df, 
             type='candle', 
             style=s, 
             addplot=add_plots, 
             figsize=(16, 10), 
             title=f"\n{stock} - 1H Analysis (HMA MTF)",
             ylabel="Precio",
             savefig=dict(fname=output_file, dpi=150, bbox_inches='tight'),
             tight_layout=True)

    print(f"Gráfico guardado como '{output_file}'")
    
    try:
        # Para mostrarlo necesitamos mpf.plot sin savefig o llamar a plt.show si mpf deja el plot en el buffer
        plt.show()
    except Exception:
        print("No se pudo mostrar la ventana del gráfico.")

if __name__ == "__main__":
    main()
