
import asyncio
from bot.db.database import init_db
from bot.config import config

async def main():
    print(f"Initializing database at: {config.database_url}")
    await init_db()
    print("Database columns and tables created successfully.")

if __name__ == "__main__":
    asyncio.run(main())
