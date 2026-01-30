# --- ETAPA 1: BUILDER ---
# Aquí instalamos todo lo necesario para compilar (pesa mucho)
FROM python:3.11-slim AS builder

WORKDIR /app

# Evitar archivos temporales de Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalamos GCC y librerías de desarrollo necesarias para compilar psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalamos las dependencias de Python
# Usamos --user para que se instalen en una carpeta fácil de copiar luego
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# --- ETAPA 2: RUNTIME ---
# Esta es la imagen que realmente se subirá a la nube (será ligera)
FROM python:3.11-slim AS runtime

WORKDIR /app

# Solo instalamos la librería de ejecución de Postgres (mucho más pequeña que la de desarrollo)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# COPIAMOS solo las librerías ya instaladas desde la etapa 'builder'
# Esto deja fuera a GCC y todos los archivos temporales de compilación
COPY --from=builder /root/.local /root/.local

# Aseguramos que Python encuentre las librerías que copiamos
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copiamos solo el código de nuestra app
COPY . .

EXPOSE 8080

CMD ["python", "-m", "src.main"]
