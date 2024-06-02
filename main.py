import sys
import threading
import queue
import pyaudio
import numpy as np
import logging
import json
from scipy.signal import butter, lfilter
import azure.cognitiveservices.speech as speechsdk
from PyQt5.QtWidgets import QApplication
from real_time_translator.gui import TranslatorApp

CONFIG_FILE = 'config.json'

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

class TranslatorLogic:
    def __init__(self):
        self.running = False
        self.audio_queue = queue.Queue()
        self.load_config()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.azure_subscription_key = config.get('azure_subscription_key', '')
                self.azure_region = config.get('azure_region', '')
        except FileNotFoundError:
            logging.warning("Config file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Error decoding config file. Using default settings.")

    def get_audio_devices(self):
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                devices.append({'name': device_info.get('name'), 'index': i})
        p.terminate()
        return devices

    def start_translation(self, input_language, output_language, device_index):
        self.running = True
        self.input_language = input_language
        self.output_language = output_language
        self.device_index = device_index
        self.capture_thread = threading.Thread(target=self.capture_audio)
        self.capture_thread.start()
        self.translation_thread = threading.Thread(target=self.translate_continuously)
        self.translation_thread.start()

    def stop_translation(self):
        self.running = False
        self.capture_thread.join()
        self.translation_thread.join()

    def capture_audio(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        LOWCUT = 300.0
        HIGHCUT = 3000.0

        p = pyaudio.PyAudio()

        try:
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=self.device_index)
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
            self.app.show_error_message(f"Error in audio capture: {str(e)}")

    def translate_continuously(self):
        while self.running:
            try:
                if not self.audio_queue.empty():
                    audio_chunk = self.audio_queue.get()
                    translation = self.translate_speech(audio_chunk)
                    self.app.update_translation(translation)
            except Exception as e:
                logging.error(f"Error in translation: {str(e)}")
                self.app.update_translation(f"Error in translation: {str(e)}")

    def translate_speech(self, audio_chunk):
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.azure_subscription_key, region=self.azure_region)
            speech_config.speech_recognition_language = self.input_language
            translation_config = speechsdk.translation.SpeechTranslationConfig(
                subscription=self.azure_subscription_key, region=self.azure_region,
                speech_recognition_language=self.input_language)
            translation_config.add_target_language(self.output_language)

            audio_input = speechsdk.audio.AudioConfig(use_default_microphone=True)
            recognizer = speechsdk.translation.TranslationRecognizer(translation_config, audio_input)
            result = recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.TranslatedSpeech:
                logging.info(f"Recognized: {result.text}")
                translations = result.translations[self.output_language]
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

def main():
    app = QApplication(sys.argv)
    logic = TranslatorLogic()
    ex = TranslatorApp(logic)
    logic.app = ex
    ex.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
