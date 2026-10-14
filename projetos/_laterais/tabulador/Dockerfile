# Dockerfile de Produção — Tabulador Web (Instituto Olhar / Jumppi)
FROM python:3.12-slim

# Evita geração de .pyc desnecessários e ativa flush imediato de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Instala dependências do sistema necessárias para compilação eventual
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python com cache de camadas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Expõe a porta padrão do servidor web
EXPOSE 5000

# Healthcheck para monitoramento do container
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1

# Inicialização com Gunicorn em modo multi-thread de produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
