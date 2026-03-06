from fastapi import FastAPI, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import speech_recognition as sr
import uvicorn
import tempfile
import os
import aiohttp
import base64
import json
from pathlib import Path
import subprocess
import threading
import time
import requests
import socket

app = FastAPI(title="Dr TITI Chat Ai", description="Разработка Dr paradox")

# Добавляем CORS middleware для работы с ngrok
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ключ API
OPENROUTER_API_KEY = "API_OPENROUTER_API_KEY"

# Создаем директорию для статических файлов
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Функция для получения локального IP
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

# Функция для запуска ngrok
def start_ngrok(port=5000):
    try:
        result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ ngrok не установлен. Установите ngrok с https://ngrok.com/download")
            return None
        
        process = subprocess.Popen(
            ['ngrok', 'http', str(port), '--log=stdout'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(3)
        
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                for tunnel in tunnels:
                    if tunnel['proto'] == 'https':
                        public_url = tunnel['public_url']
                        print(f"✅ ngrok туннель создан: {public_url}")
                        return public_url
        except Exception as e:
            print(f"⚠️ Не удалось получить URL ngrok: {e}")
        
        return "http://localhost:4040 (проверьте веб-интерфейс ngrok)"
        
    except FileNotFoundError:
        print("❌ ngrok не найден. Установите ngrok с https://ngrok.com/download")
        return None
    except Exception as e:
        print(f"❌ Ошибка при запуске ngrok: {e}")
        return None

# Создаем CSS файл
css_content = """
:root {
    --bg-primary: #343541;
    --bg-secondary: #444654;
    --bg-user: #343541;
    --bg-ai: #444654;
    --text-primary: #ececf1;
    --text-secondary: #8e8ea0;
    --accent: #10a37f;
    --accent-hover: #1a7f64;
    --border: #4d4d4f;
    --shadow: 0 2px 6px rgba(0,0,0,0.3);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 1000px;
    margin: 0 auto;
    width: 100%;
    background: var(--bg-primary);
}

.chat-header {
    padding: 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-primary);
    text-align: center;
}

.chat-header h1 {
    font-size: 1.5rem;
    font-weight: 500;
    margin-bottom: 5px;
    color: var(--accent);
}

.chat-header p {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

.messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.message {
    display: flex;
    gap: 20px;
    padding: 20px;
    border-radius: 8px;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message.user {
    background: var(--bg-user);
}

.message.assistant {
    background: var(--bg-ai);
}

.message-avatar {
    width: 30px;
    height: 30px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}

.message-content {
    flex: 1;
    line-height: 1.6;
}

.message-content p {
    margin-bottom: 10px;
}

.message-time {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 5px;
}

.input-container {
    padding: 20px;
    background: var(--bg-primary);
    border-top: 1px solid var(--border);
}

.input-wrapper {
    display: flex;
    gap: 10px;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 10px;
    border: 1px solid var(--border);
}

textarea {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 1rem;
    padding: 10px;
    resize: none;
    max-height: 200px;
    outline: none;
    font-family: inherit;
}

textarea::placeholder {
    color: var(--text-secondary);
}

.button-group {
    display: flex;
    gap: 8px;
    align-items: flex-end;
}

.icon-button {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: 1.2rem;
    cursor: pointer;
    padding: 8px;
    border-radius: 8px;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.icon-button:hover {
    background: var(--bg-primary);
    color: var(--text-primary);
}

.icon-button.primary {
    background: var(--accent);
    color: white;
}

.icon-button.primary:hover {
    background: var(--accent-hover);
}

.icon-button.recording {
    background: #ef4444;
    color: white;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}

.file-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background: var(--bg-secondary);
    border-radius: 8px;
    margin-top: 10px;
    border: 1px solid var(--border);
}

.file-name {
    flex: 1;
    color: var(--text-primary);
    font-size: 0.9rem;
}

.typing-indicator {
    display: flex;
    gap: 5px;
    padding: 10px;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    background: var(--text-secondary);
    border-radius: 50%;
    animation: typing 1s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.6; }
    30% { transform: translateY(-10px); opacity: 1; }
}

.error-message {
    color: #ef4444;
    padding: 10px;
    background: rgba(239, 68, 68, 0.1);
    border-radius: 8px;
    margin-top: 10px;
}

.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--text-secondary);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
    .message {
        padding: 15px;
    }
    
    .input-wrapper {
        flex-direction: column;
    }
    
    .button-group {
        justify-content: flex-end;
    }
}
"""

with open(static_dir / "style.css", "w", encoding="utf-8") as f:
    f.write(css_content)

# HTML шаблон - без информации о подключении
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dr TITI AI Chat</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🤖 Dr TITI AI Chat</h1>
            <p>Разработка Dr paradox</p>
        </div>
        
        <div id="messages" class="messages-container">
            <!-- Сообщения будут добавляться сюда -->
        </div>
        
        <div class="input-container">
            <div class="input-wrapper">
                <textarea 
                    id="messageInput" 
                    placeholder="Отправьте сообщение... (Enter для отправки, Shift+Enter для новой строки)"
                    rows="1"
                ></textarea>
                <div class="button-group">
                    <button id="audioButton" class="icon-button" onclick="toggleRecording()" title="Голосовой ввод">
                        🎤
                    </button>
                    <button id="fileButton" class="icon-button" onclick="document.getElementById('fileInput').click()" title="Прикрепить аудиофайл">
                        📎
                    </button>
                    <button id="sendButton" class="icon-button primary" onclick="sendMessage()" title="Отправить (Enter)">
                        ➤
                    </button>
                </div>
            </div>
            <div id="fileInfo" class="file-info" style="display: none;">
                <span>📁</span>
                <span id="fileName" class="file-name"></span>
                <button class="icon-button" onclick="clearFile()" title="Удалить">✕</button>
            </div>
            <input type="file" id="fileInput" accept="audio/*" style="display: none;" onchange="handleFileSelect(event)">
        </div>
    </div>

    <script>
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const audioButton = document.getElementById('audioButton');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        
        let selectedFile = null;
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        
        // Автоматическое изменение высоты textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Отправка по Enter (без Shift)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Загрузка истории сообщений
        loadHistory();
        
        async function loadHistory() {
            try {
                const response = await fetch('/history');
                const messages = await response.json();
                messages.forEach(msg => addMessageToChat(msg.role, msg.content));
            } catch (error) {
                console.error('Error loading history:', error);
            }
        }
        
        function addMessageToChat(role, content, isTyping = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            
            const time = new Date().toLocaleTimeString('ru-RU', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    ${isTyping ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' : 
                      `<p>${content.replace(/\\n/g, '<br>')}</p>
                       <div class="message-time">${time}</div>`}
                </div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            return messageDiv;
        }
        
        async function sendMessage() {
            const text = messageInput.value.trim();
            
            if (!text && !selectedFile) {
                alert('Введите сообщение или выберите аудиофайл');
                return;
            }
            
            if (selectedFile) {
                await sendAudioFile(selectedFile);
            } else if (text) {
                await sendTextMessage(text);
            }
        }
        
        async function sendTextMessage(text) {
            // Добавляем сообщение пользователя
            addMessageToChat('user', text);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Показываем индикатор печати
            const typingMessage = addMessageToChat('assistant', '', true);
            
            try {
                const response = await fetch('/process_text', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                
                const data = await response.json();
                
                // Удаляем индикатор печати
                typingMessage.remove();
                
                // Добавляем ответ ассистента
                addMessageToChat('assistant', data.ai_response);
                
            } catch (error) {
                typingMessage.remove();
                addMessageToChat('assistant', '❌ Ошибка при обработке запроса');
                console.error('Error:', error);
            }
        }
        
        async function sendAudioFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            addMessageToChat('user', `🎤 Аудиосообщение: ${file.name}`);
            
            const typingMessage = addMessageToChat('assistant', '', true);
            
            try {
                const response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                typingMessage.remove();
                
                if (data.error) {
                    addMessageToChat('assistant', `❌ ${data.error}`);
                } else {
                    addMessageToChat('assistant', `📝 Распознано: "${data.text}"\\n\\n🤖 ${data.ai_response}`);
                }
                
            } catch (error) {
                typingMessage.remove();
                addMessageToChat('assistant', '❌ Ошибка при обработке аудио');
                console.error('Error:', error);
            }
            
            clearFile();
        }
        
        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                selectedFile = file;
                fileName.textContent = file.name;
                fileInfo.style.display = 'flex';
            }
        }
        
        function clearFile() {
            selectedFile = null;
            fileInput.value = '';
            fileInfo.style.display = 'none';
        }
        
        async function toggleRecording() {
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
                        
                        // Останавливаем все треки
                        stream.getTracks().forEach(track => track.stop());
                        
                        await sendAudioFile(audioFile);
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    audioButton.classList.add('recording');
                    audioButton.title = 'Остановить запись';
                    
                } catch (error) {
                    alert('Не удалось получить доступ к микрофону');
                    console.error('Error:', error);
                }
            } else {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
                isRecording = false;
                audioButton.classList.remove('recording');
                audioButton.title = 'Голосовой ввод';
            }
        }
        
        // Обработка перетаскивания файлов
        document.body.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            document.body.style.opacity = '0.8';
        });
        
        document.body.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            document.body.style.opacity = '1';
        });
        
        document.body.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            document.body.style.opacity = '1';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('audio/')) {
                selectedFile = files[0];
                fileName.textContent = files[0].name;
                fileInfo.style.display = 'flex';
            }
        });
    </script>
