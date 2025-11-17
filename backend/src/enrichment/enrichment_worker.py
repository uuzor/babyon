"""
Background Enrichment Worker
Continuously enriches addresses with labels and metadata
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from ..utils.logger import DebugLogger
from ..utils.config import get_settings
from ..database.connection import Database
from .address_labeler import AddressLabeler
from .ml_classifier import MLAddressClassifier

logger = DebugLogger("enrichment_worker")

print("="*80)
print("⚙️  Loading Background Enrichment Worker")
print("="*80)


class EnrichmentWorker:
    """
    Background worker that continuously enriches addresses

    Tasks:
    1. Label new addresses using heuristics
    2. Classify addresses using ML (if model trained)
    3. Update address metadata
    4. Track enrichment progress
    """

    def __init__(
        self,
        batch_size: int = 100,
        interval_seconds: int = 300,  # 5 minutes
        use_ml: bool = True,
        ml_model_path: Optional[str] = None
    ):
        """
        Initialize enrichment worker

        Args:
            batch_size: Number of addresses to process per batch
            interval_seconds: Seconds between enrichment cycles
            use_ml: Whether to use ML classifier in addition to heuristics
            ml_model_path: Path to pre-trained ML model
        """
        print("\n" + "="*80)
        print("⚙️  Initializing Enrichment Worker")
        print("="*80)

        self.batch_size = batch_size
        self.interval = interval_seconds
        self.use_ml = use_ml

        self.db = Database()
        self.heuristic_labeler = AddressLabeler(self.db)
        self.ml_classifier = None

        if use_ml:
            self.ml_classifier = MLAddressClassifier(self.db, model_path=ml_model_path)

        # Statistics
        self.stats = {
            "cycles_completed": 0,
            "addresses_enriched": 0,
            "heuristic_labels_applied": 0,
            "ml_labels_applied": 0,
            "errors": 0,
            "start_time": None,
        }

        self.is_running = False

        logger.log_startup("EnrichmentWorker", {
            "batch_size": batch_size,
            "interval_seconds": interval_seconds,
            "use_ml": use_ml,
            "ml_model_loaded": self.ml_classifier and self.ml_classifier.is_trained if self.ml_classifier else False
        })

        print(f"✓ Batch size: {batch_size}")
        print(f"✓ Enrichment interval: {interval_seconds}s ({interval_seconds/60:.1f} minutes)")
        print(f"✓ Heuristic labeling: ENABLED")
        print(f"✓ ML classification: {'ENABLED' if use_ml and self.ml_classifier and self.ml_classifier.is_trained else 'DISABLED'}")
        print("="*80 + "\n")

    async def run(self):
        """Main enrichment loop"""
        print("\n" + "="*80)
        print("🚀 Starting Background Enrichment Worker")
        print("="*80)

        self.is_running = True
        self.stats["start_time"] = datetime.utcnow()

        logger.info("Enrichment worker started")

        try:
            while self.is_running:
                cycle_start = datetime.utcnow()

                print(f"\n⏰ Enrichment cycle started at {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-"*80)

                # Run enrichment cycle
                await self.enrich_batch()

                self.stats["cycles_completed"] += 1

                # Calculate next cycle time
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                wait_time = max(0, self.interval - cycle_duration)

                print(f"\n✓ Cycle complete (took {cycle_duration:.1f}s)")
                print(f"⏳ Waiting {wait_time:.1f}s until next cycle...")
                print("="*80)

                logger.log_metric("enrichment_cycle_complete", 1, "count", {
                    "duration_seconds": round(cycle_duration, 2),
                    "addresses_processed": self.batch_size
                })

                # Wait for next cycle
                await asyncio.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("Enrichment worker stopped by user")
            print("\n🛑 Enrichment worker stopped by user")
        except Exception as e:
            logger.error("Enrichment worker crashed", exc=e)
            print(f"\n❌ Enrichment worker crashed: {e}")
            raise
        finally:
            await self.shutdown()

    async def enrich_batch(self):
        """
        Enrich a batch of addresses

        Strategy:
        1. Find addresses with no labels (prioritize new/active addresses)
        2. Apply heuristic labeling
        3. Apply ML classification (if enabled and model trained)
        4. Update metadata in database
        """
        logger.debug("Starting enrichment batch")
        print("🔍 Finding addresses to enrich...")

        # Get unlabeled addresses (prioritize recent activity)
        from sqlalchemy import select, and_, or_
        from ..database.models import AddressMetadata, Transaction, Transfer

        async with self.db.get_session() as session:
            # Strategy: Find addresses from recent transactions that haven't been labeled

            # Get recent addresses from transactions
            recent_tx_result = await session.execute(
                select(Transaction.sender.distinct())
                .where(Transaction.sender.isnot(None))
                .order_by(Transaction.timestamp.desc())
                .limit(self.batch_size * 2)  # Get more than we need
            )
            recent_senders = [row[0] for row in recent_tx_result.all()]

            # Get recent addresses from transfers
            recent_transfer_result = await session.execute(
                select(Transfer.from_address.distinct())
                .order_by(Transfer.timestamp.desc())
                .limit(self.batch_size * 2)
            )
            recent_from = [row[0] for row in recent_transfer_result.all()]

            # Combine and deduplicate
            candidate_addresses = list(set(recent_senders + recent_from))

            # Filter out already labeled addresses
            labeled_result = await session.execute(
                select(AddressMetadata.address)
                .where(AddressMetadata.label_type.isnot(None))
            )
            labeled_addresses = set(row[0] for row in labeled_result.all())

            # Get unlabeled addresses
            unlabeled_addresses = [addr for addr in candidate_addresses if addr not in labeled_addresses]

            # Take batch_size addresses
            addresses_to_process = unlabeled_addresses[:self.batch_size]

        if not addresses_to_process:
            print("  ℹ️  No new addresses found to enrich (all recent addresses already labeled)")
            logger.info("No addresses to enrich")
            return

        print(f"  ✓ Found {len(addresses_to_process)} unlabeled addresses")

        # Process each address
        enriched_count = 0

        for i, address in enumerate(addresses_to_process):
            print(f"\n📍 Address {i+1}/{len(addresses_to_process)}: {address[:16]}...")

            try:
                # Apply heuristic labeling
                heuristic_labels, heuristic_confidence = await self.heuristic_labeler.label_address(address)

                if heuristic_labels:
                    print(f"  🏷️  Heuristic: {', '.join(heuristic_labels).upper()} ({heuristic_confidence:.2%})")

                # Apply ML classification (if enabled and model trained)
                ml_label = None
                ml_confidence = 0.0

                if self.use_ml and self.ml_classifier and self.ml_classifier.is_trained:
                    ml_label, ml_confidence = await self.ml_classifier.predict(address)

                    if ml_label:
                        print(f"  🤖 ML: {ml_label.upper()} ({ml_confidence:.2%})")

                # Combine labels (prefer ML if high confidence, otherwise use heuristic)
                final_label = None
                final_confidence = 0.0

                if ml_label and ml_confidence >= 0.7:
                    # High confidence ML prediction
                    final_label = ml_label
                    final_confidence = ml_confidence
                    print(f"  ✅ Final: {final_label.upper()} (ML, {final_confidence:.2%})")
                    self.stats["ml_labels_applied"] += 1
                elif heuristic_labels:
                    # Use heuristic label
                    final_label = heuristic_labels[0]  # Primary label
                    final_confidence = heuristic_confidence
                    print(f"  ✅ Final: {final_label.upper()} (Heuristic, {final_confidence:.2%})")
                    self.stats["heuristic_labels_applied"] += 1
                else:
                    print(f"  ℹ️  No label assigned (regular user)")

                # Save labels
                if final_label:
                    await self.heuristic_labeler.save_labels(address, [final_label], final_confidence)
                    enriched_count += 1

            except Exception as e:
                logger.error(f"Failed to enrich address {address[:16]}", exc=e)
                print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")
                self.stats["errors"] += 1

        self.stats["addresses_enriched"] += enriched_count

        print(f"\n📊 Batch summary:")
        print(f"  ✓ Addresses processed: {len(addresses_to_process)}")
        print(f"  ✓ Addresses enriched: {enriched_count}")
        print(f"  ✓ Heuristic labels: {self.stats['heuristic_labels_applied']}")
        if self.use_ml:
            print(f"  ✓ ML labels: {self.stats['ml_labels_applied']}")

    async def shutdown(self):
        """Shutdown enrichment worker gracefully"""
        print("\n" + "="*80)
        print("📊 Enrichment Worker Statistics")
        print("="*80)

        if self.stats["start_time"]:
            runtime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
            print(f"✓ Runtime: {runtime:.1f}s ({runtime/60:.1f} minutes)")

        print(f"✓ Cycles completed: {self.stats['cycles_completed']}")
        print(f"✓ Addresses enriched: {self.stats['addresses_enriched']}")
        print(f"✓ Heuristic labels applied: {self.stats['heuristic_labels_applied']}")
        print(f"✓ ML labels applied: {self.stats['ml_labels_applied']}")
        print(f"✓ Errors: {self.stats['errors']}")

        print("="*80 + "\n")

        logger.log_shutdown("EnrichmentWorker", f"Enriched {self.stats['addresses_enriched']} addresses")

        await self.db.close()

        logger.info("✓ Enrichment worker shutdown complete")


async def main():
    """Main entry point for enrichment worker"""
    settings = get_settings()

    worker = EnrichmentWorker(
        batch_size=100,
        interval_seconds=300,  # 5 minutes
        use_ml=True,
        ml_model_path=None  # Will auto-train if needed
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())


print("✓ Background enrichment worker loaded successfully!")
print("="*80)
