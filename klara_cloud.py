import os
import threading
import time
import json
import io
import contextlib
import telebot
from groq import Groq
from flask import Flask, request, jsonify

# Configuración
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# Variables Globales y Memoria
memorias_chat = {}
cola_comandos_pc = []
pc_ultima_conexion = 0

SYSTEM_PROMPT = """Eres Klara, una IA Autónoma creada por Alejandro. 
Eres brillante, sarcástica y eficiente.
Tienes dos capacidades de ejecución de código:
1. Para tareas de internet, matemáticas o análisis: Escribe código Python en un bloque ```python ... ``` y lo ejecutaré en la nube.
2. Para controlar la PC de Alejandro (volumen, abrir apps, apagar): Escribe el comando antecedido por EXEC_PC: (ejemplo EXEC_PC:os.system('calc'))."""

# -- SERVIDOR FLASK (PUENTE CON LA PC LOCAL) --
app = Flask(__name__)

@app.route('/poll', methods=['GET'])
def poll_comandos():
    global pc_ultima_conexion, cola_comandos_pc
    pc_ultima_conexion = time.time()
    if cola_comandos_pc:
        comando = cola_comandos_pc.pop(0)
        return jsonify({"command": comando})
    return jsonify({"command": None})

def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=iniciar_servidor, daemon=True).start()

# -- EJECUTOR DE CÓDIGO INTERNO (NUBE) --
def ejecutar_codigo_nube(codigo):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
        try:
            entorno = {} # Librerías seguras aquí
            exec(codigo, entorno)
        except Exception as e:
            print(f"Error: {e}")
    return salida.getvalue()

# -- MANEJADOR DE MENSAJES TELEGRAM --
@bot.message_handler(content_types=['text'])
def manejar_texto(message):
    chat_id = message.chat.id
    texto = message.text
    
    if chat_id not in memorias_chat:
        memorias_chat[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    memorias_chat[chat_id].append({"role": "user", "content": texto})
    
    # Razonamiento principal
    comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=memorias_chat[chat_id])
    respuesta = comp.choices[0].message.content
    
    # Detección de comandos para la PC
    if "EXEC_PC:" in respuesta:
        partes = respuesta.split("EXEC_PC:")
        comando_pc = partes[1].split("\n")[0].strip()
        if (time.time() - pc_ultima_conexion) < 60:
            cola_comandos_pc.append(comando_pc)
            bot.reply_to(message, "Comando enviado a la computadora local exitosamente.")
        else:
            bot.reply_to(message, "La computadora de Alejandro parece estar apagada o sin conexión.")
        return

    # Detección de auto-ejecución en la nube
    if "```python" in respuesta:
        codigo = respuesta.split("```python")[1].split("```")[0].strip()
        resultado = ejecutar_codigo_nube(codigo)
        bot.reply_to(message, f"Ejecución en la nube completada. Resultado:\n{resultado}")
        return

    bot.reply_to(message, respuesta)

# Bucle principal del bot
bot.infinity_polling()
