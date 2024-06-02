import sys
import threading
import queue
import pyaudio
import numpy as np
import logging
import json
from scipy.signal import butter, lfilter
import azure.cognitiveservices.speech as speechsdk
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QComboBox, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'config.json'

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def normalize_audio(audio_data):
    max_val = np.max(np.abs(audio_data))
    return audio_data / max_val if max_val != 0 else audio_data

class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.running = False
        self.audio_queue = queue.Queue()
        self.load_config()

    def initUI(self):
        self.setWindowTitle('Real-Time Translator')
        self.setGeometry(100, 100, 800, 600)
        
        self.label = QLabel('Translation will appear here', self)
        self.label.setWordWrap(True)
        
        self.start_button = QPushButton('Start Translation', self)
        self.start_button.clicked.connect(self.start_translation)
        
        self.stop_button = QPushButton('Stop Translation', self)
        self.stop_button.clicked.connect(self.stop_translation)

        self.status_label = QLabel('Status: Stopped', self)
        
        self.input_language_label = QLabel('Input Language:', self)
        self.input_language = QLineEdit(self)
        self.input_language.setPlaceholderText('en-US')
        self.input_language.setToolTip('Enter the language code for the input language (e.g., en-US for English)')
        
        self.output_language_label = QLabel('Output Language:', self)
        self.output_language = QLineEdit(self)
        self.output_language.setPlaceholderText('es-ES')
        self.output_language.setToolTip('Enter the language code for the output language (e.g., es-ES for Spanish)')
        
        self.audio_device_label = QLabel('Audio Device:', self)
        self.audio_device_combo = QComboBox(self)
        self.populate_audio_devices()
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_language_label)
        layout.addWidget(self.input_language)
        layout.addWidget(self.output_language_label)
        layout.addWidget(self.output_language)
        layout.addWidget(self.audio_device_label)
        layout.addWidget(self.audio_device_combo)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        
        # Subtitle overlay setup
        self.subtitle_overlay = QLabel('', self, flags=Qt.WindowStaysOnTopHint)
        self.subtitle_overlay.setGeometry(0, 0, 800, 100)
        self.subtitle_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; font-size: 24px;")
        self.subtitle_overlay.setAlignment(Qt.AlignCenter)
        self.subtitle_overlay.show()

    def populate_audio_devices(self):
        p = pyaudio.PyAudio()
        self.audio_device_combo.clear()
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('hostApi') == p.get_host_api_info_by_type(pyaudio.paWASAPI)['index']:
                self.audio_device_combo.addItem(device_info.get('name'), i)
        p.terminate()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.input_language.setText(config.get('input_language', 'en-US'))
                self.output_language.setText(config.get('output_language', 'es-ES'))
                audio_device_index = config.get('audio_device_index', -1)
                if audio_device_index != -1:
                    self.audio_device_combo.setCurrentIndex(audio_device_index)
        except FileNotFoundError:
            logging.warning("Config file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Error decoding config file. Using default settings.")

    def save_config(self):
        config = {
            'input_language': self.input_language.text(),
            'output_language': self.output_language.text(),
            'audio_device_index': self.audio_device_combo.currentIndex()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def start_translation(self):
        self.running = True
        self.status_label.setText('Status: Running')
        logging.info("Translation started.")
        self.save_config()
        self.capture_thread = threading.Thread(target=self.capture_audio)
        self.capture_thread.start()
        self.translation_thread = threading.Thread(target=self.translate_continuously)
        self.translation_thread.start()

    def stop_translation(self):
        self.running = False
        self.capture_thread.join()
        self.translation_thread.join()
        self.status_label.setText('Status: Stopped')
        logging.info("Translation stopped.")

    def update_translation(self, text):
        self.label.setText(text)
        self.subtitle_overlay.setText(text)

    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

    def capture_audio(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        LOWCUT = 300.0
        HIGHCUT = 3000.0

        p = pyaudio.PyAudio()

        try:
            device_index = self.audio_device_combo.currentData()
            if device_index is None:
                raise Exception("WASAPI loopback device not found.")
            
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=device_index,
                            as_loopback=True)
            logging.info("Audio capture started using WASAPI loopback.")

            while self.running:
                data = stream.read(CHUNK)
                audio_data = np.frombuffer(data, dtype=np.int16)
                filtered_audio = butter_bandpass_filter(audio_data, LOWCUT, HIGHCUT, RATE)
                normalized_audio = normalize_audio(filtered_audio)
                self.audio_queue.put(normalized_audio)

            stream.stop_stream()
            stream.close()
            p.terminate()
            logging.info("Audio capture stopped.")
        except Exception as e:
            logging.error(f"Error in audio capture: {str(e)}")
            self.show_error_message(f"Error in audio capture: {str(e)}")

    def translate_continuously(self):
        while self.running:
            try:
                if not self.audio_queue.empty():
                    audio_chunk = self.audio_queue.get()
                    translation = self.translate_speech(audio_chunk)
                    self.update_translation(translation)
            except Exception as e:
                logging.error(f"Error in translation: {str(e)}")
                self.update_translation(f"Error in translation: {str(e)}")

    def translate_speech(self, audio_chunk):
        try:
            speech_config = speechsdk.SpeechConfig(subscription="YourAzureSubscriptionKey", region="YourServiceRegion")
            speech_config.speech_recognition_language = self.input_language.text()
            translation_config = speechsdk.translation.SpeechTranslationConfig(
                subscription="YourAzureSubscriptionKey", region="YourServiceRegion",
                speech_recognition_language=self.input_language.text())
            translation_config.add_target_language(self.output_language.text())

            audio_input = speechsdk.audio.AudioConfig(use_default_microphone=True)
            recognizer = speechsdk.translation.TranslationRecognizer(translation_config, audio_input)
            result = recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.TranslatedSpeech:
                logging.info(f"Recognized: {result.text}")
                translations = result.translations[self.output_language.text()]
                return translations
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logging.warning("No speech could be recognized.")
                return "No speech could be recognized."
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logging.error(f"Speech Recognition canceled: {cancellation_details.reason}")
                return f"Speech Recognition canceled: {cancellation_details.reason}"
        except Exception as e:
            logging.error(f"Error in speech recognition: {str(e)}")
            return f"Error in speech recognition: {str(e)}"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TranslatorApp()
    ex.show()
    sys.exit(app.exec_())
