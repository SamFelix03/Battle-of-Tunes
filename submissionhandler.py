import os
import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler
)
import aiohttp

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
WAITING_WALLET, WAITING_AUDIO = range(2)

class SongBattleBot:
    def __init__(self, token):
        self.token = token
        self.participants = {}  # {user_id: {'username': str, 'wallet_address': str, 'audio_file': str}}
        self.battle_start_time = None
        self.battle_active = False

    async def start(self, update: Update, context):
        """Handler for /start command"""
        user = update.effective_user
        
        if self.battle_active and user.id in self.participants:
            await update.message.reply_text(
                "You're already registered for the current song battle!"
            )
            return

        await update.message.reply_text(
            f"Welcome {user.mention_markdown_v2()}! Please provide your crypto wallet address."
        )
        return WAITING_WALLET

    async def validate_wallet_address(self, update: Update, context):
        """Validate and store wallet address"""
        wallet_address = update.message.text.strip()
        user = update.effective_user

        # Basic wallet address validation (you might want to make this more robust)
        if not wallet_address.startswith('0x') or len(wallet_address) != 42:
            await update.message.reply_text(
                "Invalid wallet address. Please provide a valid Ethereum wallet address."
            )
            return WAITING_WALLET

        self.participants[user.id] = {
            'username': user.username,
            'wallet_address': wallet_address,
            'audio_file': None
        }

        # If this is the first participant, start the battle timer
        if len(self.participants) == 1:
            self.battle_start_time = datetime.now()
            self.battle_active = True
            asyncio.create_task(self.battle_timeout())

        await update.message.reply_text(
            f"Wallet address registered! Here's the link to the song generation bot: [Song Bot Link]"
        )
        return ConversationHandler.END

    async def battle_timeout(self):
        """Handle battle timeout logic"""
        await asyncio.sleep(300)  # 5 minutes
        
        if self.battle_active:
            await self.process_battle()

    async def receive_audio(self, update: Update, context):
        """Handle audio file submission"""
        user = update.effective_user
        audio_file = await update.message.audio.get_file()
        
        if user.id not in self.participants:
            await update.message.reply_text("You're not registered for this battle.")
            return

        # Download and save audio file
        file_path = f"audio_submissions/{user.id}_{audio_file.file_unique_id}.mp3"
        await audio_file.download_to_drive(file_path)

        self.participants[user.id]['audio_file'] = file_path

        # Check if all participants have submitted
        if all(p['audio_file'] for p in self.participants.values()):
            await self.process_battle()

    async def process_battle(self):
        """Submit audio files to evaluation API"""
        self.battle_active = False
        
        # Prepare submission data
        submission_data = {
            'submissions': [
                {
                    'wallet_address': participant['wallet_address'],
                    'audio_file': participant['audio_file']
                } 
                for participant in self.participants.values() 
                if participant['audio_file']
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post('https://your-evaluation-api.com/submit', json=submission_data) as response:
                result = await response.json()

        # Announce winner
        winner_wallet = result.get('winner_wallet')
        winner = next(
            (p for p in self.participants.values() if p['wallet_address'] == winner_wallet), 
            None
        )

        if winner:
            message = f"🏆 Battle Winner: {winner['username']} (Wallet: {winner_wallet})"
        else:
            message = "No winner could be determined."

        # Broadcast to all participants
        for user_id in self.participants:
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Could not send message to {user_id}: {e}")

        # Reset battle state
        self.participants.clear()
        self.battle_start_time = None

    def main(self):
        """Set up and run the bot"""
        application = Application.builder().token(self.token).build()

        # Conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                WAITING_WALLET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.validate_wallet_address)
                ],
            },
            fallbacks=[]
        )

        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.AUDIO, self.receive_audio))

        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Replace with your actual Telegram bot token
    TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
    
    # Ensure audio submissions directory exists
    os.makedirs('audio_submissions', exist_ok=True)

    bot = SongBattleBot(TOKEN)
    bot.main()