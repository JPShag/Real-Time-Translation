
# Real-Time Live Translator with PyQt GUI

This is a real-time live translator application built using Python, PyQt5, and Azure Cognitive Services. The application captures audio from the Windows system speakers using WASAPI loopback, translates the captured audio into a specified language, and displays the translated text in a GUI overlay that stays on top of all applications.

## Features
- **Real-Time Translation**: Captures and translates audio in real-time.
- **Subtitle Overlay**: Displays translated text as subtitles over all applications.
- **Configurable Input/Output Languages**: Users can specify input and output languages.
- **Audio Device Selection**: Users can choose from available audio devices.
- **Configuration Persistence**: Saves user preferences for input/output languages, selected audio device, and Azure settings.
- **Customization Options**: Customize the subtitle overlay's font, color, and appearance.
- **Settings Management**: Reset settings to default, import/export settings.

## Requirements
- pyenv
- pyenv-virtualenv
- A valid Azure Cognitive Services subscription key and service region.

## Installation

### Install pyenv and pyenv-virtualenv
Follow the instructions [here](https://github.com/pyenv/pyenv) to install pyenv.

Additionally, install pyenv-virtualenv by following the instructions [here](https://github.com/pyenv/pyenv-virtualenv).

### Clone this repository
```sh
git clone https://github.com/jpshag/real-time-translator.git
cd real-time-translator
```

### Set up a Python version with pyenv
Install a specific Python version (e.g., 3.8.10):
```sh
pyenv install 3.8.10
```

Set the local Python version for this project:
```sh
pyenv local 3.8.10
```

### Create and activate a virtual environment with pyenv-virtualenv
Create a virtual environment:
```sh
pyenv virtualenv 3.8.10 translator-env
```

Activate the virtual environment:
```sh
pyenv activate translator-env
```

### Install the required packages
If a `requirements.txt` is provided:
```sh
pip install -r requirements.txt
```

If `requirements.txt` is not provided, manually install the dependencies:
```sh
pip install pyaudio numpy scipy azure-cognitiveservices-speech PyQt5
```

## Configuration
Obtain an Azure Cognitive Services subscription key and service region. You can create a free account [here](https://azure.microsoft.com/free/cognitive-services/).

Create a `config.json` file with your settings:
```json
{
    "input_language": "en-US",
    "output_language": "es-ES",
    "audio_device_index": 0,
    "subtitle_font": "Arial,24",
    "subtitle_color": "#FFFFFF",
    "azure_subscription_key": "YourAzureSubscriptionKey",
    "azure_region": "YourServiceRegion"
}
```

## Usage
Run the application:
```sh
python main.py
```

Configure the input language, output language, and audio device using the GUI.

Click the "Start Translation" button to begin capturing and translating audio.

The translated text will be displayed in the GUI and as a subtitle overlay on top of all applications.

Click the "Stop Translation" button to stop the translation process.

To customize the subtitle overlay, click the "Settings" button and adjust the font, color, and other options as desired.

## Known Issues
- Ensure the correct audio device supporting WASAPI loopback is selected.
- The application currently supports only Windows due to the use of WASAPI for audio capture.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any changes or improvements.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
