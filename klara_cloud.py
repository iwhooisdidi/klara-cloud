import telebot
from groq import Groq
import requests
import os

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "8675385836:AAHuuwhua9T7z9VNIh_lEy7jmwLKRJPhTk4"
GROQ_API_KEY = "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" # Reemplaza con tu llave
HF_API_KEY = "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" # Reemplaza con tu llave de Hugging Face

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres Klara, asistente IA de Alejandro. 
Estás conectada a la red móvil vía Telegram. 
Tu objetivo es ayudarle 24/7. Sé sarcástica, brillante y directa."""

memoria_telegram = [{"role": "system", "content": SYSTEM_PROMPT}]

# --- GENERADOR DE IMÁGENES (Hugging Face) ---
def generar_imagen(prompt):
    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    return response.content

# --- CHAT MULTIMODAL ---
@bot.message_handler(content_types=['text', 'photo', 'voice'])
def manejar_mensajes(message):
    chat_id = message.chat.id

    # 1. SI ES UN MENSAJE DE TEXTO
    if message.content_type == 'text':
        texto_usuario = message.text
        
        # Detectar si pide una imagen
        if "genera una imagen" in texto_usuario.lower() or "dibuja" in texto_usuario.lower():
            bot.send_message(chat_id, "Procesando imagen, dame un segundo...")
            try:
                imagen_bytes = generar_imagen(texto_usuario)
                bot.send_photo(chat_id, imagen_bytes, caption="Aquí tienes, Alejandro.")
            except Exception as e:
                bot.send_message(chat_id, "Hubo un fallo en mi módulo de arte.")
            return

        # Respuesta normal de texto
        memoria_telegram.append({"role": "user", "content": texto_usuario})
        
        try:
            chat_completion = client.chat.completions.create(
                messages=memoria_telegram,
                model="llama3-8b-8192"
            )
            respuesta = chat_completion.choices[0].message.content
            memoria_telegram.append({"role": "assistant", "content": respuesta})
            bot.send_message(chat_id, respuesta)
        except Exception as e:
            bot.send_message(chat_id, f"Error en la red neuronal: {e}")

    # 2. SI ES UNA FOTO
    elif message.content_type == 'photo':
        bot.send_message(chat_id, "He recibido la imagen. Mi módulo visual de Groq/HF la está analizando (Función en desarrollo en esta API).")
        # Aquí se integraría la llamada específica al modelo de visión (LLaVA) de Groq cuando lo liberen o conectando HF.

    # 3. SI ES UNA NOTA DE VOZ
    elif message.content_type == 'voice':
        bot.send_message(chat_id, "Recibí tu nota de voz. Procesando audio...")
        # Lógica de descarga de archivo .ogg de Telegram -> Transcripción con Whisper (Groq) -> Respuesta.
        # (El código base está listo para expandir esta función sin romper el bot)

if __name__ == "__main__":
    print("Klara Cloud 24/7 conectada a Telegram...")
    bot.infinity_polling()