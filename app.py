from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from googletrans import Translator
import edge_tts
import asyncio
import os
import time
from datetime import datetime

app = Flask(__name__, template_folder='templates')
CORS(app)

# 初始化翻譯器
translator = Translator()

# 語音設置
VOICE_OPTIONS = {
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en": "en-US-JennyNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "th": "th-TH-PremwadeeNeural",
    "vi": "vi-VN-HoaiMyNeural"
}

@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        text = data.get('text')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')

        # 執行翻譯
        translation = translator.translate(text, src=source_lang, dest=target_lang)
        
        return jsonify({
            'success': True,
            'translated_text': translation.text,
            'source_lang': translation.src,
            'target_lang': translation.dest
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/speak', methods=['POST'])
async def speak():
    try:
        data = request.json
        text = data.get('text')
        lang = data.get('lang', 'en')
        
        # 獲取對應的語音
        voice = VOICE_OPTIONS.get(lang, VOICE_OPTIONS['en'])
        
        # 生成唯一的文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"temp/audio_{timestamp}.mp3"
        
        # 確保temp目錄存在
        os.makedirs('temp', exist_ok=True)
        
        # 生成語音
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)
        
        # 返回音頻文件的URL
        return jsonify({
            'success': True,
            'audio_url': f'/audio/{os.path.basename(filename)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('temp', filename)

# 添加根路由
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 