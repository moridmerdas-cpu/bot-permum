import logging
import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword

logger = logging.getLogger(__name__)

class InstagramManager:
    def __init__(self, session_file: str = None):
        self.client = None
        self.user_id = None
        self.username = None
        self.session_file = session_file
    
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Authenticate with Instagram using instagrapi library"""
        try:
            self.client = Client()
            self.client.login(username, password)
            self.user_id = self.client.user_id
            self.username = username
            
            if self.session_file:
                os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
                self.client.dump_settings(self.session_file)
            
            return True, "✅ ورود موفق"
        except BadPassword:
            return False, "❌ رمز اشتباه"
        except LoginRequired:
            return False, "❌ ورود ناموفق - اکانت محدود شده"
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"❌ خطا در ورود: {str(e)}"
    
    def restore_session(self, session_file: str) -> bool:
        """Restore previous session without storing passwords"""
        try:
            if not os.path.exists(session_file):
                return False
            self.client = Client()
            self.client.load_settings(session_file)
            self.client.get_timeline_feed()  # validates the restored session is still active
            self.user_id = self.client.user_id
            self.session_file = session_file
            return True
        except Exception as e:
            logger.error(f"Session restore failed: {e}")
            return False
    
    def get_user_media(self, limit: int = 50) -> list:
        """Fetch user's own posts"""
        if not self.client:
            return []
        try:
            media = self.client.user_medias(self.user_id, amount=limit)
            return media
        except Exception as e:
            logger.error(f"Failed to fetch media: {e}")
            return []
    
    def unlike_all_posts(self) -> dict:
        """Remove likes from all user's posts"""
        if not self.client:
            return {"status": "error", "message": "❌ وارد نشده"}
        
        try:
            media_list = self.get_user_media(limit=100)
            unliked_count = 0
            failed_count = 0
            
            for media in media_list:
                try:
                    if media.like_count > 0:
                        self.client.media_unlike(media.id)
                        unliked_count += 1
                except Exception as e:
                    logger.warning(f"Failed to unlike {media.id}: {e}")
                    failed_count += 1
            
            return {
                "status": "success",
                "unliked": unliked_count,
                "failed": failed_count
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_own_comments(self) -> dict:
        """Delete comments made by this account"""
        if not self.client:
            return {"status": "error", "message": "❌ وارد نشده"}
        
        try:
            media_list = self.get_user_media(limit=100)
            deleted_count = 0
            failed_count = 0
            
            for media in media_list:
                try:
                    comments = self.client.media_comments(media.id)
                    for comment in comments:
                        if comment.user.pk == self.user_id:
                            self.client.comment_delete(media.id, comment.pk)
                            deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed processing media {media.id}: {e}")
                    failed_count += 1
            
            return {
                "status": "success",
                "deleted": deleted_count,
                "failed": failed_count
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_account_info(self) -> dict:
        """Get account information"""
        if not self.client:
            return {}
        try:
            user = self.client.user_info(self.user_id)
            return {
                "username": user.username,
                "full_name": user.full_name,
                "biography": user.biography,
                "followers": user.follower_count,
                "following": user.following_count,
                "media_count": user.media_count,
                "is_verified": user.is_verified
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    def logout(self):
        """Clear session"""
        try:
            if self.session_file and os.path.exists(self.session_file):
                os.remove(self.session_file)
        except Exception as e:
            logger.warning(f"Error clearing session file: {e}")
        
        self.client = None
        self.user_id = None
        self.username = None
