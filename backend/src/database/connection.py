"""
Database connection and session management
Handles async PostgreSQL connections with extensive logging
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, event
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import time

from ..utils.logger import DebugLogger
from ..utils.config import get_settings
from .models import Base

logger = DebugLogger("database")


class Database:
    """
    Database connection manager with connection pooling
    Provides async sessions and handles reconnection
    """

    def __init__(self):
        """Initialize database connection"""
        settings = get_settings()

        print("\n" + "=" * 80)
        print("🗄️  Initializing Database Connection")
        print("=" * 80)

        # Convert postgresql:// to postgresql+asyncpg://
        self.database_url = settings.database_url.replace(
            'postgresql://',
            'postgresql+asyncpg://'
        )

        logger.log_startup("Database", {
            "url": self._mask_password(self.database_url),
            "pool_size": settings.database_pool_size,
            "echo": settings.database_echo
        })

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections every hour
        )

        # Add query logging
        if settings.log_level == "DEBUG":
            @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
            def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
                conn.info.setdefault("query_start_time", []).append(time.time())
                logger.debug(
                    f"🗄️  Executing query",
                    query=statement[:200] if len(statement) > 200 else statement
                )

            @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
            def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
                total_time = time.time() - conn.info["query_start_time"].pop()
                logger.log_performance("database_query", total_time * 1000, items_processed=cursor.rowcount)

        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Statistics
        self.stats = {
            "queries": 0,
            "inserts": 0,
            "updates": 0,
            "deletes": 0,
            "errors": 0
        }

        logger.info("✓ Database connection initialized")
        print("✓ Database engine created")
        print("✓ Connection pool configured")
        print("=" * 80 + "\n")

    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in database URL"""
        if "@" in url and "://" in url:
            parts = url.split("://")
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                if "@" in rest:
                    creds, host = rest.split("@", 1)
                    if ":" in creds:
                        user, _ = creds.split(":", 1)
                        return f"{protocol}://{user}:****@{host}"
        return url

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session (context manager)

        Usage:
            async with db.get_session() as session:
                result = await session.execute(query)
        """
        logger.debug("📖 Creating new database session")
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
                logger.debug("✓ Session committed successfully")
            except Exception as e:
                await session.rollback()
                self.stats["errors"] += 1
                logger.error("❌ Session rolled back", exc=e)
                raise
            finally:
                await session.close()
                logger.debug("✓ Session closed")

    async def create_tables(self):
        """Create all database tables"""
        logger.info("🔨 Creating database tables...")
        print("\n" + "=" * 80)
        print("🔨 Creating Database Tables")
        print("=" * 80)

        try:
            async with self.engine.begin() as conn:
                # Create tables
                await conn.run_sync(Base.metadata.create_all)

                logger.info("✓ All tables created successfully")
                print("✓ Tables created:")
                for table_name in Base.metadata.tables.keys():
                    print(f"  - {table_name}")

                # Check if TimescaleDB extension is available
                try:
                    result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"))
                    has_timescale = result.scalar() is not None

                    if has_timescale:
                        logger.info("✓ TimescaleDB extension detected")
                        print("\n✓ TimescaleDB detected - time-series optimization available")

                        # Create hypertables for time-series data
                        await self._create_hypertables(conn)
                    else:
                        logger.warning("⚠️  TimescaleDB not available - using regular PostgreSQL")
                        print("\n⚠️  TimescaleDB not installed - using regular PostgreSQL tables")

                except Exception as e:
                    logger.warning("TimescaleDB check failed", exc=e)
                    print("\n⚠️  Could not check for TimescaleDB extension")

        except Exception as e:
            logger.error("Failed to create tables", exc=e)
            raise

        print("=" * 80 + "\n")

    async def _create_hypertables(self, conn):
        """Create TimescaleDB hypertables"""
        logger.info("🕐 Creating TimescaleDB hypertables...")

        hypertables = [
            ('transactions', 'timestamp', '1 day'),
            ('transfers', 'timestamp', '1 day'),
        ]

        for table_name, time_column, chunk_interval in hypertables:
            try:
                # Check if already a hypertable
                check_query = text("""
                    SELECT 1 FROM timescaledb_information.hypertables
                    WHERE hypertable_name = :table_name
                """)
                result = await conn.execute(check_query, {"table_name": table_name})
                exists = result.scalar() is not None

                if not exists:
                    # Create hypertable
                    create_query = text(f"""
                        SELECT create_hypertable(
                            '{table_name}',
                            '{time_column}',
                            chunk_time_interval => INTERVAL '{chunk_interval}',
                            if_not_exists => TRUE
                        )
                    """)
                    await conn.execute(create_query)
                    logger.info(f"✓ Hypertable created: {table_name}")
                    print(f"  ✓ Hypertable: {table_name} (chunked by {chunk_interval})")
                else:
                    logger.debug(f"Hypertable already exists: {table_name}")
                    print(f"  - Hypertable exists: {table_name}")

            except Exception as e:
                logger.warning(f"Failed to create hypertable {table_name}", exc=e)
                print(f"  ⚠️  Could not create hypertable: {table_name}")

    async def drop_tables(self):
        """Drop all database tables (USE WITH CAUTION!)"""
        logger.warning("⚠️  DROPPING ALL TABLES!")
        print("\n" + "=" * 80)
        print("⚠️  DROPPING ALL DATABASE TABLES")
        print("=" * 80)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("✓ All tables dropped")
        print("✓ All tables dropped")
        print("=" * 80 + "\n")

    async def test_connection(self) -> bool:
        """Test database connection"""
        logger.debug("🔍 Testing database connection...")
        print("\n" + "=" * 80)
        print("🔍 Testing Database Connection")
        print("=" * 80)

        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                value = result.scalar()

                if value == 1:
                    logger.info("✓ Database connection test successful")
                    print("✓ Connection test: SUCCESS")
                    print("✓ Database is responsive")

                    # Get PostgreSQL version
                    result = await session.execute(text("SELECT version()"))
                    version = result.scalar()
                    logger.info(f"Database version: {version[:80]}")
                    print(f"✓ Version: {version[:60]}...")

                    print("=" * 80 + "\n")
                    return True

        except Exception as e:
            logger.error("Database connection test failed", exc=e)
            print(f"❌ Connection test: FAILED")
            print(f"❌ Error: {str(e)[:100]}")
            print("=" * 80 + "\n")
            return False

    async def get_stats(self) -> dict:
        """Get database statistics"""
        async with self.get_session() as session:
            stats = {}

            # Get table row counts
            for table_name in Base.metadata.tables.keys():
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    stats[f"{table_name}_count"] = count
                    logger.debug(f"Table {table_name}: {count:,} rows")
                except Exception as e:
                    logger.warning(f"Failed to count {table_name}", exc=e)
                    stats[f"{table_name}_count"] = -1

            # Add operation stats
            stats.update(self.stats)

            return stats

    async def close(self):
        """Close database connections"""
        logger.log_shutdown("Database", "Closing all connections")
        await self.engine.dispose()
        logger.info("✓ Database connections closed")


# Global database instance
_db: Database = None


def get_database() -> Database:
    """Get global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db


# Test the database connection
async def test_database():
    """Test database connection and operations"""
    print("\n" + "=" * 80)
    print("Testing Database Connection")
    print("=" * 80 + "\n")

    db = Database()

    # Test connection
    success = await db.test_connection()

    if success:
        print("\n📊 Database Statistics:")
        print("-" * 80)
        stats = await db.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value:,}")

    await db.close()

    print("\n" + "=" * 80)
    print("✓ Database test complete!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_database())
