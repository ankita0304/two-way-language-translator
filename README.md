# Two-Way Language Translator

A web app that translates text and speech between 21 languages, with a focus on Indian languages (Hindi, Kannada, Telugu, Tamil, Malayalam, Marathi, Bengali and more). Built with **Python** and **Streamlit**.

![tests](https://github.com/<your-username>/two-way-translator/actions/workflows/tests.yml/badge.svg)

<!-- Add a screenshot or GIF here after you run the app:  ![Demo](docs/demo.png) -->

## Features

| Mode | What it does |
|---|---|
| **Text** | Type text, pick languages, translate, and hear the result. A swap button reverses the direction (and moves the translation into the input box). |
| **Voice** | Record from your microphone, see what was heard, then get the translation as text and audio. |
| **Conversation** | Two speakers, each with their own language. Every message is translated into the *other* speaker's language and shown as a chat, by typing or speaking. |
| **History** | Every translation from all three modes. Export as **CSV, JSON or TXT**. |

Other details: auto-detect source language (text mode), slow-speech option, friendly error messages, clean responsive UI.

## Important: which Google services are used (and which are not)

This project uses **unofficial, free** libraries. None of them is an official Google Cloud API.

| Feature | Library | What it really calls | Official Google Cloud API? |
|---|---|---|---|
| Translation | `deep-translator` (`GoogleTranslator`) | The free Google Translate *web* endpoint | **No** |
| Speech to text | `SpeechRecognition` (`recognize_google`) | Google's free Web Speech endpoint (shared default key) | **No** |
| Text to speech | `gTTS` | Google Translate's text-to-speech web endpoint | **No** |
| Microphone | `st.audio_input` (Streamlit) | Records in the user's browser | n/a |

Consequences you should know about:

- No API key and no cost, which is great for learning and demos.
- **No uptime guarantee.** Google can rate-limit or change these endpoints at any time.
- Roughly 5,000 characters per translation request (long text is split automatically).
- Not suitable for a commercial or high-traffic product. For that, switch to the official Cloud Translation, Speech-to-Text and Text-to-Speech APIs (see *Design decisions*).

## Architecture

```
┌──────────────────────────────────────────────┐
│ Presentation layer (Streamlit)               │
│ app.py  +  ui/components.py, ui/styles.css   │
└──────────────────────┬───────────────────────┘
                       │ calls
┌──────────────────────▼───────────────────────┐
│ Service layer (core/)                        │
│ translator  speech_to_text  text_to_speech   │
│ languages   history                          │
└──────────────────────┬───────────────────────┘
                       │ wraps
┌──────────────────────▼───────────────────────┐
│ External libraries (unofficial Google web    │
│ endpoints): deep-translator, SpeechRecognition, gTTS │
└──────────────────────────────────────────────┘
```

**Voice data flow:** browser microphone, WAV bytes, `transcribe()` gives source text, `Translator.translate()` gives target text, `synthesize()` gives MP3 bytes (in memory), `st.audio` plays it.

## Project structure

```
two_way_translator/
├── app.py                     # Streamlit entry point: layout + wiring only
├── requirements.txt           # Runtime dependencies (pinned)
├── requirements-dev.txt       # + pytest
├── README.md
├── LICENSE
├── .gitignore
├── .streamlit/config.toml     # Theme and server settings
├── .github/workflows/tests.yml  # CI: runs pytest on Python 3.11-3.13
├── core/                      # Business logic (no Streamlit code)
│   ├── languages.py           # Language registry: 3 different codes per language
│   ├── translator.py          # Translator class, chunking, error wrapping
│   ├── speech_to_text.py      # WAV bytes -> text
│   ├── text_to_speech.py      # text -> MP3 bytes (in memory)
│   └── history.py             # History data model + CSV/JSON/TXT export
├── ui/
│   ├── components.py          # Reusable widgets (selector, result card, chat bubble)
│   └── styles.css             # Custom styling
├── utils/
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── validators.py          # Input checks
│   └── logger.py              # Logging setup
└── tests/                     # pytest suite (runs offline)
```

## Run it locally

Requires **Python 3.11 or newer** (Streamlit 1.67 needs it).

```bash
git clone https://github.com/<your-username>/two-way-translator.git
cd two-way-translator

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. An internet connection is required, because translation, speech recognition and audio generation all call Google web endpoints. Your browser will ask for microphone permission the first time you record. (Browsers only allow microphone access on `localhost` or HTTPS.)

No PyAudio and no FFmpeg are needed: the browser records the audio.

## Windows + VS Code quick start

1. Install **Python 3.11+** from https://www.python.org/downloads/ (tick **"Add python.exe to PATH"** in the installer).
2. Open the project folder in VS Code (**File > Open Folder**), then open a terminal with **Ctrl + `**.
3. Run:

```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

4. If PowerShell says *"running scripts is disabled"*, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use the **Command Prompt** terminal instead.
5. In VS Code press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and pick the one inside `venv`.
6. The app opens at http://localhost:8501. Stop it with **Ctrl + C**.

## Upload to GitHub

1. Install Git from https://git-scm.com/download/win and create an empty repository on https://github.com/new (do not add a README there).
2. In the project folder terminal:

```powershell
git init
git add .
git commit -m "Initial commit: Two-Way Language Translator"
git branch -M main
git remote add origin https://github.com/<your-username>/two-way-translator.git
git push -u origin main
```

3. Sign in when the browser prompt appears.

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest tests -v
```

All tests run **offline**. External services are replaced by fakes, and the full Streamlit app is exercised with Streamlit's `AppTest` framework (clicking buttons, checking output, error handling and the de-duplication of voice recordings).

## Deploy to Streamlit Community Cloud (free)

1. Push this project to a **public GitHub repository**.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**, choose your repository and branch, and set **Main file path** to `app.py`.
4. Under **Advanced settings**, choose **Python 3.12** (3.11 to 3.13 all work).
5. Click **Deploy**. Streamlit installs `requirements.txt` automatically.

Streamlit Cloud serves the app over HTTPS, so microphone recording works. There are no secrets or environment variables to configure. If translation or speech fails on the hosted app but works locally, Google may be rate-limiting the shared cloud IP address. This is a limitation of the unofficial endpoints (see below).

## Design decisions (good interview material)

- **Layered architecture.** `app.py` only draws UI and calls services. `core/` has zero Streamlit imports, so it can be tested and reused (for example in a CLI or API) unchanged.
- **One language registry.** `deep-translator`, `gTTS` and `SpeechRecognition` use different language codes (`kn` versus `kn-IN`). Storing all of them per language in `core/languages.py` avoids scattered hard-coded codes, and a test verifies every code against the libraries' own supported-language tables.
- **Exception wrapping.** Each service catches library-specific errors and raises its own `TranslationError`, `SpeechRecognitionError` or `TTSError`. The UI catches one base class and shows a friendly message, so it is not coupled to any library.
- **Dependency injection for testability.** Services accept their backend (`Translator(backend=...)`, `synthesize(..., tts_backend=...)`), so tests use fakes and need no network.
- **Browser-side recording.** `sr.Microphone()` records from the *server's* microphone and needs PyAudio, so it fails once deployed. `st.audio_input` records in the user's browser and sends WAV bytes.
- **Audio in memory.** MP3 is built with `BytesIO`, with no temp files, so there are no clean-up problems or name clashes between users.
- **Streamlit re-runs the script on every interaction.** State lives in `st.session_state`. Recordings are fingerprinted with a hash so the same recording is not sent to the speech service again on every re-run.
- **Graceful degradation.** If audio generation fails, the translation is still shown, with a warning.
- **Security.** User and Google text is passed through `html.escape()` before being placed in custom HTML (prevents XSS), and CSV export prefixes cells that start with `=`, `+`, `-` or `@` (prevents spreadsheet formula injection). The CSV is written with a UTF-8 BOM so Excel displays Indian scripts correctly.
- **Bounded memory.** History is capped at 200 entries per session.
- **Production upgrade path.** To use the official Google Cloud APIs, replace the internals of `translator.py`, `speech_to_text.py` and `text_to_speech.py`. Their public functions and the UI stay the same.

## Known limitations

- Depends on unofficial endpoints that can be rate-limited or changed by Google.
- Speech recognition accuracy varies by language, accent and background noise. Voice input needs a specific language (no auto-detect).
- Audio and speech support differs per language; if audio is unavailable the app says so.
- History lives only in the browser session. Nothing is stored on a server, and a page refresh clears it.
- Machine translation can be wrong. Do not use it for legal, medical or other critical content.

## Future improvements

- Switch to the official Google Cloud (or another provider's) APIs behind the same interfaces.
- Offline speech recognition with Whisper.
- Image / OCR translation, and document upload.
- Persistent history with a database and user accounts.
- Automatic language detection display, and a pronunciation guide.

## License

MIT. See [LICENSE](LICENSE).
