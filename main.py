import logging
import os
import pytesseract
import gspread
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# --- Configurações ---
TOKEN = "8068955182:AAEQLG6ewM2DhV19FiCyCBRqPnj42HCS4VM"
PLANILHA_ID = "1pJocCGzuPMrqzDilq_SRsPW_DOb3Bd43WItKmaPZZ7I"
ABA_VEICULOS = "Veículos"
ABA_OBSERVACOES = "Observações"

# --- Autenticação Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
gc = gspread.authorize(creds)
sheet_veiculos = gc.open_by_key(PLANILHA_ID).worksheet(ABA_VEICULOS)
sheet_obs = gc.open_by_key(PLANILHA_ID).worksheet(ABA_OBSERVACOES)

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Busca placa na planilha ---
async def buscar_placa(update: Update, context: ContextTypes.DEFAULT_TYPE, placa: str):
    try:
        data = sheet_veiculos.get_all_records()
        for row in data:
            if str(row['Placa']).strip().upper() == placa.upper():
                texto = (
                    f"🚗 *Placa*: {row['Placa']}\n"
                    f"📌 *Carro*: {row.get('Carro', 'N/A')}\n"
                    f"🎨 *Cor*: {row.get('Cor', 'N/A')}\n"
                    f"🧾 *Financiado para*: {row.get('Financiado', 'N/A')}"
                )
                keyboard = [
                    [InlineKeyboardButton("📍 Enviar Localização", callback_data=f'localizar:{row["Placa"]}')],
                    [InlineKeyboardButton("📝 Adicionar Observação", callback_data=f'observar:{row["Placa"]}')],
                    [InlineKeyboardButton("📄 Relatório da Placa", callback_data=f'relatorio:{row["Placa"]}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_markdown(texto, reply_markup=reply_markup)
                return
        await update.message.reply_text("Placa não encontrada na planilha.")
    except Exception as e:
        logging.exception("Erro ao buscar a placa")
        await update.message.reply_text("Erro ao buscar a placa.")

# --- Handler de botões ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('localizar:'):
        context.user_data['ultima_placa'] = data.split(":")[1]
        await query.message.reply_text("Envie sua localização atual compartilhando pelo Telegram.")

    elif data.startswith('observar:'):
        context.user_data['ultima_placa'] = data.split(":")[1]
        await query.message.reply_text("Digite a observação que deseja adicionar.")

    elif data.startswith('relatorio:'):
        placa = data.split(":")[1]
        linhas = sheet_obs.get_all_records()
        observacoes = []
        for row in linhas:
            if str(row['Placa']).strip().upper() == placa.upper():
                obs = row.get('Observação', '').strip()
                loc = row.get('Localização', '').strip()
                data = row.get('Data', '').strip()
                if obs or loc:
                    bloco = f"📆 {data}"
                    if loc:
                        bloco += f"\n📍 Localização: {loc}"
                    if obs:
                        bloco += f"\n📝 Observação: {obs}"
                    observacoes.append(bloco)
        if observacoes:
            await query.message.reply_text(f"📄 Relatório da Placa {placa}:\n\n" + "\n---\n".join(observacoes))
        else:
            await query.message.reply_text("Sem informações extras para esta placa.")

# --- Processa texto (placa ou observação) ---
async def decidir_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'ultima_placa' in context.user_data:
        obs = update.message.text
        data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
        sheet_obs.append_row([context.user_data['ultima_placa'], obs, '', data_hora])
        del context.user_data['ultima_placa']
        await update.message.reply_text("📝 Observação salva!")
    else:
        texto = update.message.text.strip()
        if texto.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
            await update.message.reply_text("Olá! Me envie uma placa ou uma foto dela para buscar informações.")
        else:
            await buscar_placa(update, context, texto)

# --- OCR de fotos com pré-processamento ---
async def foto_placa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = update.message.photo[-1]
    file = await foto.get_file()
    path = "temp.jpg"
    await file.download_to_drive(path)

    # Processar imagem com OpenCV
    image = cv2.imread(path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    texto = pytesseract.image_to_string(thresh)
    os.remove(path)

    import re
    placas_encontradas = re.findall(r'[A-Z]{3}[0-9][0-9A-Z][0-9]{2}', texto.upper())

    if placas_encontradas:
        placa = placas_encontradas[0]
        await buscar_placa(update, context, placa)
    else:
        await update.message.reply_text("❌ Não foi possível identificar uma placa válida na imagem.")

# --- Localização enviada ---
async def receber_localizacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'ultima_placa' in context.user_data:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        url = f"https://www.google.com/maps?q={lat},{lon}"
        data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
        sheet_obs.append_row([context.user_data['ultima_placa'], '', url, data_hora])
        del context.user_data['ultima_placa']
        await update.message.reply_text("📍 Localização registrada!")

# --- Inicialização ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, foto_placa))
    app.add_handler(MessageHandler(filters.LOCATION, receber_localizacao))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), decidir_texto))

    print("✅ Bot rodando...")
    app.run_polling()
