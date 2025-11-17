"""
Babylon Block Indexer - Core blockchain synchronization engine
Indexes blocks, transactions, and events with extensive logging
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
import hashlib

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from ..utils.logger import DebugLogger
from ..utils.config import get_settings
from ..utils.rpc_factory import create_rpc_client
from ..database.connection import Database
from ..database.models import Block, Transaction, Transfer

logger = DebugLogger("indexer")


class BlockIndexer:
    """
    Babylon blockchain indexer with extensive debugging
    Synchronizes blocks, transactions, and transfers to database
    """

    def __init__(self, start_height: Optional[int] = None):
        """
        Initialize block indexer

        Args:
            start_height: Block height to start indexing from (None = auto-detect)
        """
        print("\n" + "=" * 80)
        print("⛓️  Initializing Babylon Block Indexer")
        print("=" * 80)

        self.settings = get_settings()
        self.db = Database()
        self.rpc_client = None  # Will be initialized in start()

        # Starting height
        self.start_height = start_height or self.settings.start_height
        self.current_height = self.start_height

        # Statistics
        self.stats = {
            "blocks_indexed": 0,
            "transactions_indexed": 0,
            "transfers_indexed": 0,
            "errors": 0,
            "start_time": None,
            "last_checkpoint": time.time()
        }

        # State
        self.is_syncing = True
        self.is_running = False

        logger.log_startup("BlockIndexer", {
            "start_height": self.start_height,
            "batch_size": self.settings.indexer_batch_size,
            "checkpoint_interval": self.settings.indexer_checkpoint_interval
        })

        print(f"✓ Start height: {self.start_height:,}")
        print(f"✓ Batch size: {self.settings.indexer_batch_size}")
        print(f"✓ Checkpoint interval: {self.settings.indexer_checkpoint_interval}")
        print("=" * 80 + "\n")

    async def initialize(self):
        """Initialize database and RPC client"""
        print("\n" + "=" * 80)
        print("🔧 Initializing Indexer Components")
        print("=" * 80)

        # Test database connection
        logger.info("Testing database connection...")
        print("📊 Testing database connection...")
        success = await self.db.test_connection()

        if not success:
            logger.error("Database connection failed!")
            print("❌ Database connection failed!")
            raise Exception("Cannot connect to database")

        # Create tables if they don't exist
        logger.info("Creating database tables...")
        print("\n📋 Creating database tables...")
        await self.db.create_tables()

        # Initialize RPC client (tries real, falls back to mock)
        logger.info("Initializing RPC client...")
        self.rpc_client = await create_rpc_client()

        # Load last indexed height from database
        await self.load_checkpoint()

        print("=" * 80 + "\n")
        logger.info("✓ Indexer initialized successfully")

    async def load_checkpoint(self):
        """Load last indexed block height from database"""
        logger.debug("🔍 Loading indexer checkpoint from database...")
        print("🔍 Checking for existing blocks in database...")

        try:
            async with self.db.get_session() as session:
                result = await session.execute(
                    select(func.max(Block.height))
                )
                max_height = result.scalar()

                if max_height is not None:
                    self.current_height = max_height + 1
                    logger.info(f"✓ Resuming from block {self.current_height:,}")
                    print(f"✓ Found existing blocks - resuming from height {self.current_height:,}")
                else:
                    logger.info(f"📝 Starting fresh from block {self.current_height:,}")
                    print(f"📝 No existing blocks - starting from height {self.current_height:,}")

        except Exception as e:
            logger.warning("Could not load checkpoint", exc=e)
            print(f"⚠️  Could not check database: {str(e)[:100]}")

    async def save_checkpoint(self):
        """Log checkpoint (blocks are automatically saved)"""
        elapsed = time.time() - self.stats["last_checkpoint"]
        self.stats["last_checkpoint"] = time.time()

        blocks_per_sec = self.stats["blocks_indexed"] / (time.time() - self.stats["start_time"]) if self.stats["start_time"] else 0

        logger.log_metric("indexer_checkpoint", self.current_height, "height", {
            "blocks_indexed": self.stats["blocks_indexed"],
            "tx_indexed": self.stats["transactions_indexed"],
            "transfers_indexed": self.stats["transfers_indexed"],
            "blocks_per_sec": round(blocks_per_sec, 2),
            "elapsed_sec": round(elapsed, 2)
        })

    async def process_block(self, height: int) -> bool:
        """
        Process a single block with extensive logging

        Args:
            height: Block height to process

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            logger.debug(f"🔍 Fetching block #{height:,}...")
            print(f"📦 Processing block #{height:,}...", end=" ", flush=True)

            # Fetch block data
            block_data = await self.rpc_client.get_block(height)
            if not block_data:
                logger.warning(f"Block #{height} not found")
                print("❌ Not found")
                return False

            # Fetch block results (transaction results, events)
            block_results = await self.rpc_client.get_block_results(height)

            # Parse block
            block_model = self.parse_block(block_data, block_results)

            # Parse transactions and transfers
            transactions = []
            transfers = []

            txs_data = block_data['block']['data'].get('txs', [])
            txs_results = block_results.get('txs_results', []) if block_results else []

            logger.debug(f"Parsing {len(txs_data)} transactions...")

            for i, tx_data in enumerate(txs_data):
                tx_result = txs_results[i] if i < len(txs_results) else {}

                tx, tx_transfers = self.parse_transaction(
                    block_data['block']['header'],
                    tx_data,
                    tx_result,
                    i
                )

                if tx:
                    transactions.append(tx)
                    transfers.extend(tx_transfers)

            # Save to database
            async with self.db.get_session() as session:
                # Insert block (use INSERT ... ON CONFLICT DO NOTHING)
                stmt = insert(Block).values(**block_model.__dict__)
                stmt = stmt.on_conflict_do_nothing(index_elements=['height'])
                await session.execute(stmt)

                # Insert transactions
                if transactions:
                    for tx in transactions:
                        stmt = insert(Transaction).values(**tx.__dict__)
                        stmt = stmt.on_conflict_do_nothing(index_elements=['hash'])
                        await session.execute(stmt)

                # Insert transfers
                if transfers:
                    for transfer in transfers:
                        session.add(transfer)

                await session.commit()

            # Update statistics
            self.stats["blocks_indexed"] += 1
            self.stats["transactions_indexed"] += len(transactions)
            self.stats["transfers_indexed"] += len(transfers)

            duration_ms = (time.time() - start_time) * 1000

            logger.log_block_processed(height, len(transactions), duration_ms)
            print(f"✓ {len(transactions)} txs, {len(transfers)} transfers ({duration_ms:.0f}ms)")

            return True

        except Exception as e:
            self.stats["errors"] += 1
            duration_ms = (time.time() - start_time) * 1000

            logger.error(f"Failed to process block #{height}", exc=e, duration_ms=round(duration_ms, 2))
            print(f"❌ Error: {type(e).__name__}")

            return False

    def parse_block(self, block_data: dict, block_results: dict) -> Block:
        """Parse block data into Block model"""
        header = block_data['block']['header']
        block_id = block_data['block_id']

        # Parse timestamp
        timestamp_str = header['time']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Count transactions
        num_txs = len(block_data['block']['data'].get('txs', []))

        # Calculate gas usage
        gas_used = 0
        gas_wanted = 0
        if block_results and 'txs_results' in block_results:
            for tx_result in block_results['txs_results']:
                gas_used += int(tx_result.get('gas_used', 0))
                gas_wanted += int(tx_result.get('gas_wanted', 0))

        block = Block(
            height=int(header['height']),
            hash=block_id['hash'],
            timestamp=timestamp,
            proposer_address=header.get('proposer_address'),
            num_transactions=num_txs,
            gas_used=gas_used,
            gas_wanted=gas_wanted,
            chain_id=header.get('chain_id')
        )

        return block

    def parse_transaction(
        self,
        header: dict,
        tx_data: str,
        tx_result: dict,
        tx_index: int
    ) -> tuple:
        """
        Parse transaction data

        Args:
            header: Block header
            tx_data: Base64 encoded transaction data
            tx_result: Transaction result with events
            tx_index: Transaction index in block

        Returns:
            (Transaction model, list of Transfer models)
        """
        try:
            # Decode transaction and generate hash
            tx_bytes = base64.b64decode(tx_data)
            tx_hash = hashlib.sha256(tx_bytes).hexdigest().upper()

            # Parse timestamp
            timestamp_str = header['time']
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Extract events
            events = tx_result.get('events', [])
            log = tx_result.get('log', '')
            code = tx_result.get('code', 0)
            status = 'success' if code == 0 else 'failed'

            # Extract sender (try to find from events)
            sender = None
            for event in events:
                if event.get('type') == 'message':
                    for attr in event.get('attributes', []):
                        if attr.get('key') == 'sender':
                            sender = attr.get('value')
                            break
                if sender:
                    break

            # Extract transfers from events
            transfers = self.extract_transfers(tx_hash, header, events)

            # Create transaction model
            transaction = Transaction(
                hash=tx_hash,
                block_height=int(header['height']),
                timestamp=timestamp,
                tx_index=tx_index,
                sender=sender,
                gas_used=int(tx_result.get('gas_used', 0)),
                gas_wanted=int(tx_result.get('gas_wanted', 0)),
                status=status,
                code=code,
                events=events,
                raw_log=log
            )

            return transaction, transfers

        except Exception as e:
            logger.warning(f"Failed to parse transaction", exc=e)
            return None, []

    def extract_transfers(self, tx_hash: str, header: dict, events: list) -> List[Transfer]:
        """Extract transfer events from transaction events"""
        transfers = []

        # Parse timestamp
        timestamp_str = header['time']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        for event in events:
            if event.get('type') in ['transfer', 'coin_spent', 'coin_received']:
                # Parse transfer attributes
                attributes = {attr.get('key'): attr.get('value') for attr in event.get('attributes', [])}

                recipient = attributes.get('recipient')
                sender = attributes.get('sender')
                amount_str = attributes.get('amount', '')

                if recipient and amount_str:
                    # Parse amount (format: "1000ubbn" or "1000ubbn,500ubbn")
                    for amount_part in amount_str.split(','):
                        amount_part = amount_part.strip()
                        if amount_part:
                            # Extract amount and denom
                            import re
                            match = re.match(r'(\d+)(\w+)', amount_part)
                            if match:
                                amount = int(match.group(1))
                                denom = match.group(2)

                                transfer = Transfer(
                                    tx_hash=tx_hash,
                                    block_height=int(header['height']),
                                    timestamp=timestamp,
                                    from_address=sender or '',
                                    to_address=recipient,
                                    amount=amount,
                                    denom=denom
                                )
                                transfers.append(transfer)

        return transfers

    async def run(self):
        """Main indexer loop with extensive progress logging"""
        if not self.rpc_client:
            await self.initialize()

        self.is_running = True
        self.stats["start_time"] = time.time()

        print("\n" + "=" * 80)
        print("🚀 Starting Babylon Block Indexer")
        print("=" * 80)
        print(f"📊 Starting height: {self.current_height:,}")
        print("⏳ Synchronizing blockchain data...")
        print("=" * 80 + "\n")

        logger.info(f"Starting indexer from height {self.current_height:,}")

        try:
            while self.is_running:
                # Get latest network height
                latest_height = await self.rpc_client.get_latest_height()

                logger.debug(f"Latest network height: {latest_height:,}, Current: {self.current_height:,}")

                if self.current_height <= latest_height:
                    # We're behind - sync mode
                    success = await self.process_block(self.current_height)

                    if success:
                        self.current_height += 1

                        # Progress logging
                        if self.stats["blocks_indexed"] % 10 == 0:
                            behind = latest_height - self.current_height
                            progress_pct = (self.current_height / latest_height * 100) if latest_height > 0 else 0
                            blocks_per_sec = self.stats["blocks_indexed"] / (time.time() - self.stats["start_time"])

                            logger.log_indexer_progress(self.current_height, latest_height, blocks_per_sec)

                            print(f"\n📊 Progress: {self.current_height:,}/{latest_height:,} ({progress_pct:.1f}%) | "
                                  f"Behind: {behind:,} | Speed: {blocks_per_sec:.2f} blocks/sec")

                        # Checkpoint
                        if self.stats["blocks_indexed"] % self.settings.indexer_checkpoint_interval == 0:
                            await self.save_checkpoint()
                            print(f"💾 Checkpoint: {self.stats['blocks_indexed']:,} blocks indexed\n")

                        # Check if caught up
                        if self.current_height > latest_height - 10:
                            if self.is_syncing:
                                self.is_syncing = False
                                logger.info("🎉 Caught up with blockchain!")
                                print("\n" + "=" * 80)
                                print("🎉 Caught up with blockchain!")
                                print("=" * 80)
                                print(f"✓ Indexed {self.stats['blocks_indexed']:,} blocks")
                                print(f"✓ Indexed {self.stats['transactions_indexed']:,} transactions")
                                print(f"✓ Indexed {self.stats['transfers_indexed']:,} transfers")
                                print("=" * 80 + "\n")
                    else:
                        # Failed to process block - wait and retry
                        logger.warning(f"Waiting before retry...")
                        await asyncio.sleep(self.settings.indexer_retry_delay)

                else:
                    # We're caught up - wait for new blocks
                    await asyncio.sleep(self.settings.indexer_block_time)

        except KeyboardInterrupt:
            logger.info("🛑 Indexer stopped by user")
            print("\n" + "=" * 80)
            print("🛑 Indexer stopped by user")
            print("=" * 80)
        except Exception as e:
            logger.error("Indexer crashed", exc=e)
            print(f"\n❌ Indexer crashed: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown indexer gracefully"""
        print("\n" + "=" * 80)
        print("📊 Final Statistics")
        print("=" * 80)

        total_time = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        blocks_per_sec = self.stats["blocks_indexed"] / total_time if total_time > 0 else 0

        print(f"✓ Blocks indexed: {self.stats['blocks_indexed']:,}")
        print(f"✓ Transactions indexed: {self.stats['transactions_indexed']:,}")
        print(f"✓ Transfers indexed: {self.stats['transfers_indexed']:,}")
        print(f"✓ Errors: {self.stats['errors']}")
        print(f"✓ Total time: {total_time:.1f}s")
        print(f"✓ Speed: {blocks_per_sec:.2f} blocks/sec")
        print("=" * 80 + "\n")

        logger.log_shutdown("BlockIndexer", f"Indexed {self.stats['blocks_indexed']} blocks")

        if self.rpc_client:
            await self.rpc_client.close()

        await self.db.close()

        logger.info("✓ Indexer shutdown complete")


# Run the indexer
async def main():
    """Main entry point"""
    indexer = BlockIndexer()
    await indexer.run()


if __name__ == "__main__":
    asyncio.run(main())
