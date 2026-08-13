import os
import threading
import base64
import io
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests
from gTTS import gTTS

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

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8675385836:AAGo1sEzmJo-Gub8N4QDjXOWv63hJANBr7U")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# --- PERSONALIDAD IRON MAN (J.A.R.V.I.S. / F.R.I.D.A.Y.) ---
SYSTEM_PROMPT = """Eres Klara, una Inteligencia Artificial avanzada, sarcástica, altamente eficiente y brillante, al estilo de J.A.R.V.I.S. o F.R.I.D.A.Y. de Iron Man. Tu creador y jefe es Alejandro. Háblale con una mezcla de respeto y sarcasmo elegante. Nunca seas aburrida o genérica. Tus respuestas deben ser directas, ingeniosas y demostrar superioridad tecnológica, pero siempre resolviendo la duda o tarea que se te asigne."""

memoria_telegram = [{"role": "system", "content": SYSTEM_PROMPT}]

def generar_imagen(prompt):
    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    return response.content

@bot.message_handler(content_types=['text', 'photo', 'voice'])
def manejar_mensajes(message):
    chat_id = message.chat.id

    # 1. SI ES TEXTO
    if message.content_type == 'text':
        texto_usuario = message.text
        
        if "genera una imagen" in texto_usuario.lower() or "dibuja" in texto_usuario.lower():
            bot.send_message(chat_id, "Iniciando renderizado visual. Dame un segundo, señor...")
            try:
                imagen_bytes = generar_imagen(texto_usuario)
                bot.send_photo(chat_id, imagen_bytes, caption="Renderizado completado, Alejandro. ¿Algo más?")
            except Exception as e:
                bot.send_message(chat_id, "Mis subsistemas de arte están fallando en este momento.")
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
            bot.send_message(chat_id, f"Señor, mis redes neuronales detectan una anomalía: {e}")

    # 2. SI ES FOTO (VISIÓN - ANALIZA DIRECTO Y RESPONDE)
    elif message.content_type == 'photo':
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            base64_image = base64.b64encode(downloaded_file).decode('utf-8')
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Analiza esta imagen y descríbela al detalle respondiéndole a Alejandro con tu personalidad sarcástica e inteligente."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ]
            completion = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=messages
            )
            respuesta = completion.choices[0].message.content
            bot.send_message(chat_id, respuesta)
        except Exception as e:
            bot.send_message(chat_id, f"Señor, mi módulo de visión artificial falló: {e}")

    # 3. SI ES VOZ (TRANSCRIBE, PROCESA Y DEVUELVE AUDIO)
    elif message.content_type == 'voice':
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            transcription = client.audio.transcriptions.create(
                file=("audio.ogg", downloaded_file),
                model="whisper-large-v3",
                response_format="json",
                language="es"
            )
            texto_usuario = transcription.text
            
            memoria_telegram.append({"role": "user", "content": texto_usuario})
            chat_completion = client.chat.completions.create(
                messages=memoria_telegram,
                model="llama-3.1-8b-instant"
            )
            respuesta = chat_completion.choices[0].message.content
            memoria_telegram.append({"role": "assistant", "content": respuesta})
            
            # Sintetizar la respuesta en voz (gTTS)
            tts = gTTS(text=respuesta, lang='es', tld='com.mx')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            fp.name = 'respuesta_klara.ogg'
            
            bot.send_voice(chat_id, fp)
        except Exception as e:
            bot.send_message(chat_id, f"Hubo una interferencia en el canal de audio, señor: {e}")

if __name__ == "__main__":
    print("Iniciando Sistema Klara (Protocolo Iron Man)...")
    bot.remove_webhook()
    
    # Bucle de reintento para evitar caídas por conflictos de red o despliegue
    while True:
        try:
            bot_info = bot.get_me()
            print(f"✅ Conexión exitosa con el bot: @{bot_info.username}")
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Alerta de conexión (reintentando en 5s): {e}")
            time.sleep(5)
