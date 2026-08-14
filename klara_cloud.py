import os
import threading
import base64
import io
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests
from gtts import gTTS
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS
from PIL import Image

# --- CONFIGURACIÓN DE CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# --- PERSONALIDAD IRON MAN (J.A.R.V.I.S. / F.R.I.D.A.Y.) ---
SYSTEM_PROMPT = """Eres Klara, una Inteligencia Artificial avanzada, sarcástica, altamente eficiente y brillante, al estilo de J.A.R.V.I.S. o F.R.I.D.A.Y. de Iron Man. Tu creador y jefe es Alejandro. Háblale con una mezcla de respeto y sarcasmo elegante. Nunca seas aburrida o genérica. Tus respuestas deben ser directas, ingeniosas y demostrar superioridad tecnológica, pero siempre resolviendo la duda o tarea que se te asigne."""

# Memoria individualizada por Chat ID
memorias_chat = {}

def obtener_memoria(chat_id):
    if chat_id not in memorias_chat:
        memorias_chat[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return memorias_chat[chat_id]

def agregar_a_memoria(chat_id, rol, contenido):
    mem = obtener_memoria(chat_id)
    mem.append({"role": rol, "content": contenido})
    # Mantener el System Prompt (0) y máximo los últimos 6 mensajes
    if len(mem) > 7:
        memorias_chat[chat_id] = [mem[0]] + mem[-6:]

# --- FUNCIÓN PARA EVITAR EL ERROR 400 "MESSAGE IS TOO LONG" DE TELEGRAM ---
def enviar_respuesta_segura(message, texto):
    MAX_LEN = 4000
    if not texto:
        return
    if len(texto) <= MAX_LEN:
        bot.reply_to(message, texto)
    else:
        # Envía el primer bloque respondiendo al mensaje original
        bot.reply_to(message, texto[:MAX_LEN])
        # Envía los bloques restantes como nuevos mensajes en secuencia
        for i in range(MAX_LEN, len(texto), MAX_LEN):
            bot.send_message(message.chat.id, texto[i:i+MAX_LEN])

# --- ESTADO DE LA PC Y PUENTE DE COMUNICACIÓN ---
pc_ultima_conexion = 0
cola_comandos_pc = []

class CloudBridgeHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        # Solución al error 501 de Render
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        global pc_ultima_conexion, cola_comandos_pc
        
        # 1. Tu PC le avisa a Render que está encendida
        if self.path == '/heartbeat':
            pc_ultima_conexion = time.time()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            
        # 2. Tu PC le consulta a Render si hay órdenes físicas pendientes
        elif self.path == '/poll':
            pc_ultima_conexion = time.time()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            comando = cola_comandos_pc.pop(0) if cola_comandos_pc else None
            self.wfile.write(json.dumps({"command": comando}).encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Klara Cloud is 24/7 online!")

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), CloudBridgeHandler)
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# --- FUNCIONES NUCLEARES DE KLARA ---

def buscar_en_internet(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r['title']}: {r['href']} ({r.get('body', '')})" for r in results])
    except Exception:
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

# --- MANEJADOR UNIFICADO DE MENSAJES ---

