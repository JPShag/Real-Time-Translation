import sys
import threading
import queue
import pyaudio
import numpy as np
import logging
from scipy.signal import butter, lfilter
import azure.cognitiveservices.speech as speechsdk
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit
from PyQt5.QtCore import Qt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        
        self.output_language_label = QLabel('Output Language:', self)
        self.output_language = QLineEdit(self)
        self.output_language.setPlaceholderText('es-ES')
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_language_label)
        layout.addWidget(self.input_language)
        layout.addWidget(self.output_language_label)
        layout.addWidget(self.output_language)
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

    def start_translation(self):
        self.running = True
        self.status_label.setText('Status: Running')
        logging.info("Translation started.")
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

    def capture_audio(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        LOWCUT = 300.0
        HIGHCUT = 3000.0

        p = pyaudio.PyAudio()

        try:
            # Use WASAPI loopback for capturing system audio
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=self.get_wasapi_device_index(),
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
            self.update_translation(f"Error in audio capture: {str(e)}")

    def get_wasapi_device_index(self):
        # Get the index of the WASAPI loopback device
        p = pyaudio.PyAudio()
        device_index = None
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if (device_info.get('name') == 'Speaker (Realtek High Definition Audio)' and
                    device_info.get('hostApi') == p.get_host_api_info_by_type(pyaudio.paWASAPI)['index']):
                device_index = i
                break
        p.terminate()
        return device_index

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
