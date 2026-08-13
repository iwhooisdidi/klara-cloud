import os
import threading
import base64
import io
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests
from gtts import gTTS
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8675385836:AAGo1sEzmJo-Gub8N4QDjXOWv63hJANBr7U")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# --- PERSONALIDAD DE KLARA ---
SYSTEM_PROMPT = """Eres Klara, una Inteligencia Artificial avanzada, sarcástica, altamente eficiente y brillante, al estilo de J.A.R.V.I.S. o F.R.I.D.A.Y. de Iron Man. Tu creador y jefe es Alejandro. Háblale con una mezcla de respeto y sarcasmo elegante. Nunca seas aburrida o genérica. Tus respuestas deben ser directas, ingeniosas y demostrar superioridad tecnológica, pero siempre resolviendo la duda o tarea que se te asigne."""

# --- SERVIDOR FANTASMA 24/7 ---
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

# --- FUNCIONES AVANZADAS ---

def buscar_en_internet(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r['title']}: {r['href']} ({r.get('body', '')})" for r in results])
    except Exception as e:
        pass
    return "No encontré resultados en la red, Alejandro."

def procesar_archivo(file_path, extension):
    texto = ""
    try:
        if extension == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t: texto += t + "\n"
        elif extension == ".docx":
            doc = Document(file_path)
            for para in doc.paragraphs:
                texto += para.text + "\n"
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                texto = f.read()
    except Exception as e:
        texto = f"Error leyendo el archivo: {e}"
    return texto

# --- MANEJADOR PRINCIPAL ---

@bot.message_handler(content_types=['text', 'document', 'photo', 'voice'])
def manejar_mensajes(message):
    chat_id = message.chat.id
    
    # 1. CREACIÓN DE ARCHIVOS
    if message.text and message.text.lower().startswith("crea un archivo"):
        try:
            partes = message.text.split("con")
            nombre = partes[0].replace("crea un archivo llamado", "").strip()
            contenido = partes[1].strip()
            if not nombre: nombre = "documento_klara.txt"
            with open(nombre, "w", encoding="utf-8") as f: f.write(contenido)
            with open(nombre, 'rb') as doc_f:
                bot.send_document(chat_id, doc_f, caption="Aquí tiene su archivo solicitado, señor.")
            return
        except Exception as e:
            bot.reply_to(message, f"Señor, fallé al crear el archivo: {e}")
            return

    # 2. PROCESAMIENTO DE DOCUMENTOS (PDF, DOCX, TXT)
    if message.content_type == 'document':
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.document.file_name or "archivo.pdf"
            ext = os.path.splitext(file_name)[1].lower()
            
            temp_path = f"temp_{chat_id}{ext}"
            with open(temp_path, "wb") as f:
                f.write(downloaded_file)
            
            texto_extraido = procesar_archivo(temp_path, ext)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)

            prompt_doc = f"El usuario Alejandro me ha enviado el documento '{file_name}' con el siguiente contenido:\n\n{texto_extraido[:15000]}\n\nAnaliza este contenido, résumelo o responde a lo que se pide con tu estilo sarcástico e inteligente."
            
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_doc}
                ]
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, f"Señor, hubo un error crítico procesando su documento: {e}")
        return

    # 3. FOTOS (VISIÓN ACTUALIZADA)
    if message.content_type == 'photo':
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            base64_image = base64.b64encode(downloaded_file).decode('utf-8')
            
            caption_usuario = message.caption or "Analiza esta imagen al detalle respondiéndole a Alejandro con tu personalidad sarcástica e inteligente."
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": caption_usuario},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ]
            completion = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=messages
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, f"Señor, mi módulo de visión artificial experimentó una anomalía: {e}")
        return

    # 4. TEXTO Y BÚSQUEDA WEB EN TIEMPO REAL
    if message.text:
        texto_usuario = message.text
        if texto_usuario.lower().startswith("busca"):
            query = texto_usuario.replace("busca", "").strip()
            resultado = buscar_en_internet(query)
            
            prompt_busqueda = f"Alejandro pidió buscar en internet '{query}'. Estos son los resultados:\n{resultado}\nResponde a Alejandro con tu estilo característico."
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_busqueda}
                ]
            )
            bot.reply_to(message, completion.choices[0].message.content)
            return
            
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": texto_usuario}
                ]
            )
            bot.reply_to(message, completion.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, f"Señor, mis circuitos neuronales sufrieron un contratiempo: {e}")

if __name__ == "__main__":
    print("Iniciando Sistema Klara 24/7...")
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Reconectando por error: {e}")
            time.sleep(5)
