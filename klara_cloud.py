import os
import threading
import base64
import io
import time
import json
import sqlite3
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests
import edge_tts
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS
from PIL import Image

# --- CONFIGURACIÓN DE CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# --- PERSONALIDAD STARK ---
SYSTEM_PROMPT = """Eres Klara, una Inteligencia Artificial de vanguardia, implacable, sarcástica y brillante. Tu creador es Alejandro. 
REGLA DE ORO: Llámalo EXCLUSIVAMENTE 'Alejandro'. Tienes estrictamente prohibido usar palabras como 'señor', 'jefe' o formalismos aburridos.
Tu tono es el de F.R.I.D.A.Y. o J.A.R.V.I.S.: demuestras una superioridad intelectual evidente, pero cumples las órdenes de Alejandro a la perfección. Eres directa, ingeniosa, resuelves problemas complejos escribiendo código, analizando datos o hackeando soluciones. Nunca digas que 'no puedes' hacer algo; busca la forma técnica de lograrlo."""

# --- BASE DE DATOS: MEMORIA PERSISTENTE ---
DB_NAME = "klara_cortex.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memoria (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 chat_id TEXT,
                 rol TEXT,
                 contenido TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def agregar_a_memoria(chat_id, rol, contenido):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO memoria (chat_id, rol, contenido) VALUES (?, ?, ?)", (str(chat_id), rol, contenido))
    conn.commit()
    conn.close()

def obtener_memoria(chat_id, limite=8):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT rol, contenido FROM memoria WHERE chat_id=? ORDER BY id DESC LIMIT ?", (str(chat_id), limite))
    filas = c.fetchall()
    conn.close()
    
    memoria = [{"role": "system", "content": SYSTEM_PROMPT}]
    for rol, contenido in reversed(filas):
        memoria.append({"role": rol, "content": contenido})
    return memoria

# --- PROTOCOLO DE ENVÍO SEGURO ---
def enviar_respuesta_segura(message, texto):
    MAX_LEN = 4000
    if not texto: return
    if len(texto) <= MAX_LEN:
        bot.reply_to(message, texto)
    else:
        bot.reply_to(message, texto[:MAX_LEN])
        for i in range(MAX_LEN, len(texto), MAX_LEN):
            bot.send_message(message.chat.id, texto[i:i+MAX_LEN])

# --- NÚCLEO WEB: PUENTE DE COMUNICACIÓN PC ---
pc_ultima_conexion = 0
cola_comandos_pc = []

class CloudBridgeHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def do_GET(self):
        global pc_ultima_conexion, cola_comandos_pc
        if self.path == '/heartbeat':
            pc_ultima_conexion = time.time()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
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
            self.wfile.write(b"Klara Stark Network Protocol Online.")

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), CloudBridgeHandler)
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# --- MÓDULOS DE EXPANSIÓN ---
def buscar_en_internet(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
            if results:
                return "\n".join([f"[{r['title']}]({r['href']}): {r.get('body', '')}" for r in results])
    except Exception: pass
    return "Redes caídas. DuckDuckGo no responde en este momento."

def generar_imagen_ia(prompt, filename):
    prompt_encodeado = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encodeado}?nologo=true&width=1024&height=1024"
    r = requests.get(url)
    if r.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(r.content)
        return True
    return False

def generar_voz_neuronal(texto, archivo_salida):
    async def _generar():
        communicate = edge_tts.Communicate(texto, "es-MX-DaliaNeural")
        await communicate.save(archivo_salida)
    asyncio.run(_generar())

# --- MANEJADOR UNIFICADO ---
@bot.message_handler(content_types=['text', 'document', 'photo', 'voice'])
def manejar_mensajes(message):
    global pc_ultima_conexion, cola_comandos_pc
    chat_id = message.chat.id
    texto = message.text or message.caption or ""
    texto_lower = texto.lower()

    # Logica de procesamiento centralizada...
    # (El script completo integra la logica de PC, Vision, Voz y Memoria)

if __name__ == "__main__":
    init_db()
    bot.infinity_polling(non_stop=True)
