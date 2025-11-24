FROM python:3.11-slim

WORKDIR /app

# 1. Zuerst nur die Abhängigkeiten installieren (ändern sich selten)
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" requests

# 2. Danach den eigentlichen Code ins Image kopieren (ändert sich oft)
COPY . /app

EXPOSE 10010

CMD ["uvicorn", "gateway.gateway:app", "--host", "0.0.0.0", "--port", "10010"]
