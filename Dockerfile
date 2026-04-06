# Základní image s Pythonem 3.11 (stabilní, kompatibilní s pandas)
FROM python:3.11-slim

# Nastavení pracovního adresáře
WORKDIR /app

# Zkopírovat requirements
COPY requirements.txt .

# Instalace závislostí
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Zkopírovat celý projekt
COPY . .

# Nastavení portu pro Render
ENV PORT=10000

# Start aplikace pomocí gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "1"]
