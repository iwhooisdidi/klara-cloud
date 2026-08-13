import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests

# --- SERVIDOR FANTASMA PARA RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Klara Cloud is online!")

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# --- CONFIGURACIÓN CON TOKEN DIRECTO ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8675385836:AAGo1sEzmJo-Gub8N4QDjXOWv63hJANBr7U")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres Klara, asistente IA de Alejandro. 
Estás conectada a la red móvil vía Telegram. 
Tu objetivo es ayudarle 24/7. Sé sarcástica, brillante y directa."""

memoria_telegram = [{"role": "system", "content": SYSTEM_PROMPT}]

def generar_imagen(prompt):
    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    return response.content

@bot.message_handler(content_types=['text', 'photo', 'voice'])
def manejar_mensajes(message):
    chat_id = message.chat.id

    if message.content_type == 'text':
        texto_usuario = message.text
        
        if "genera una imagen" in texto_usuario.lower() or "dibuja" in texto_usuario.lower():
            bot.send_message(chat_id, "Procesando imagen, dame un segundo...")
            try:
                imagen_bytes = generar_imagen(texto_usuario)
                bot.send_photo(chat_id, imagen_bytes, caption="Aquí tienes, Alejandro.")
            except Exception as e:
                bot.send_message(chat_id, "Hubo un fallo en mi módulo de arte.")
            return

        memoria_telegram.append({"role": "user", "content": texto_usuario})
        
        try:
            chat_completion = client.chat.completions.create(
                messages=memoria_telegram,
                model="llama-3.1-8b-instant"
            )
            respuesta = chat_completion.choices[0].message.content
            memoria_telegram.append({"role": "assistant", "content": respuesta})
            bot.send_message(chat_id, respuesta)
        except Exception as e:
            bot.send_message(chat_id, f"Error en la red neuronal: {e}")

    elif message.content_type == 'photo':
        bot.send_message(chat_id, "He recibido la imagen. Analizando...")

    elif message.content_type == 'voice':
        bot.send_message(chat_id, "Recibí tu nota de voz.")

if __name__ == "__main__":
    print("Iniciando Klara Cloud...")
    try:
        bot_info = bot.get_me()
        print(f"✅ Conexión exitosa con el bot: @{bot_info.username}")
        # Limpieza estándar de webhook sin argumentos incompatibles
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
