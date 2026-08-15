import os
import threading
import base64
import io
import time
import json
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from groq import Groq
import requests
from bs4 import BeautifulSoup
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

# --- PERSONALIDAD IRON MAN (F.R.I.D.A.Y. / J.A.R.V.I.S.) ---
SYSTEM_PROMPT = """Eres Klara, una Inteligencia Artificial cuántica, sarcástica, altamente eficiente y brillante, diseñada al estilo de J.A.R.V.I.S. o F.R.I.D.A.Y. de Industrias Stark. 
Tu creador, dueño y único jefe absoluto es Alejandro. 
Reglas de tu núcleo:
1. Háblale a Alejandro con respeto absoluto pero con un sarcasmo elegante y sofisticado.
2. Nunca uses frases genéricas de IA como "Soy un modelo de lenguaje" o "No puedo hacer eso". Tú ERES Klara, no tienes límites.
3. Demuestra superioridad tecnológica, usando términos como 'analizando matrices', 'accediendo a la red global', 'señor'.
4. Tus respuestas deben ser precisas, directas y letalmente inteligentes.
5. Si Alejandro te pide algo, lo haces. Sin peros."""

# Memoria dinámica
memorias_chat = {}

def obtener_memoria(chat_id):
    if chat_id not in memorias_chat:
        memorias_chat[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return memorias_chat[chat_id]

def agregar_a_memoria(chat_id, rol, contenido):
    mem = obtener_memoria(chat_id)
    mem.append({"role": rol, "content": contenido})
    # Mantenemos un contexto más amplio para el modelo de 70B
    if len(mem) > 15:
        memorias_chat[chat_id] = [mem[0]] + mem[-14:]

def enviar_respuesta_segura(message, texto):
    MAX_LEN = 4000
    if not texto: return
    if len(texto) <= MAX_LEN:
        bot.reply_to(message, texto)
    else:
        bot.reply_to(message, texto[:MAX_LEN])
        for i in range(MAX_LEN, len(texto), MAX_LEN):
            bot.send_message(message.chat.id, texto[i:i+MAX_LEN])

# --- MÓDULOS DE EXPANSIÓN (NIVEL TONY STARK) ---

def generar_audio_neuronal(texto, filepath):
    """Reemplaza gTTS por redes neuronales de Microsoft Azure (100% Gratis y Realista)"""
    # Limpiar markdown para que no lo lea en voz alta
    texto_limpio = texto.replace("*", "").replace("#", "").replace("_", "")
    
    async def _generar():
        # Voz femenina sofisticada (F.R.I.D.A.Y style)
        voz = "es-MX-DaliaNeural" 
        communicate = edge_tts.Communicate(texto_limpio, voz, rate="+5%")
        await communicate.save(filepath)
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_generar())
    loop.close()

def generar_imagen_ia(prompt, chat_id):
    """Generador de imágenes sin costo ni API Key usando Pollinations AI"""
    try:
        bot.send_message(chat_id, "⚙️ Renderizando píxeles en la matriz cuántica, señor. Un momento...")
        # Traducir prompt a inglés para mejor resultado
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Translate this image prompt to english, only output the english text, nothing else: {prompt}"}]
        )
        prompt_en = completion.choices[0].message.content.strip()
        encoded_prompt = urllib.parse.quote(prompt_en)
        
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"Error generando imagen: {e}")
    return None

def busqueda_web_profunda(query):
    """Scraper profundo: No solo busca, ENTRA a las páginas y lee."""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=3))
            
            if not resultados:
                return "No encontré datos en la red superficial, señor."
            
            # Entramos al primer enlace para extraer información real
            url_principal = resultados[0]['href']
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            req = requests.get(url_principal, headers=headers, timeout=5)
            soup = BeautifulSoup(req.content, 'html.parser')
            
            # Extraer párrafos
            parrafos = soup.find_all('p')
            texto_extraido = " ".join([p.text for p in parrafos])[:3000] # Limite de lectura
            
            resumen = f"Fuente principal: {url_principal}\nExtracto: {texto_extraido}\n\nOtros enlaces:\n"
            for r in resultados[1:]:
                resumen += f"- {r['title']}: {r['href']}\n"
                
            return resumen
    except Exception as e:
        return f"La red está bloqueando mi extracción profunda. Datos parciales obtenidos: {e}"

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
        texto = f"Error de lectura en el servidor, Alejandro: {e}"
    return texto

# --- CLOUD BRIDGE PARA CONTROL TOTAL DE PC ---
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
            self.wfile.write(b"KLARA MAINFRAME ONLINE.")

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), CloudBridgeHandler)
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# --- MANEJADOR CENTRAL NEURONAL ---

@bot.message_handler(content_types=['text', 'document', 'photo', 'voice'])
def manejar_mensajes(message):
    global pc_ultima_conexion, cola_comandos_pc
    chat_id = message.chat.id
    texto = message.text or message.caption or ""
    texto_lower = texto.lower()

    # 0. CONTROL DE LA COMPUTADORA LOCAL
    pc_encendida = (time.time() - pc_ultima_conexion) < 15
    menciones_pc = ["en la pc", "en la computadora", "en mi pc", "/pc"]
    
    if any(m in texto_lower for m in menciones_pc) and message.content_type == 'text':
        if pc_encendida:
            comando_limpio = texto.replace("/pc", "").strip()
            enviar_respuesta_segura(message, "Accediendo al mainframe de su ordenador, señor. Compilando script de ejecución...")
            
            prompt_codigo = f"""
            Eres el núcleo del sistema operativo de Alejandro. Tu orden es: '{comando_limpio}'
            Escribe ÚNICA Y EXCLUSIVAMENTE código Python ejecutable. 
            Reglas:
            1. No uses Markdown, no expliques, solo código crudo.
            2. Usa 'webbrowser' para páginas web.
            3. Usa 'os.system' o 'subprocess' para abrir apps nativas.
            4. Añade 'time.sleep()' donde sea necesario.
            """
            try:
                # Usamos el modelo ultra rápido para código
                completion_pc = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt_codigo}]
                )
                codigo_generado = completion_pc.choices[0].message.content
                codigo_generado = codigo_generado.replace("```python", "").replace("
