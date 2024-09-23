# Usa una imagen base oficial de Python
FROM python:3.12

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY . /app

# Instala las dependencias de la aplicación
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 8080 (necesario para Cloud Run)
EXPOSE 8080

# Define el comando para ejecutar la aplicación
CMD ["python", "App.py"]
