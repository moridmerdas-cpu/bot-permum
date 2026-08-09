import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.bot import InstagramManagerBot
from config.settings import Settings
from utils.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    settings = Settings()
    
    db = Database(settings.DATABASE_URL)
    await db.initialize()
    
    bot = InstagramManagerBot(settings, db)
    
    logger.info("🚀 Instagram Manager Bot Starting")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT}")
    
    await bot.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