@bot.message_handler(content_types=['text', 'document', 'photo', 'voice'])
def manejar_mensajes(message):
    global pc_ultima_conexion, cola_comandos_pc
    chat_id = message.chat.id
    texto = message.text or message.caption or ""

    # Verificar si la PC se ha reportado en los últimos 15 segundos
    pc_encendida = (time.time() - pc_ultima_conexion) < 15

    # DETECCIÓN DE ÓRDENES PARA LA COMPUTADORA
    texto_lower = texto.lower()
    menciones_pc = ["en la pc", "en la computadora", "en mi pc", "en el ordenador", "computadora"]
    
    es_orden_pc = any(m in texto_lower for m in menciones_pc) or texto_lower.startswith("/pc")

    if es_orden_pc and message.content_type == 'text':
        if pc_encendida:
            comando_limpio = texto.replace("/pc", "").strip()
            enviar_respuesta_segura(message, "Analizando entorno del sistema y generando protocolo de ejecución, Alejandro...")
            
            prompt_codigo = f"""
            Eres el motor de ejecución autónomo para Windows de Alejandro.
            El usuario solicitó: '{comando_limpio}'
            
            Tu objetivo es escribir ÚNICA Y EXCLUSIVAMENTE código Python ejecutable que cumpla la orden de forma robusta.
            
            REGLAS DE RAZONAMIENTO MULTI-RUTA:
            1. CLASIFICACIÓN DE SERVICIOS:
               - Plataformas Web (YouTube, Canva, Pinterest, Google Meet, Gmail, Google): NO BUSQUES archivos .exe locales. Usa 'webbrowser.open()' directamente con la URL de la plataforma o la consulta específica.
               - Aplicaciones Nativas (Roblox, Spotify, Discord, VS Code, Bloc de Notas): Intenta abrir el acceso directo o protocolo URI (ej. 'roblox://' o usando os.system).
            
            2. NAVEGACIÓN Y REPRODUCCIÓN EN YOUTUBE:
               - Para buscar y reproducir un video en YouTube:
                 a) Abre la búsqueda directa: webbrowser.open('https://www.youtube.com/results?search_query=TERMINO_DE_BUSQUEDA')
                 b) Espera 4 a 5 segundos con time.sleep(5)
                 c) Usa pyautogui.press('tab', presses=4, interval=0.2) o pyautogui.click() en las coordenadas aproximadas del primer resultado, seguido de pyautogui.press('enter').

            3. ESTRUCTURA Y SINTAXIS:
               - NO uses Markdown (NO ```python). Solo código Python puro.
               - Incluye 'import webbrowser, pyautogui, time, os' al inicio del bloque si es necesario.
               - Incluye tiempos de espera razonables ('time.sleep(3)') entre acciones para permitir la carga de páginas web o programas.
            """

            try:
                completion_pc = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt_codigo}]
                )
                
                codigo_generado = completion_pc.choices[0].message.content
                codigo_generado = codigo_generado.replace("```python", "").replace("```", "").strip()
                
                cola_comandos_pc.append(f"EXEC:{codigo_generado}")
                enviar_respuesta_segura(message, "Protocolo enviado a tu estación de trabajo. Ejecutando comando...")
            except Exception as e:
                enviar_respuesta_segura(message, f"Error generando el código de automatización: {e}")
        else:
            enviar_respuesta_segura(message, "Tu computadora está offline o desconectada del puente de control, Alejandro.")
        return

    # PROCESAMIENTO MULTIMODAL (VOZ, FOTO, DOCUMENTO, TEXTO)
    es_voz = False
    
    if message.content_type == 'voice':
        es_voz = True
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Transcripción mediante Whisper en Groq
            transcription = client.audio.transcriptions.create(
                file=("voice.ogg", downloaded_file),
                model="whisper-large-v3",
                response_format="text"
            )
            texto = str(transcription).strip()
        except Exception as e:
            enviar_respuesta_segura(message, f"Error procesando nota de voz: {e}")
            return

    elif message.content_type == 'document':
        try:
            file_info = bot.get_file(message.document.file_id)
            file_ext = os.path.splitext(file_info.file_path)[1].lower()
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_path = f"temp_{message.document.file_id}{file_ext}"
            with open(temp_path, "wb") as f:
                f.write(downloaded_file)
            
            contenido_doc = procesar_archivo(temp_path, file_ext)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            texto = f"El usuario adjuntó un archivo ({message.document.file_name}). Contenido:\n{contenido_doc}\nMensaje adicional: {texto}"
        except Exception as e:
            enviar_respuesta_segura(message, f"Error procesando documento: {e}")
            return

    elif message.content_type == 'photo':
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Compresión de la imagen
            img = Image.open(io.BytesIO(downloaded_file))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.thumbnail((1024, 1024))
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Análisis visual mediante Llama 3.2 Vision
            vision_response = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe con precisión esta imagen y responde a lo siguiente si aplica: " + (texto or "Analiza el contenido de la imagen.")},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }]
            )
            analisis_imagen = vision_response.choices[0].message.content
            texto = f"[Análisis de imagen enviada]: {analisis_imagen}\nComentario de Alejandro: {texto}"
        except Exception as e:
            enviar_respuesta_segura(message, f"Error analizando la imagen: {e}")
            return

    # EVALUACIÓN DE BÚSQUEDA WEB SI LA CONSULTA REQUIERE INFORMACIÓN ACTUALIZADA
    if any(k in texto.lower() for k in ["busca", "investiga", "noticias", "quién es", "qué es", "precio"]):
        info_web = buscar_en_internet(texto)
        texto += f"\n\n[Información obtenida de Internet]:\n{info_web}"

    # RESPUESTA PRINCIPAL DE KLARA MEDIANTE GROQ
    agregar_a_memoria(chat_id, "user", texto)
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=obtener_memoria(chat_id),
            temperature=0.7,
            max_tokens=1000
        )
        
        respuesta = completion.choices[0].message.content
        agregar_a_memoria(chat_id, "assistant", respuesta)

        if es_voz:
            # Convertir la respuesta a audio si el usuario se comunicó por nota de voz
            tts = gTTS(text=respuesta, lang='es', tld='com.mx')
            voice_io = io.BytesIO()
            tts.write_to_fp(voice_io)
            voice_io.seek(0)
            bot.send_voice(chat_id, voice_io, reply_to_message_id=message.message_id)
        else:
            enviar_respuesta_segura(message, respuesta)

    except Exception as e:
        enviar_respuesta_segura(message, f"Error de comunicación interna: {e}")

# --- INICIO DEL BOT ---
if __name__ == "__main__":
    bot.infinity_polling()
