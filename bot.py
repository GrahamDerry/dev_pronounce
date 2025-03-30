import os
import random
import json
import telegram.constants  # Import this for MarkdownV2
from google.cloud import texttospeech
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes
)
from telegram.error import BadRequest  # Add this at the top

import database

############################
# Generates speech from text using Google Cloud Text-to-Speech API.
############################
def synthesize_speech(text, filename="output.mp3"):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(filename, "wb") as out:
        out.write(response.audio_content)

    return filename  # Return the generated file path


############################
# GLOBALS AND CONSTANTS
############################
load_dotenv(override=True)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

ACTIVITY1_STATE = range(1)

###########################
# HELPER FUNCTIONS
###########################
def load_words(filepath="words1.json"):
    """Load the JSON file containing words and their IPA."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def escape_markdown_v2(text: str) -> str:
    """
    Escape all special characters that Telegram Markdown V2 requires.
    If any of these aren't escaped, Telegram may drop the formatting.
    """
    # This covers all the characters Telegram specifically says to escape for MarkdownV2.
    for ch in r"_*[\]()~`>#+-=|{}.!":
        text = text.replace(ch, "\\" + ch)
    return text


###########################
# /start COMMAND
###########################
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.username or "Unknown"

    # Register user if new
    database.register_user(user_id, user_name)

    await update.message.reply_text(
        "Hello! Welcome to the English Pronunciation Bot.\n"
        "Type /activity1 to start practicing IPA symbols, or /progress to view your progress."
    )

###########################
# /progress COMMAND
###########################
async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a menu of activities with checkmarks if completed, or arrows if incomplete."""
    user_id = update.effective_user.id

    # For Activity 1:
    # Count how many total words in words1.json
    all_words_dict = load_words("words1.json")
    total_count_activity1 = len(all_words_dict.keys())

    # How many words user has learned for Activity 1
    completed_words = database.get_completed_words1(user_id, as_list=True)
    learned_count_activity1 = len(completed_words)

    # Decide if Activity 1 is complete
    if learned_count_activity1 >= total_count_activity1:
        status1 = "✅"
    else:
        status1 = "🔄"

    # Placeholder for Activity 2
    status2 = "🔄"  # Not implemented
    # You can expand logic for Activity 2 in the future

    # Create an inline keyboard so user can tap to see details of each activity
    keyboard = [
        [InlineKeyboardButton(text=f"Activity 1 {status1}", callback_data="progress_activity1")],
        [InlineKeyboardButton(text=f"Activity 2 {status2}", callback_data="progress_activity2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Your progress:\n\n"
        f"Activity 1 {status1}\n"
        f"Activity 2 {status2}\n\n"
        "Tap a button to see details."
    )

    await update.message.reply_text(text, reply_markup=reply_markup)

###########################
# PROGRESS DETAILS (CALLBACK)
###########################
async def progress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks for progress details."""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == "progress_activity1":
        # Show the user the words they have completed in Activity 1
        learned_words = database.get_completed_words1(user_id, as_list=True)
        if learned_words:
            joined_words = "\n".join(learned_words)
            text = f"Activity 1 - Learned words ({len(learned_words)}):\n{joined_words}"
        else:
            text = "You haven't learned any words in Activity 1 yet."
        await query.edit_message_text(text=text)

    elif query.data == "progress_activity2":
        # Just a placeholder
        text = "Activity 2 progress is not implemented yet."
        await query.edit_message_text(text=text)


###########################
# ACTIVITY 1 - ENTRY POINT
###########################
async def activity1_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """
    Start Activity 1 - Present a random set of IPA words to the user.
    """
    user_id = update.effective_user.id
    all_words_dict = load_words("words1.json")
    all_words_list = list(all_words_dict.keys())

    # Get words the user has completed
    completed_words = database.get_completed_words1(user_id)

    # If user has learned them all, show the 'activity complete' message
    if len(completed_words) >= len(all_words_list):
        await update.message.reply_text("🎉 Activity Complete! 🎉 You have learned all words in Activity 1.")
        return ConversationHandler.END

    # Filter out completed words
    unseen_words = [w for w in all_words_list if w not in completed_words]
    random.shuffle(unseen_words)

    # Take up to 10 words in a session
    session_words = unseen_words[:10]

    # Store session info in user_data
    context.user_data["activity1_session_words"] = session_words
    context.user_data["activity1_session_index"] = 0
    context.user_data["activity1_all_words_dict"] = all_words_dict

    return await activity1_present_word(update, context)

############################
# ACTIVITY 1 - WORD PRESENTATION
############################
async def activity1_present_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show the current IPA word with a Next/Show/Listen interface, or end if no more.
    """
    session_words = context.user_data["activity1_session_words"]
    index = context.user_data["activity1_session_index"]
    all_words_dict = context.user_data["activity1_all_words_dict"]

    if index >= len(session_words):
        # Mark these words completed
        user_id = update.effective_user.id
        database.mark_completed_words1(user_id, session_words)

        completed_words = database.get_completed_words1(user_id)
        total_words = list(all_words_dict.keys())
        if len(completed_words) >= len(total_words):
            await _send_message(update, context, "🎉 Activity Complete! 🎉 You have learned all words in Activity 1.")
            return ConversationHandler.END
        else:
            await _send_message(update, context, "Session complete! Type /activity1 to practice more.")
        return ConversationHandler.END

    # Get current word and IPA transcription
    current_word = session_words[index]
    ipa = all_words_dict[current_word]

    # Escape special characters for MarkdownV2
    ipa_escaped = escape_markdown_v2(ipa)

    # Build inline keyboard
    reply_markup = _make_keyboard()

    # Display the word in bold
    n = index + 1
    x = len(session_words)
    text_msg = f"Word {n}/{x}\n*{ipa_escaped}*\n ✏️"

    await _send_message(update, context, text_msg, reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
    return ACTIVITY1_STATE


async def _send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text, reply_markup=None, parse_mode=None):
    """
    Helper to send a new message in any context (text command or callback query).
    If it's a callback query, update.message is None. So we use chat_id.
    """
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode  # Ensure MarkdownV2 parsing if provided
    )


##############################
# ACTIVITY 1 - BUTTON HANDLERS
##############################

async def activity1_handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle Listen, Show, and Next button presses.
    """
    query = update.callback_query
    await query.answer()

    choice = query.data
    index = context.user_data["activity1_session_index"]
    session_words = context.user_data["activity1_session_words"]
    all_words_dict = context.user_data["activity1_all_words_dict"]

    current_word = session_words[index]
    ipa = all_words_dict[current_word]

    # For the “counter” text
    n = index + 1
    x = len(session_words)

    if choice == "listen":
        # Generate speech audio for the word
        audio_file = synthesize_speech(current_word)

        # Send the audio file to the user and store the message ID
        audio_message = await query.message.reply_voice(voice=open(audio_file, "rb"))
        
        # Store audio message ID in context for deletion
        if "audio_messages" not in context.user_data:
            context.user_data["audio_messages"] = []
        
        context.user_data["audio_messages"].append(audio_message.message_id)

        return ACTIVITY1_STATE

    elif choice == "show":
        # Escape for MarkdownV2
        ipa_escaped = escape_markdown_v2(ipa)
        text_msg = f"Word {n}/{x}\n*{ipa_escaped}*\n{current_word}"

        await query.edit_message_text(
            text=text_msg,
            reply_markup=_make_keyboard(),
            parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
        )
        return ACTIVITY1_STATE

    elif choice == "next":
        # Delete old audio messages
        if "audio_messages" in context.user_data:
            for message_id in context.user_data["audio_messages"]:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
                except BadRequest:
                    pass  # Ignore errors if the message was already deleted

            context.user_data["audio_messages"] = []  # Reset the list after deletion

        context.user_data["activity1_session_index"] += 1
        # Remove the old message
        await query.delete_message()
        # Present the next word in a new message
        return await activity1_present_word(update, context)


def _make_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Listen", callback_data="listen"),
            InlineKeyboardButton("Show", callback_data="show"),
            InlineKeyboardButton("Next", callback_data="next")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def activity1_handle_quit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed 'quit' => end the conversation immediately."""
    await _send_message(update, context, "Exiting Activity 1. Type /activity1 to start again.")
    return ConversationHandler.END


############################
# MAIN FUNCTION
############################
def main():
    """Start the bot."""
    database.init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # /start and /progress commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("progress", progress_command))

    # Callback handlers for progress details
    app.add_handler(CallbackQueryHandler(progress_callback, pattern=r"^progress_activity"))

    # Activity 1 conversation
    activity1_handler = ConversationHandler(
        entry_points=[CommandHandler("activity1", activity1_start)],
        states={
            ACTIVITY1_STATE: [
                CallbackQueryHandler(activity1_handle_buttons),
                MessageHandler(filters.Regex(r'(?i)^quit$'), activity1_handle_quit),
            ]
        },
        fallbacks=[MessageHandler(filters.Regex(r'(?i)^quit$'), activity1_handle_quit)],
    )
    app.add_handler(activity1_handler)

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
