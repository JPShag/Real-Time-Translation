# Real-Time Live Translator with PyQt GUI

This is a real-time live translator application built using Python, PyQt5, and Azure Cognitive Services. The application captures audio from the Windows system speakers using WASAPI loopback, translates the captured audio into a specified language, and displays the translated text in a GUI overlay that stays on top of all applications.

## Features

- **Real-Time Translation**: Captures and translates audio in real-time.
- **Subtitle Overlay**: Displays translated text as subtitles over all applications.
- **Configurable Input/Output Languages**: Users can specify input and output languages.
- **Audio Device Selection**: Users can choose from available audio devices.
- **Configuration Persistence**: Saves user preferences for input/output languages and selected audio device.

## Requirements

- Python 3.x
- `pyaudio`
- `numpy`
- `scipy`
- `azure-cognitiveservices-speech`
- `PyQt5`
- A valid Azure Cognitive Services subscription key and service region.

## Installation

1. Clone this repository:

    ```sh
    git clone https://github.com/yourusername/repo-name.git
    cd repo-name
    ```

2. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

    If `requirements.txt` is not provided, you can manually install the dependencies:

    ```sh
    pip install pyaudio numpy scipy azure-cognitiveservices-speech PyQt5
    ```

## Configuration

1. Obtain an Azure Cognitive Services subscription key and service region. You can create a free account [here](https://azure.microsoft.com/en-us/services/cognitive-services/speech-to-text/).

2. Update the Azure subscription key and region in the code:

    ```python
    speech_config = speechsdk.SpeechConfig(subscription="YourAzureSubscriptionKey", region="YourServiceRegion")
    ```

3. Optionally, you can create a `config.json` file to save your settings:

    ```json
    {
        "input_language": "en-US",
        "output_language": "es-ES",
        "audio_device_index": 0
    }
    ```

## Usage

1. Run the application:

    ```sh
    python main.py
    ```

2. Configure the input language, output language, and audio device using the GUI.

3. Click the "Start Translation" button to begin capturing and translating audio.

4. The translated text will be displayed in the GUI and as a subtitle overlay on top of all applications.

5. Click the "Stop Translation" button to stop the translation process.

## Known Issues

- Ensure the correct audio device supporting WASAPI loopback is selected.
- The application currently supports only Windows due to the use of WASAPI for audio capture.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
