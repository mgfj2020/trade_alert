# Usa una imagen de Python ligera
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y permite que los logs se vean en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 (Postgres)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Exponer el puerto que usará FastAPI (Cloud Run lo sobreescribe pero es buena práctica)
EXPOSE 8080

# Comando para ejecutar la aplicación
# Usamos el módulo para que reconozca los imports de src
CMD ["python", "-m", "src.main"]
