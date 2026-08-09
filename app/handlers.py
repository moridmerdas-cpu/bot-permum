import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .instagram import InstagramManager
from config.settings import Settings
from utils.database import Database
import os

logger = logging.getLogger(__name__)

INSTAGRAM_LOGIN_USERNAME, INSTAGRAM_LOGIN_PASSWORD = range(2)

class UserHandlers:
    def __init__(self, db: Database, managers: dict, settings: Settings):
        self.db = db
        self.managers = managers
        self.settings = settings
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user_id = update.effective_user.id
        user = await self.db.get_user(user_id)
        
        if not user:
            await self.db.create_user(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🔐 ورود اینستاگرام", callback_data="login_instagram")],
            [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 خوش آمدی به Instagram Account Manager\n\n"
            "اینجا می تونی اکانت اینستاگرامت رو مدیریت کنی:",
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
📚 **راهنما**

این ربات کار می کنه برای:
• ❌ حذف تمام کامنت های خودت
• 💔 حذف لایک های خودت روی پست ها
• 👤 مشاهده اطلاعات اکانت

**نکات مهم:**
⚠️ رمز اینستاگرام هرگز ذخیره نمی شود
🔒 جلسه درست بعد از لاگ اوت حذف می شود
📱 فقط عملیات خودت رو می تونی مدیریت کنی

/login - برای ورود
/logout - برای خروج
        """
        await update.message.reply_text(help_text)
    
    async def login_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate login flow"""
        await update.message.reply_text(
            "📧 **یوزرنیم یا ایمیل اینستاگرامت رو ارسال کن:**"
        )
        return INSTAGRAM_LOGIN_USERNAME
    
    async def handle_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram username input"""
        context.user_data['instagram_username'] = update.message.text
        await update.message.reply_text(
            "🔑 **حالا رمزت رو ارسال کن:**"
        )
        return INSTAGRAM_LOGIN_PASSWORD
    
    async def handle_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram password and perform login"""
        user_id = update.effective_user.id
        username = context.user_data.get('instagram_username')
        password = update.message.text
        
        await update.message.reply_text("⏳ در حال ورود...")
        
        # Create session file
        sessions_dir = self.settings.SESSIONS_DIR
        session_file = os.path.join(sessions_dir, f"{user_id}.json")
        
        manager = InstagramManager(session_file=session_file)
        success, message = manager.login(username, password)
        
        if success:
            self.managers[user_id] = manager
            await self.db.update_user_login(user_id, username)
            
            await update.message.reply_text(
                f"✅ وارد شدی به @{manager.username}\n\n"
                "از منوی زیر انتخاب کن:"
            )
            await self.show_main_menu(update, context)
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text(message)
            context.user_data.clear()
            return ConversationHandler.END
    
    async def cancel_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel login"""
        context.user_data.clear()
        await update.message.reply_text("❌ ورود لغو شد.")
        return ConversationHandler.END
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display main management menu"""
        keyboard = [
            [
                InlineKeyboardButton("❌ حذف کامنت های من", callback_data="delete_comments"),
                InlineKeyboardButton("💔 حذف لایک های من", callback_data="unlike_all")
            ],
            [
                InlineKeyboardButton("👤 اطلاعات اکانت", callback_data="account_info"),
                InlineKeyboardButton("🚪 خروج", callback_data="logout")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text="📱 **منوی مدریت اینستاگرام**",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📱 **منوی مدریت اینستاگرام**",
                reply_markup=reply_markup
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()
        
        if query.data == "login_instagram":
            await query.edit_message_text("📧 یوزرنیم یا ایمیل اینستاگرامت رو ارسال کن:")
            return
        
        elif query.data == "help":
            help_text = """
📚 **راهنما**

این ربات کار می کنه برای:
• ❌ حذف تمام کامنت های خودت
• 💔 حذف لایک های خودت روی پست ها
• 👤 مشاهده اطلاعات اکانت

**نکات مهم:**
⚠️ رمز اینستاگرام هرگز ذخیره نمی شود
🔒 جلسه درست بعد از لاگ اوت حذف می شود
📱 فقط عملیات خودت رو می تونی مدیریت کنی
            """
            await query.edit_message_text(help_text)
            return
        
        manager = self.managers.get(user_id)
        if not manager or not manager.client:
            await query.edit_message_text("❌ لطفا ابتدا وارد شو /login")
            return
        
        if query.data == "delete_comments":
            await query.edit_message_text("⏳ در حال حذف کامنت ها...")
            result = manager.delete_own_comments()
            
            if result['status'] == 'success':
                await self.db.update_stats(comments_deleted=result['deleted'])
                await query.edit_message_text(
                    f"✅ کامنت های حذف شده: {result['deleted']}\n"
                    f"❌ ناموفق: {result['failed']}"
                )
            else:
                await query.edit_message_text(f"❌ خطا: {result['message']}")
            
            await self.show_main_menu(update, context)
        
        elif query.data == "unlike_all":
            await query.edit_message_text("⏳ در حال حذف لایک ها...")
            result = manager.unlike_all_posts()
            
            if result['status'] == 'success':
                await self.db.update_stats(unlikes=result['unliked'])
                await query.edit_message_text(
                    f"✅ لایک های حذف شده: {result['unliked']}\n"
                    f"❌ ناموفق: {result['failed']}"
                )
            else:
                await query.edit_message_text(f"❌ خطا: {result['message']}")
            
            await self.show_main_menu(update, context)
        
        elif query.data == "account_info":
            info = manager.get_account_info()
            if info:
                info_text = f"""
👤 **اطلاعات اکانت**

نام کاربری: @{info.get('username', 'N/A')}
نام کامل: {info.get('full_name', 'N/A')}
بیوگرافی: {info.get('biography', 'N/A')}
دنبال کننده: {info.get('followers', 0):,}
دنبال کردن: {info.get('following', 0):,}
تعداد پست: {info.get('media_count', 0)}
تایید شده: {'✓' if info.get('is_verified') else '✗'}
                """
                await query.edit_message_text(info_text)
            else:
                await query.edit_message_text("❌ خطا در دریافت اطلاعات")
            
            await self.show_main_menu(update, context)
        
        elif query.data == "logout":
            manager.logout()
            if user_id in self.managers:
                del self.managers[user_id]
            await query.edit_message_text("👋 خروج موفق. /start برای شروع دوباره")


class AdminHandlers:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel access"""
        user_id = update.effective_user.id
        
        if user_id != self.settings.ADMIN_TELEGRAM_ID:
            await update.message.reply_text("❌ شما دسترسی ندارید.")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
                InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("📋 لاگ اقدامات", callback_data="admin_logs"),
                InlineKeyboardButton("🔍 جستجو", callback_data="admin_search")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🛠️ **پنل مدیریت**",
            reply_markup=reply_markup
        )
        
        await self.db.log_admin_action(user_id, "admin_panel_opened")
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin callbacks"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if user_id != self.settings.ADMIN_TELEGRAM_ID:
            await query.answer("❌ دسترسی رد شد", show_alert=True)
            return
        
        await query.answer()
        
        if query.data == "admin_stats":
            users = await self.db.get_all_users()
            await query.edit_message_text(
                f"📊 **آمار ربات**\n\n"
                f"کل کاربران: {len(users)}\n"
                f"کاربران فعال: {sum(1 for u in users if u.is_active)}\n\n"
                f"آخرین بروزرسانی: الان"
            )
        
        elif query.data == "admin_users":
            users = await self.db.get_all_users()
            user_list = "\n".join([
                f"@{u.instagram_username or 'N/A'} (ID: {u.telegram_id})"
                for u in users[:10]
            ])
            await query.edit_message_text(
                f"👥 **لیست کاربران (10 تای آخر)**\n\n{user_list}"
            )
