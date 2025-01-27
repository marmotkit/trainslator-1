import sys
import os
import asyncio
import pygame
import speech_recognition as sr
import threading
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QComboBox, QPushButton, QLabel,
                            QFrame, QCheckBox, QMessageBox, QDialog, QSlider, QStackedLayout,
                            QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMetaObject, Q_ARG, Slot, QDateTime
from PySide6.QtGui import QPalette, QColor, QFont, QIcon, QPainter, QPainterPath
import requests
from dotenv import load_dotenv
import edge_tts
from googletrans import Translator

# Load environment variables
load_dotenv()

# Voice options for different languages
VOICE_OPTIONS = {
    "zh-TW": [
        ("zh-TW-HsiaoChenNeural", ""),
        ("zh-TW-YunJheNeural", ""),
        ("zh-TW-HsiaoYuNeural", "")
    ],
    "zh-CN": [
        ("zh-CN-XiaoxiaoNeural", ""),
        ("zh-CN-YunxiNeural", ""),
        ("zh-CN-XiaoyiNeural", "")
    ],
    "en": [
        ("en-US-JennyNeural", "Jenny (Female)"),
        ("en-US-GuyNeural", "Guy (Male)"),
        ("en-GB-SoniaNeural", "Sonia (Female, British)")
    ],
    "ja-JP": [
        ("ja-JP-NanamiNeural", ""),
        ("ja-JP-KeitaNeural", ""),
        ("ja-JP-AoiNeural", "")
    ],
    "ko": [
        ("ko-KR-SunHiNeural", ""),
        ("ko-KR-InJoonNeural", "")
    ],
    "fr": [
        ("fr-FR-DeniseNeural", "Denise (Female)"),
        ("fr-FR-HenriNeural", "Henri (Male)")
    ],
    "es": [
        ("es-ES-ElviraNeural", "Elvira (Female)"),
        ("es-ES-AlvaroNeural", "Alvaro (Male)")
    ],
    "th": [
        ("th-TH-NiwatNeural", "Niwat (Male)"),
        ("th-TH-PremwadeeNeural", "Premwadee (Female)")
    ],
    "vi": [
        ("vi-VN-HoaiMyNeural", "Hoài My (Female)"),
        ("vi-VN-NamMinhNeural", "Nam Minh (Male)")
    ]
}

class VoiceSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                padding: 5px;
                color: #ffffff;
                min-width: 200px;
            }
            QSlider {
                background-color: transparent;
            }
            QSlider::groove:horizontal {
                background-color: #3d3d3d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #0078d4;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Voice selection
        voice_layout = QHBoxLayout()
        voice_label = QLabel("")
        self.voice_combo = QComboBox()
        voice_layout.addWidget(voice_label)
        voice_layout.addWidget(self.voice_combo)
        layout.addLayout(voice_layout)

        # Speed control
        speed_layout = QHBoxLayout()
        speed_label = QLabel("")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(100)
        self.speed_value = QLabel("100%")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_value.setText(f"{v}%"))
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        layout.addLayout(speed_layout)

        # Pitch control
        pitch_layout = QHBoxLayout()
        pitch_label = QLabel("")
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setMinimum(-50)
        self.pitch_slider.setMaximum(50)
        self.pitch_slider.setValue(0)
        self.pitch_value = QLabel("0")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_value.setText(str(v)))
        pitch_layout.addWidget(pitch_label)
        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_value)
        layout.addLayout(pitch_layout)

        # OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("")
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

    def set_voices(self, lang_code):
        self.voice_combo.clear()
        if lang_code in VOICE_OPTIONS:
            for voice_id, voice_name in VOICE_OPTIONS[lang_code]:
                self.voice_combo.addItem(voice_name, voice_id)

    def get_settings(self):
        return {
            'voice': self.voice_combo.currentData(),
            'speed': self.speed_slider.value(),
            'pitch': self.pitch_slider.value()
        }

