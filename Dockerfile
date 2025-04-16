# Use uma imagem oficial do Python como base
FROM python:3.12-slim

# Setar o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (para OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar os arquivos do projeto para o container
COPY . /app

# Criar um ambiente virtual
RUN python3 -m venv /opt/venv

# Ativar o ambiente virtual e instalar as dependências do Python
RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install -r requirements.txt

# Definir variáveis de ambiente para garantir o uso do ambiente virtual
ENV PATH="/opt/venv/bin:$PATH"

# Expor a porta que o aplicativo irá usar (se for o caso)
EXPOSE 5000

# Comando para rodar o seu app quando o container for iniciado
CMD ["python", "main.py"]
