# Two-Way Language Translator

A web-based translator built using **Python and Streamlit**. It supports text translation, voice translation, conversation mode, and translation history across 11 languages.

Text translation uses a locally running **LibreTranslate server powered by Argos Translate**.

## Features

| Mode | Description |
|---|---|
| Text Translation | Enter text, select source and target languages, and translate. |
| Voice Translation | Record speech, convert it into text, translate it, and listen to the translated audio. |
| Conversation Mode | Two speakers can communicate using different languages. Messages are translated into the other speaker's language. |
| Translation History | View previous translations and export history as CSV, JSON, or TXT. |

Other features:
- Automatic source-language detection in text mode.
- Swap source and target languages.
- Speech-to-text and text-to-speech support.
- Friendly error messages.
- Responsive user interface.

## Supported Languages

The application currently supports:

1. English
2. Hindi
3. Bengali
4. Urdu
5. Arabic
6. French
7. German
8. Spanish
9. Italian
10. Russian
11. Japanese

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Streamlit | Web application interface |
| LibreTranslate | Text translation service |
| Argos Translate | Local machine translation engine |
| Requests | Communication with LibreTranslate |
| SpeechRecognition | Speech-to-text |
| gTTS | Text-to-speech |
| Pandas and NumPy | Data processing and supporting operations |
| Pytest | Unit testing |

## Architecture

The application follows a layered architecture.

```text
Presentation Layer
       |
       v
   app.py
       |
       v
    ui/
       |
       v
   Service Layer
      core/
       |
       +---- translator.py
       +---- languages.py
       +---- speech_to_text.py
       +---- text_to_speech.py
       +---- history.py
       |
       v
 External Services
       |
       +---- LibreTranslate
       +---- Argos Translate
       +---- Speech Recognition
       +---- gTTS
```

## Project Structure

```text
two-way-language-translator/
|
|-- app.py
|-- requirements.txt
|-- requirements-dev.txt
|-- README.md
|-- LICENSE
|-- .gitignore
|
|-- .streamlit/
|   |-- config.toml
|
|-- .github/
|   |-- workflows/
|       |-- tests.yml
|
|-- core/
|   |-- languages.py
|   |-- translator.py
|   |-- speech_to_text.py
|   |-- text_to_speech.py
|   |-- history.py
|
|-- ui/
|   |-- components.py
|   |-- styles.css
|
|-- utils/
|   |-- exceptions.py
|   |-- validators.py
|   |-- logger.py
|
|-- tests/
    |-- conftest.py
    |-- test_app.py
    |-- test_history.py
    |-- test_languages.py
    |-- test_speech_to_text.py
    |-- test_text_to_speech.py
    |-- test_translator.py
    |-- test_validators.py
```

## Run the Project Locally

### Requirements

- Python 3.11 or newer.
- LibreTranslate running locally.
- Required Argos Translate language packages installed.
- Internet connection for speech recognition and text-to-speech services.

### Step 1: Clone the repository

```bash
git clone https://github.com/ankita0304/two-way-language-translator.git
cd two-way-language-translator
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start LibreTranslate

Make sure the local LibreTranslate server is running at:

```text
http://127.0.0.1:5000
```

Install the required Argos language packages for the supported translation pairs.

### Step 5: Run the application

Open another terminal in the project directory and execute:

```bash
streamlit run app.py
```

Open the application in your browser:

```text
http://localhost:8501
```

## Run Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run all tests:

```bash
python -m pytest -q
```

The test suite uses mock backends for external services so tests can run without making actual translation or speech-service requests.

## GitHub Repository

Project source code:

[Two-Way Language Translator](https://github.com/ankita0304/two-way-language-translator)

## Design Decisions

- **Layered Architecture:** The application separates the user interface, business logic, and utility functions.
- **Centralized Language Registry:** Language configurations are maintained in `core/languages.py`.
- **Local Translation:** LibreTranslate connects to the locally running Argos Translate engine.
- **Error Handling:** Custom exceptions provide meaningful error messages.
- **Dependency Injection:** Services support mock backends, making testing easier.
- **Session Management:** Streamlit session state maintains translation history and application state.
- **Audio Processing:** Audio data is processed in memory rather than stored in temporary files.

## Known Limitations

- LibreTranslate must be running locally for text translation.
- Required Argos language packages must be installed.
- Speech recognition and text-to-speech depend on external services.
- Speech recognition accuracy can vary depending on accent and background noise.
- Translation results may not always be accurate.
- Translation history is maintained within the current application session.

## Future Improvements

- Add more supported languages.
- Integrate offline speech recognition using Whisper.
- Add image and document translation.
- Implement database-based translation history.
- Improve speech recognition and pronunciation support.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