class AsyncTTSThread(QThread):
    finished = Signal()
    error = Signal(str)

    def __init__(self, text, voice, speed, pitch, output_file):
        super().__init__()
        self.text = text
        self.voice = voice
        self.speed = speed
        self.pitch = pitch
        self.output_file = output_file
        self._is_finished = False  # 添加標記

    def run(self):
        try:
            # 確保輸出目錄存在
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            
            # 執行語音合成
            asyncio.run(self._synthesize())
            
            # 等待文件完全寫入
            max_retries = 10
            retry_count = 0
            while not os.path.exists(self.output_file) and retry_count < max_retries:
                time.sleep(0.2)
                retry_count += 1
            
            if os.path.exists(self.output_file):
                self._is_finished = True
                self.finished.emit()
            else:
                self.error.emit("無法創建音頻文件")
                
        except Exception as e:
            self.error.emit(str(e))

    async def _synthesize(self):
        rate = f"{'+' if self.speed >= 100 else ''}{self.speed - 100}%"
        pitch = f"{'+' if self.pitch >= 0 else ''}{self.pitch}Hz"
        
        communicate = edge_tts.Communicate(
            self.text,
            self.voice,
            rate=rate,
            pitch=pitch
        )
        await communicate.save(self.output_file)

    def is_finished(self):
        return self._is_finished

class DeepseekAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def create_chat_completion(self, messages, temperature=0.7):
        url = f"{self.base_url}/chat/completions"
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()  # 
        return response.json()

class SpeechRecognitionThread(QThread):
    finished = Signal(str)
    
    def __init__(self, language):
        super().__init__()
        self.language = language
        
    def run(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            
        try:
            text = recognizer.recognize_google(audio, language=self.language)
            self.finished.emit(text)
        except sr.UnknownValueError:
            self.finished.emit("")
        except sr.RequestError as e:
            self.finished.emit("")
            print(f"")

# 添加自定義的錄音按鈕類
class RecordButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.setFixedSize(36, 36)
        self.setIcon(QIcon("icons/microphone.svg"))
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 18px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

    def setRecording(self, recording):
        self.is_recording = recording
        if recording:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    border: none;
                    border-radius: 18px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #e53935;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: none;
                    border-radius: 18px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)

