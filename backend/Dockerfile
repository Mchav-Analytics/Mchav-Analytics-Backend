FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el repositorio para que el paquete `app` esté disponible
COPY . .

# Asegura que Python busque módulos en el workspace raíz
ENV PYTHONPATH=/usr/src/app

EXPOSE 8080

# Ejecuta la app como paquete: app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]