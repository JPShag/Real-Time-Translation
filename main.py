import sys
import threading
import queue
import pyaudio
import numpy as np
import logging
import json
from scipy.signal import butter, lfilter
import azure.cognitiveservices.speech as speechsdk
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QComboBox, QLineEdit, QMessageBox, QDialog, QFormLayout, QColorDialog, QFileDialog, QFontDialog
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

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle('Settings')
        self.setGeometry(200, 200, 400, 300)
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.font_button = QPushButton('Choose Font', self)
        self.font_button.clicked.connect(self.choose_font)
        layout.addWidget(self.font_button)

        self.color_button = QPushButton('Choose Color', self)
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        self.reset_button = QPushButton('Reset to Default', self)
        self.reset_button.clicked.connect(self.reset_settings)
        layout.addWidget(self.reset_button)

        self.import_button = QPushButton('Import Settings', self)
        self.import_button.clicked.connect(self.import_settings)
        layout.addWidget(self.import_button)

        self.export_button = QPushButton('Export Settings', self)
        self.export_button.clicked.connect(self.export_settings)
        layout.addWidget(self.export_button)

        self.setLayout(layout)

    def choose_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.parent().subtitle_overlay.setFont(font)
            self.parent().save_config()

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.parent().subtitle_overlay.setStyleSheet(f"background-color: rgba(0, 0, 0, 128); color: {color.name()}; font-size: 24px;")
            self.parent().save_config()

    def reset_settings(self):
        self.parent().reset_to_default()
        self.parent().save_config()

    def import_settings(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.parent().load_config(file_name)

    def export_settings(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Settings", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.parent().save_config(file_name)

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
        self.label.setStyleSheet("font-size: 16px; margin-bottom: 20px;")

        self.start_button = QPushButton('Start Translation', self)
        self.start_button.clicked.connect(self.start_translation)
        self.start_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: green; color: white;")

        self.stop_button = QPushButton('Stop Translation', self)
        self.stop_button.clicked.connect(self.stop_translation)
        self.stop_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: red; color: white;")

        self.status_label = QLabel('Status: Stopped', self)
        self.status_label.setStyleSheet("font-size: 14px; color: red;")

        self.settings_button = QPushButton('Settings', self)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: blue; color: white;")

        self.input_language_label = QLabel('Input Language:', self)
        self.input_language = QLineEdit(self)
        self.input_language.setPlaceholderText('en-US')
        self.input_language.setToolTip('Enter the language code for the input language (e.g., en-US for English)')
        self.input_language.setStyleSheet("font-size: 14px; padding: 5px;")

        self.output_language_label = QLabel('Output Language:', self)
        self.output_language = QLineEdit(self)
        self.output_language.setPlaceholderText('es-ES')
        self.output_language.setToolTip('Enter the language code for the output language (e.g., es-ES for Spanish)')
        self.output_language.setStyleSheet("font-size: 14px; padding: 5px;")

        self.audio_device_label = QLabel('Audio Device:', self)
        self.audio_device_combo = QComboBox(self)
        self.populate_audio_devices()
        self.audio_device_combo.setStyleSheet("font-size: 14px; padding: 5px;")

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
        layout.addWidget(self.settings_button)
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
            if device_info.get('maxInputChannels') > 0:
                self.audio_device_combo.addItem(device_info.get('name'), i)
        p.terminate()

    def load_config(self, file_name=CONFIG_FILE):
        try:
            with open(file_name, 'r') as f:
                config = json.load(f)
                self.input_language.setText(config.get('input_language', 'en-US'))
                self.output_language.setText(config.get('output_language', 'es-ES'))
                audio_device_index = config.get('audio_device_index', -1)
                if audio_device_index != -1:
                    self.audio_device_combo.setCurrentIndex(audio_device_index)
                font = config.get('subtitle_font', "Arial,24")
                self.subtitle_overlay.setFont(QFont(*font.split(',')))
                color = config.get('subtitle_color', '#FFFFFF')
                self.subtitle_overlay.setStyleSheet(f"background-color: rgba(0, 0, 0, 128); color: {color}; font-size: 24px;")
        except FileNotFoundError:
            logging.warning("Config file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Error decoding config file. Using default settings.")

    def save_config(self, file_name=CONFIG_FILE):
        font = self.subtitle_overlay.font()
        config = {
            'input_language': self.input_language.text(),
            'output_language': self.output_language.text(),
            'audio_device_index': self.audio_device_combo.currentIndex(),
            'subtitle_font': f"{font.family()},{font.pointSize()}",
            'subtitle_color': self.subtitle_overlay.styleSheet().split('color: ')[1].split(';')[0]
        }
        with open(file_name, 'w') as f:
            json.dump(config, f)

    def reset_to_default(self):
        self.input_language.setText('en-US')
        self.output_language.setText('es-ES')
        self.audio_device_combo.setCurrentIndex(0)
        self.subtitle_overlay.setFont(QFont("Arial", 24))
        self.subtitle_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; font-size: 24px;")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def start_translation(self):
        self.running = True
        self.status_label.setText('Status: Running')
        self.status_label.setStyleSheet("color: green;")
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
        self.status_label.setStyleSheet("color: red;")
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
                raise Exception("Selected audio device not found.")
            
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=device_index)
            logging.info("Audio capture started using selected device.")

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