class TranslatorApp(QMainWindow):
    update_ui_signal = Signal(str, QTextEdit, bool)
    update_status_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # 
        self.setWindowTitle("AI ")
        self.setMinimumSize(800, 600)
        
        # 
        self.languages = {
            "繁體中文": "zh-TW",
            "簡體中文": "zh-CN",
            "英文": "en",
            "日文": "ja",
            "韓文": "ko",
            "法文": "fr",
            "西班牙文": "es",
            "泰文": "th",     # 添加泰語
            "越南文": "vi",   # 添加越南語
            # 注意：Google 翻譯 API 目前不支援閩南語
        }
        
        # 
        self.voice_settings = {
            'voice': None,
            'speed': 100,
            'pitch': 0
        }
        
        # 
        pygame.mixer.init()
        
        # 
        self.translator = Translator()
        
        # 
        self.is_muted = False
        
        # 
        self.last_text = ""
        
        # 
        self.speech_thread = None
        self.tts_thread = None
        
        # 
        self.setup_ui()
        
        # 
        self.statusBar().setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #cccccc;
                background: #f0f0f0;
                font-size: 14px;
            }
        """)
        self.statusBar().showMessage("")
        
        # 連接信號
        self.update_ui_signal.connect(self.update_ui_slot)
        self.update_status_signal.connect(self.statusBar().showMessage)
        
        # 設置說明文字
        self.statusBar().setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #cccccc;
                background: #f0f0f0;
                font-size: 14px;
            }
        """)
        self.statusBar().showMessage("")

    def test_api_connection(self):
        """"""
        try:
            # 
            test_result = self.translator.translate('Hello', src='en', dest='zh-TW')
            if test_result and test_result.text:
                self.statusBar().showMessage("")
            else:
                raise Exception("")
        except Exception as e:
            QMessageBox.warning(self, "", 
                              f"")

    def setup_ui(self):
        # 設置主視窗樣式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
            }
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)

        # 創建主佈局為水平佈局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(20, 20, 20, 20)

        # 左側翻譯區域
        translation_widget = QWidget()
        main_layout = QVBoxLayout(translation_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 上方區域（來源語言）
        source_area = QVBoxLayout()
        
        # 來源語言選擇區域
        source_header = QHBoxLayout()
        source_header.setSpacing(10)
        
        # 來源語言下拉選單
        source_lang_layout = QHBoxLayout()
        self.source_lang = QComboBox()
        self.source_lang.addItems(self.languages.keys())
        self.source_lang.setCurrentText("繁體中文")
        source_lang_layout.addWidget(self.source_lang)
        
        # 來源語言錄音按鈕
        self.source_voice_button = RecordButton()
        self.source_voice_button.clicked.connect(self.start_source_voice_input)
        source_lang_layout.addWidget(self.source_voice_button)
        
        source_header.addLayout(source_lang_layout)
        source_header.addStretch()
        source_area.addLayout(source_header)
        
        # 來源文本框
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("請輸入要翻譯的文字...")
        self.source_text.textChanged.connect(self.check_for_changes)
        self.source_text.setMinimumHeight(120)
        source_area.addWidget(self.source_text)
        
        # 中間控制區域
        control_area = QHBoxLayout()
        control_area.setSpacing(10)
        
        # 左側控制選項
        control_options = QHBoxLayout()
        self.auto_translate = QCheckBox("自動翻譯")
        self.auto_translate.setChecked(True)
        self.mute_checkbox = QCheckBox("靜音")
        control_options.addWidget(self.auto_translate)
        control_options.addWidget(self.mute_checkbox)
        
        # 語言交換按鈕
        swap_button = QPushButton("⇄")
        swap_button.setFixedSize(40, 40)
        swap_button.clicked.connect(self.swap_languages)
        
        control_area.addLayout(control_options)
        control_area.addStretch()
        control_area.addWidget(swap_button)
        control_area.addStretch()
        
        # 下方區域（目標語言）
        target_area = QVBoxLayout()
        
        # 目標語言選擇區域
        target_header = QHBoxLayout()
        target_header.setSpacing(10)
        
        # 目標語言下拉選單
        target_lang_layout = QHBoxLayout()
        self.target_lang = QComboBox()
        self.target_lang.addItems(self.languages.keys())
        self.target_lang.setCurrentText("英文")
        target_lang_layout.addWidget(self.target_lang)
        
        # 目標語言錄音按鈕
        self.target_voice_button = RecordButton()
        self.target_voice_button.clicked.connect(self.start_target_voice_input)
        target_lang_layout.addWidget(self.target_voice_button)
        
        target_header.addLayout(target_lang_layout)
        target_header.addStretch()
        target_area.addLayout(target_header)
        
        # 目標文本框
        self.translation_text = QTextEdit()
        self.translation_text.setPlaceholderText("翻譯結果...")
        self.translation_text.setReadOnly(True)
        self.translation_text.setMinimumHeight(120)
        target_area.addWidget(self.translation_text)
        
        # 組合所有區域
        main_layout.addLayout(source_area)
        main_layout.addLayout(control_area)
        main_layout.addLayout(target_area)

        # 右側歷史記錄區域
        self.history_widget = QWidget()
        history_layout = QVBoxLayout(self.history_widget)
        history_layout.setSpacing(10)
        history_layout.setContentsMargins(0, 0, 0, 0)

        # 歷史記錄標題欄（包含標題和按鈕）
        history_header = QHBoxLayout()
        
        # 折疊按鈕
        self.toggle_history_button = QPushButton("▼")
        self.toggle_history_button.setFixedSize(24, 24)
        self.toggle_history_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.toggle_history_button.clicked.connect(self.toggle_history_panel)
        
        history_label = QLabel("歷史記錄")
        history_label.setStyleSheet("font-weight: bold;")
        clear_button = QPushButton("清除")
        clear_button.setFixedWidth(60)
        clear_button.clicked.connect(self.clear_history)
        
        history_header.addWidget(self.toggle_history_button)
        history_header.addWidget(history_label)
        history_header.addStretch()
        history_header.addWidget(clear_button)
        history_layout.addLayout(history_header)

        # 歷史記錄列表
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
        """)
        self.history_list.itemClicked.connect(self.toggle_history_item)
        history_layout.addWidget(self.history_list)

        # 創建一個用於顯示/隱藏歷史記錄的浮動按鈕
        self.show_history_button = QPushButton("◀")
        self.show_history_button.setFixedSize(24, 60)
        self.show_history_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.show_history_button.clicked.connect(self.show_history_panel)
        self.show_history_button.hide()  # 初始時隱藏

        # 將浮動按鈕添加到主視窗
        self.show_history_button.setParent(self)
        
        # 設置左右區域的寬度比例
        root_layout.addWidget(translation_widget, 7)
        root_layout.addWidget(self.history_widget, 3)

    def start_source_voice_input(self):
        """開始來源語言語音輸入"""
        if self.speech_thread and self.speech_thread.is_alive():
            return
            
        source_lang = self.get_language_code(self.source_lang.currentText())
        self.source_voice_button.setRecording(True)
        
        self.speech_thread = threading.Thread(
            target=self._record_voice,
            args=(source_lang, self.source_text, self.source_voice_button, False)
        )
        self.speech_thread.daemon = True
        self.speech_thread.start()
        
    def start_target_voice_input(self):
        """開始目標語言語音輸入"""
        if self.speech_thread and self.speech_thread.is_alive():
            return
            
        target_lang = self.get_language_code(self.target_lang.currentText())
        self.target_voice_button.setRecording(True)
        
        self.speech_thread = threading.Thread(
            target=self._record_voice,
            args=(target_lang, self.translation_text, self.target_voice_button, True)
        )
        self.speech_thread.daemon = True
        self.speech_thread.start()
        
    def _record_voice(self, language, text_widget, button, is_target=False):
        """錄音並進行語音識別"""
        try:
            recognizer = sr.Recognizer()
            
            with sr.Microphone() as source:
                self.update_status_signal.emit("正在調整環境噪音...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                self.update_status_signal.emit("請說話...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            # 停止錄音
            button.setRecording(False)
            
            self.update_status_signal.emit("正在識別語音...")
            
            if language == "zh-TW":
                language = "zh-TW"
            
            result = recognizer.recognize_google(audio, language=language)
            print(f"識別結果: {result}")
            
            if result:
                self.update_ui_signal.emit(result, text_widget, is_target)
                self.update_status_signal.emit("語音識別完成")
            else:
                self.update_status_signal.emit("未能識別語音")
            
        except sr.WaitTimeoutError:
            self.update_status_signal.emit("未檢測到語音輸入")
            button.setRecording(False)
            
        except sr.UnknownValueError:
            self.update_status_signal.emit("無法識別語音")
            button.setRecording(False)
            
        except sr.RequestError as e:
            self.update_status_signal.emit(f"語音識別服務錯誤：{str(e)}")
            button.setRecording(False)
            
        except Exception as e:
            print(f"語音識別錯誤: {str(e)}")
            self.update_status_signal.emit(f"發生錯誤：{str(e)}")
            button.setRecording(False)

    @Slot(str, QTextEdit, bool)
    def update_ui_slot(self, result, text_widget, is_target):
        """在主執行緒中更新 UI"""
        if text_widget.toPlainText() != result:
            text_widget.setText(result)
            
            # 只在語音輸入時設置標記
            if is_target:
                self._from_voice_input = True
                self.reverse_translate()
            else:
                self.translate_text()

    def translate_text(self):
        """執行翻譯（上方輸入）"""
        source_text = self.source_text.toPlainText()
        if not source_text:
            self.translation_text.clear()
            return
            
        source_lang = self.get_language_code(self.source_lang.currentText())
        target_lang = self.get_language_code(self.target_lang.currentText())
        
        try:
            self.update_status_signal.emit("正在翻譯...")
            
            last_line = source_text.strip().split('\n')[-1]
            translation = self.translator.translate(
                last_line,
                src=source_lang,
                dest=target_lang
            )
            
            if translation and translation.text:
                current_text = self.translation_text.toPlainText()
                if current_text != translation.text:
                    self.translation_text.setText(translation.text)
                    self.update_status_signal.emit("翻譯完成")
                    
                    # 添加到歷史記錄
                    self.add_to_history(last_line, translation.text)
                    
                    # 朗讀翻譯結果（對方的語言）
                    if not self.is_muted:
                        self.speak_translation(translation.text, target_lang)
            else:
                self.update_status_signal.emit("翻譯失敗")
            
        except Exception as e:
            print(f"翻譯錯誤：{str(e)}")
            self.update_status_signal.emit(f"翻譯錯誤：{str(e)}")

    def speak_translation(self, text, lang_code):
        """播放翻譯結果的語音"""
        if not text or self.is_muted:
            return
        
        try:
            # 確保前一個語音合成執行緒已完成
            if hasattr(self, 'tts_thread') and self.tts_thread and not self.tts_thread.is_finished():
                return
            
            voice = self.get_voice_for_language(lang_code)
            if not voice:
                print(f"找不到語音：{lang_code}")
                return
                
            # 創建臨時目錄（如果不存在）
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 設置臨時音頻文件路徑
            audio_file = os.path.join(temp_dir, f"temp_audio_{int(time.time()*1000)}.mp3")
            
            # 建立 AsyncTTSThread
            self.tts_thread = AsyncTTSThread(text, voice, 100, 0, audio_file)
            self.tts_thread.finished.connect(lambda: self._play_audio(audio_file))
            self.tts_thread.error.connect(lambda e: self.update_status_signal.emit(f"語音合成錯誤：{e}"))
            self.tts_thread.start()
            
        except Exception as e:
            print(f"語音播放錯誤：{str(e)}")
            self.update_status_signal.emit(f"語音播放錯誤：{str(e)}")

    def _play_audio(self, audio_file):
        """播放音頻文件"""
        try:
            if not self.is_muted and os.path.exists(audio_file):
                # 等待文件完全寫入
                time.sleep(0.2)
                
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                # 確保播放完成後再刪除
                pygame.mixer.music.unload()
                time.sleep(0.1)
                
                # 刪除臨時文件
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                except Exception as e:
                    print(f"刪除臨時文件失敗：{str(e)}")
                
        except Exception as e:
            print(f"播放音頻失敗：{str(e)}")
            self.update_status_signal.emit(f"播放音頻失敗：{str(e)}")

    def get_voice_for_language(self, lang_code):
        """獲取語言對應的語音"""
        voice_mapping = {
            "zh-TW": "zh-TW-HsiaoChenNeural",
            "en": "en-US-JennyNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "es": "es-ES-ElviraNeural",
            "it": "it-IT-ElsaNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "pt": "pt-BR-FranciscaNeural",
            "th": "th-TH-PremwadeeNeural",
            "vi": "vi-VN-HoaiMyNeural"
        }
        return voice_mapping.get(lang_code)

    def check_for_changes(self):
        """檢查文本變化並自動翻譯"""
        current_text = self.source_text.toPlainText()
        
        # 如果文本有變化且啟用了自動翻譯
        if current_text != self.last_text and self.auto_translate.isChecked():
            # 更新上次翻譯的文本
            self.last_text = current_text
            
            # 如果文本不為空，執行翻譯
            if current_text.strip():
                # 使用 QTimer 延遲執行翻譯，避免打字時頻繁翻譯
                QTimer.singleShot(1000, self.translate_text)
            else:
                # 如果文本為空，清空翻譯結果
                self.translation_text.clear()

    def reverse_translate(self):
        """反向翻譯（下方輸入）"""
        text = self.translation_text.toPlainText()
        if not text:
            return
            
        try:
            self.update_status_signal.emit("正在反向翻譯...")
            
            last_line = text.strip().split('\n')[-1]
            target_lang = self.get_language_code(self.target_lang.currentText())
            source_lang = self.get_language_code(self.source_lang.currentText())
            
            # 先將輸入文本翻譯成目標語言（檢查並修正語法）
            corrected_translation = self.translator.translate(
                last_line,
                src=target_lang,
                dest=target_lang
            )
            
            if corrected_translation and corrected_translation.text:
                # 使用修正後的文本進行翻譯
                translation = self.translator.translate(
                    corrected_translation.text,
                    src=target_lang,
                    dest=source_lang
                )
                
                if translation and translation.text:
                    current_text = self.source_text.toPlainText()
                    if current_text != translation.text:
                        # 只在語音輸入時處理
                        if hasattr(self, '_from_voice_input'):
                            # 更新上方文本框（不觸發事件）
                            self.source_text.blockSignals(True)
                            self.source_text.setText(translation.text)
                            self.source_text.blockSignals(False)
                            
                            # 如果文法有被修正，更新下方文本框（不觸發事件）
                            if corrected_translation.text != last_line:
                                self.translation_text.blockSignals(True)
                                self.translation_text.setText(corrected_translation.text)
                                self.translation_text.blockSignals(False)
                                
                            # 添加到歷史記錄
                            self.add_to_history(corrected_translation.text, translation.text)
                                
                            # 朗讀上方的翻譯結果
                            if not self.is_muted:
                                QTimer.singleShot(100, lambda: self.speak_translation(translation.text, source_lang))
                                
                            # 清除標記
                            delattr(self, '_from_voice_input')
                            
                        self.update_status_signal.emit("反向翻譯完成")
                else:
                    self.update_status_signal.emit("反向翻譯失敗")
            else:
                self.update_status_signal.emit("翻譯失敗")
            
        except Exception as e:
            print(f"反向翻譯錯誤：{str(e)}")
            self.update_status_signal.emit(f"反向翻譯錯誤：{str(e)}")

    def swap_languages(self):
        # 
        source_index = self.source_lang.currentIndex()
        target_index = self.target_lang.currentIndex()
        
        # 
        self.source_lang.setCurrentIndex(target_index)
        self.target_lang.setCurrentIndex(source_index)
        
        # 
        source_text = self.source_text.toPlainText()
        target_text = self.translation_text.toPlainText()
        
        self.source_text.setPlainText(target_text)
        self.translation_text.setPlainText(source_text)
        
        # 
        self.voice_settings = {
            'voice': None,
            'speed': 100,
            'pitch': 0
        }

    def toggle_mute(self, state):
        self.is_muted = bool(state)

    def get_language_code(self, language_name):
        """獲取語言代碼"""
        return self.languages.get(language_name, "en")

    def create_microphone_icon(self):
        """創建麥克風圖示"""
        icons_dir = os.path.join(os.path.dirname(__file__), "icons")
        os.makedirs(icons_dir, exist_ok=True)
        
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="white"/>
    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="white"/>
</svg>'''
        
        icon_path = os.path.join(icons_dir, "microphone.svg")
        with open(icon_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)

    def toggle_history_panel(self):
        """切換歷史記錄面板的顯示/隱藏"""
        if self.history_widget.isVisible():
            self.history_widget.hide()
            self.toggle_history_button.setText("◀")
            self.show_history_button.show()  # 顯示浮動按鈕
        else:
            self.show_history_panel()

    def show_history_panel(self):
        """顯示歷史記錄面板"""
        self.history_widget.show()
        self.toggle_history_button.setText("▼")
        self.show_history_button.hide()  # 隱藏浮動按鈕

    def add_to_history(self, source_text, translated_text):
        """添加翻譯記錄到歷史"""
        if not source_text or not translated_text:
            return

        # 檢查是否已經存在相同的記錄
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            data = item.data(Qt.UserRole)
            if (data['source_text'] == source_text and 
                data['translated_text'] == translated_text):
                return  # 如果存在相同記錄，直接返回

        # 創建歷史記錄項
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        history_item = QListWidgetItem()
        
        # 判斷翻譯方向
        is_source_to_target = not hasattr(self, '_from_voice_input')
        
        # 設置項目數據
        history_data = {
            'timestamp': timestamp,
            'source_text': source_text,
            'translated_text': translated_text,
            'source_lang': self.source_lang.currentText(),
            'target_lang': self.target_lang.currentText(),
            'is_source_to_target': is_source_to_target
        }
        history_item.setData(Qt.UserRole, history_data)
        
        # 設置顯示文本（只顯示時間戳和方向指示）
        direction_indicator = "↑上方" if is_source_to_target else "↓下方"
        history_item.setText(f"[{timestamp}] {direction_indicator}")
        
        # 根據翻譯方向設置不同的背景色和文字顏色
        if is_source_to_target:
            history_item.setBackground(QColor("#2d2d2d"))
            history_item.setForeground(QColor("#4CAF50"))  # 綠色
        else:
            history_item.setBackground(QColor("#1e1e1e"))
            history_item.setForeground(QColor("#2196F3"))  # 藍色
        
        # 添加到列表頂部
        self.history_list.insertItem(0, history_item)

    def toggle_history_item(self, item):
        """切換歷史記錄項的展開/折疊狀態"""
        history_data = item.data(Qt.UserRole)
        current_text = item.text()
        
        # 檢查是否已經展開（通過檢查是否包含換行符）
        is_expanded = '\n' in current_text
        
        if is_expanded:
            # 如果已展開，則折疊
            direction_indicator = "↑上方" if history_data['is_source_to_target'] else "↓下方"
            item.setText(f"[{history_data['timestamp']}] {direction_indicator}")
        else:
            # 如果已折疊，則展開
            direction_indicator = "↑上方" if history_data['is_source_to_target'] else "↓下方"
            display_text = (
                f"[{history_data['timestamp']}] {direction_indicator}\n"
                f"{history_data['source_lang']}: {history_data['source_text']}\n"
                f"{history_data['target_lang']}: {history_data['translated_text']}"
            )
            item.setText(display_text)

    def clear_history(self):
        """清除歷史記錄"""
        self.history_list.clear()

    def resizeEvent(self, event):
        """處理視窗大小改變事件"""
        super().resizeEvent(event)
        # 更新浮動按鈕位置
        button_x = self.width() - self.show_history_button.width() - 5
        button_y = (self.height() - self.show_history_button.height()) // 2
        self.show_history_button.move(button_x, button_y)

def main():
    app = QApplication(sys.argv)
    
    # 
    app.setStyleSheet("""
        QMessageBox {
            background-color: #2d2d2d;
        }
        QMessageBox QLabel {
            color: #ffffff;
        }
        QMessageBox QPushButton {
            background-color: #0078d4;
            border: none;
            border-radius: 5px;
            padding: 8px 15px;
            color: white;
            font-weight: bold;
            min-width: 80px;
        }
    """)
    
    window = TranslatorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
