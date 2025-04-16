# Usar uma imagem base com Python
FROM python:3.12-slim

# Instalar dependências do sistema, incluindo o libGL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho no contêiner
WORKDIR /app

# Copiar o arquivo requirements.txt (onde estão as dependências do Python)
COPY requirements.txt .

# Instalar as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código para o contêiner
COPY . .

# Comando para rodar o bot (ou o seu script principal)
CMD ["python", "main.py"]
f
