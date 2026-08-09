import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import TelegramError
from .instagram import InstagramManager
from .handlers import UserHandlers, AdminHandlers
from config.settings import Settings
from utils.database import Database

logger = logging.getLogger(__name__)

INSTAGRAM_LOGIN_USERNAME, INSTAGRAM_LOGIN_PASSWORD = range(2)

class InstagramManagerBot:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self.managers = {}
        self.app = None
    
    async def run(self):
        """Start the bot"""
        self.app = Application.builder().token(self.settings.TELEGRAM_TOKEN).build()
        
        # User handlers
        user_handlers = UserHandlers(self.db, self.managers, self.settings)
        admin_handlers = AdminHandlers(self.db, self.settings)
        
        # Conversation handler for login
        login_conv = ConversationHandler(
            entry_points=[CommandHandler("login", user_handlers.login_command)],
            states={
                INSTAGRAM_LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.handle_username)],
                INSTAGRAM_LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.handle_password)],
            },
            fallbacks=[CommandHandler("cancel", user_handlers.cancel_login)]
        )
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", user_handlers.start))
        self.app.add_handler(CommandHandler("help", user_handlers.help_command))
        self.app.add_handler(CommandHandler("admin", admin_handlers.admin_panel))
        self.app.add_handler(login_conv)
        
        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(user_handlers.handle_callback))
        self.app.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_callback))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
        logger.info("🚀 Bot initialized successfully")
        
        if self.settings.ENVIRONMENT == "production" and self.settings.TELEGRAM_WEBHOOK_URL:
            await self.setup_webhook()
        else:
            await self.app.run_polling()
    
    async def setup_webhook(self):
        """Setup webhook for production"""
        try:
            await self.app.bot.set_webhook(
                url=self.settings.TELEGRAM_WEBHOOK_URL,
                drop_pending_updates=True
            )
            logger.info(f"✅ Webhook set to {self.settings.TELEGRAM_WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"❌ Webhook setup failed: {e}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ یک خطا رخ داده. لطفا بعدا دوباره تلاش کن."
                )
        except TelegramError as e:
            logger.error(f"Failed to send error message: {e}")
