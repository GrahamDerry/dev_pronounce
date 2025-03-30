# English Pronunciation Telegram Bot

This is a Telegram bot designed to help Spanish-speaking developers improve their English pronunciation using IPA (International Phonetic Alphabet) transcription.

## Features

- Practice developer-related English vocabulary with IPA symbols.
- Interactive Telegram UI with inline buttons.
- Google Cloud Text-to-Speech integration for pronunciation.
- Tracks user progress across activities.
- Local database (SQLite or other) to persist data.

## Commands

- `/start` – Welcome message and instructions.
- `/activity1` – Practice session with listen/reveal buttons.
- `/progress` – View your learning progress.

## Setup

1. Clone the repository.  
2. Create a `.env` file with the following:

    ```
    TELEGRAM_BOT_TOKEN=your_telegram_token
    GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json
    ```

3. Install dependencies:

    ```bash
    pip3 install -r requirements.txt
    ```

4. Run the bot:

    ```bash
    python3 bot.py
    ```
