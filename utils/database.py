import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    instagram_username = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    session_data = Column(Text)

class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True)
    admin_telegram_id = Column(Integer, nullable=False)
    action = Column(String(255), nullable=False)
    target_user_id = Column(Integer)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class BotStats(Base):
    __tablename__ = "bot_stats"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_comments_deleted = Column(Integer, default=0)
    total_unlikes = Column(Integer, default=0)

class Database:
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    async def initialize(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    async def create_user(self, telegram_id: int, instagram_username: str = None) -> User:
        session = self.SessionLocal()
        try:
            user = User(
                telegram_id=telegram_id,
                instagram_username=instagram_username
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            session.close()
    
    async def get_user(self, telegram_id: int) -> User:
        session = self.SessionLocal()
        try:
            return session.query(User).filter(User.telegram_id == telegram_id).first()
        finally:
            session.close()
    
    async def update_user_login(self, telegram_id: int, instagram_username: str = None):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.last_login = datetime.utcnow()
                if instagram_username:
                    user.instagram_username = instagram_username
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user login: {e}")
        finally:
            session.close()
    
    async def log_admin_action(self, admin_id: int, action: str, target_user_id: int = None, details: str = None):
        session = self.SessionLocal()
        try:
            log_entry = AdminLog(
                admin_telegram_id=admin_id,
                action=action,
                target_user_id=target_user_id,
                details=details
            )
            session.add(log_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging admin action: {e}")
        finally:
            session.close()
    
    async def get_all_users(self) -> list:
        session = self.SessionLocal()
        try:
            return session.query(User).filter(User.is_active == True).all()
        finally:
            session.close()
    
    async def disable_user(self, telegram_id: int):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.is_active = False
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error disabling user: {e}")
        finally:
            session.close()
    
    async def update_stats(self, comments_deleted: int = 0, unlikes: int = 0):
        session = self.SessionLocal()
        try:
            stats = session.query(BotStats).order_by(BotStats.date.desc()).first()
            if not stats:
                stats = BotStats()
                session.add(stats)
            
            stats.total_comments_deleted += comments_deleted
            stats.total_unlikes += unlikes
            stats.total_users = session.query(User).filter(User.is_active == True).count()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating stats: {e}")
        finally:
            session.close()