</body>
</html>
"""

# Получаем локальный IP
local_ip = get_local_ip()

# Запускаем ngrok в фоновом режиме
ngrok_url = None
try:
    ngrok_url = start_ngrok(5000)
except Exception as e:
    print(f"⚠️ Не удалось запустить ngrok: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/static/style.css")
async def get_css():
    return HTMLResponse(content=css_content, media_type="text/css")

# Хранилище истории сообщений
message_history = []

@app.post("/process_text")
async def process_text(request: Request):
    try:
        data = await request.json()
        user_text = data.get("text", "")
        
        # Сохраняем сообщение пользователя
        message_history.append({"role": "user", "content": user_text})
        
        ai_text = await get_ai_response(user_text)
        
        # Сохраняем ответ ассистента
        message_history.append({"role": "assistant", "content": ai_text})
        
        return {"user_text": user_text, "ai_response": ai_text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/process_audio")
async def process_audio(request: Request, file: UploadFile = File(...)):
    try:
        print(f"Получен аудиофайл: {file.filename}")
        
        # Сохраняем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        print(f"Файл сохранен: {tmp_path}")
        
        # Распознаем речь
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            # Настраиваем распознавание для лучшего качества
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio, language="ru-RU")
                print(f"Распознанный текст: {text}")
            except sr.UnknownValueError:
                os.remove(tmp_path)
                return {"error": "Не удалось распознать речь"}
            except sr.RequestError as e:
                os.remove(tmp_path)
                return {"error": f"Ошибка сервиса распознавания: {e}"}
        
        # Удаляем временный файл
        os.remove(tmp_path)
        
        # Сохраняем распознанный текст как сообщение пользователя
        message_history.append({"role": "user", "content": f"🎤 {text}"})
        
        # Получаем ответ от AI
        ai_text = await get_ai_response(text)
        
        # Сохраняем ответ ассистента
        message_history.append({"role": "assistant", "content": ai_text})
        
        return {"text": text, "ai_response": ai_text}
        
    except Exception as e:
        print(f"Ошибка при обработке аудио: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/history")
async def get_history():
    return message_history

@app.get("/ngrok_url")
async def get_ngrok_url():
    return {"ngrok_url": ngrok_url}

@app.get("/health")
async def health_check():
    return {"status": "ok", "ngrok_url": ngrok_url, "local_ip": local_ip}

async def get_ai_response(text: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": ngrok_url if ngrok_url else "http://localhost:5000",
        "X-Title": "Dr TITI AI Chat"
    }
    
    # Формируем контекст из истории
    messages = [
        {"role": "system", "content": "Ты дружелюбный AI ассистент по имени Dr TITI. Отвечай кратко, но информативно. Используй emoji для эмоциональной окраски."}
    ]
    
    # Добавляем последние 10 сообщений для контекста
    for msg in message_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    print(f"API Error: {resp.status} - {error_text}")
                    return f"❌ Извините, произошла ошибка при обращении к AI. Попробуйте позже."
    except Exception as e:
        print(f"Exception: {str(e)}")
        return "❌ Ошибка соединения с AI сервисом"

if __name__ == "__main__":
    # Определяем статус ngrok для вывода
    ngrok_status = ngrok_url if ngrok_url else "❌ Не удалось создать ngrok"
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              🚀 Dr TITI AI Chat запущен                      ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                              ║
    ║   📱 Локальный доступ:                                        ║
    ║   ► http://localhost:5000                                    ║
    ║   ► http://{}:5000                                   ║
    ║                                                              ║
    ║   🌐 Публичный доступ (ngrok):                                ║
    ║   ► {}║
    ║                                                              ║
    ║   🎤 Голосовой ввод поддерживается                           ║
    ║   📁 Drag & drop аудиофайлов                                 ║
    ║                                                              ║
    ║   ℹ️  Веб-интерфейс ngrok: http://localhost:4040             ║
    ║   🔍 Проверка статуса: http://localhost:5000/health          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """.format(local_ip, ngrok_status))
    

    uvicorn.run(app, host="0.0.0.0", port=5000)
