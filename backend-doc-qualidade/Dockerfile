FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema necessárias para compilação (se houver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Instala PyTorch CPU primeiro (Economia gigantesca de espaço)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Copia e instala o resto das dependências
COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

RUN python -m spacy download pt_core_news_lg

# 3. Copia o código
COPY . .

# Cria diretórios necessários para persistência
RUN mkdir -p app/core/faiss_index app/outputs

# Expõe a porta
EXPOSE 8000

# Comando de execução
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]