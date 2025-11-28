FROM python:3.11-slim

WORKDIR /app

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY . .

# Cria pastas de upload/output
RUN mkdir -p uploads docs_gerados

EXPOSE 5000

# Usa Gunicorn para produção ao invés do servidor de dev do Flask
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "main:app"]