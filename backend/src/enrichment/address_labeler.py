"""
Heuristic-Based Address Labeler
Classifies addresses using rule-based heuristics with extensive logging
"""
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.sql import and_

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import (
    AddressMetadata, Transaction, Transfer, Block
)

logger = DebugLogger("address_labeler")

print("="*80)
print("🏷️  Loading Heuristic-Based Address Labeler")
print("="*80)


class AddressLabeler:
    """
    Heuristic-based address classifier

    Detects:
    - Exchanges (high volume, many counterparties)
    - Validators (staking rewards, governance)
    - Whales (large balances, big transactions)
    - Bots (high frequency, consistent patterns)
    - Bridge/IBC Relayers (cross-chain transfers)
    - Smart Contracts (CosmWasm contracts)
    """

    # Configurable thresholds
    THRESHOLDS = {
        # Exchange detection
        "exchange_min_tx_count": 100,
        "exchange_min_counterparties": 50,
        "exchange_min_volume": 1_000_000,  # 1M ubbn

        # Whale detection
        "whale_min_balance": 100_000_000_000,  # 100k BABY (in ubbn)
        "whale_min_tx_amount": 10_000_000_000,  # 10k BABY

        # Bot detection
        "bot_min_tx_frequency": 10.0,  # 10 tx per day
        "bot_min_tx_count": 100,

        # IBC Relayer detection
        "relayer_min_transfers": 50,

        # Validator detection (placeholder)
        "validator_min_delegations": 10,
    }

    def __init__(self, db: Database):
        """Initialize address labeler"""
        print("\n" + "="*80)
        print("🏷️  Initializing Address Labeler")
        print("="*80)

        self.db = db

        logger.log_startup("AddressLabeler", {
            "thresholds": self.THRESHOLDS
        })

        print("✓ Heuristic thresholds configured:")
        print(f"  • Exchange: ≥{self.THRESHOLDS['exchange_min_tx_count']} txs, ≥{self.THRESHOLDS['exchange_min_counterparties']} counterparties")
        print(f"  • Whale: ≥{self.THRESHOLDS['whale_min_balance']/1e9:.0f} BABY balance")
        print(f"  • Bot: ≥{self.THRESHOLDS['bot_min_tx_frequency']} txs/day")
        print("="*80 + "\n")

    async def label_address(self, address: str) -> Tuple[List[str], float]:
        """
        Label a single address using heuristics

        Args:
            address: Babylon address to label

        Returns:
            (list of labels, confidence score 0.0-1.0)
        """
        logger.debug(f"🔍 Labeling address: {address[:16]}...")
        print(f"🔍 Analyzing address: {address[:16]}...")

        labels = []
        confidence_scores = []

        # Get address statistics
        stats = await self.get_address_stats(address)

        if not stats:
            logger.warning(f"No stats found for address {address[:16]}...")
            print(f"  ⚠️  No activity found for this address")
            return [], 0.0

        logger.debug(f"Address stats", stats=stats)
        print(f"  📊 Stats: {stats['tx_sent']} txs sent, {stats['tx_received']} received, {stats['balance_ubbn']/1e9:.2f} BABY")

        # Apply heuristics
        label_checks = [
            (self._check_exchange, "exchange"),
            (self._check_whale, "whale"),
            (self._check_bot, "bot"),
            (self._check_validator, "validator"),
            (self._check_relayer, "relayer"),
        ]

        for check_func, label_type in label_checks:
            is_match, confidence = await check_func(address, stats)

            if is_match:
                labels.append(label_type)
                confidence_scores.append(confidence)
                logger.info(f"✓ Detected {label_type}", confidence=confidence)
                print(f"  ✅ {label_type.upper()} detected (confidence: {confidence:.2f})")

        # Calculate overall confidence (average of all matched labels)
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        if labels:
            logger.log_metric("address_labeled", 1, "count", {
                "address": address[:16],
                "labels": labels,
                "confidence": round(overall_confidence, 2)
            })
            print(f"  🏷️  Final labels: {', '.join(labels).upper()} (confidence: {overall_confidence:.2f})")
        else:
            print(f"  ℹ️  No labels matched (regular user)")

        return labels, overall_confidence

    async def get_address_stats(self, address: str) -> Optional[Dict]:
        """
        Get statistics for an address

        Returns:
            Dictionary with address statistics or None if no activity
        """
        logger.debug(f"📊 Fetching stats for {address[:16]}...")

        async with self.db.get_session() as session:
            # Count transactions sent
            tx_sent_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(Transaction.sender == address)
            )
            tx_sent = tx_sent_result.scalar() or 0

            # Count transactions received (transfers to this address)
            tx_received_result = await session.execute(
                select(func.count(Transfer.id.distinct()))
                .where(Transfer.to_address == address)
            )
            tx_received = tx_received_result.scalar() or 0

            if tx_sent == 0 and tx_received == 0:
                return None

            # Count unique counterparties
            unique_senders_result = await session.execute(
                select(func.count(Transfer.from_address.distinct()))
                .where(Transfer.to_address == address)
            )
            unique_senders = unique_senders_result.scalar() or 0

            unique_receivers_result = await session.execute(
                select(func.count(Transfer.to_address.distinct()))
                .where(Transfer.from_address == address)
            )
            unique_receivers = unique_receivers_result.scalar() or 0

            unique_counterparties = unique_senders + unique_receivers

            # Calculate total volume
            sent_volume_result = await session.execute(
                select(func.sum(Transfer.amount))
                .where(and_(Transfer.from_address == address, Transfer.denom == 'ubbn'))
            )
            sent_volume = sent_volume_result.scalar() or 0

            received_volume_result = await session.execute(
                select(func.sum(Transfer.amount))
                .where(and_(Transfer.to_address == address, Transfer.denom == 'ubbn'))
            )
            received_volume = received_volume_result.scalar() or 0

            total_volume = sent_volume + received_volume
            current_balance = received_volume - sent_volume  # Simplified balance calculation

            # Get first and last activity timestamps
            first_tx_result = await session.execute(
                select(Transaction.timestamp)
                .where(Transaction.sender == address)
                .order_by(Transaction.timestamp.asc())
                .limit(1)
            )
            first_tx_row = first_tx_result.first()
            first_seen = first_tx_row[0] if first_tx_row else None

            last_tx_result = await session.execute(
                select(Transaction.timestamp)
                .where(Transaction.sender == address)
                .order_by(Transaction.timestamp.desc())
                .limit(1)
            )
            last_tx_row = last_tx_result.first()
            last_seen = last_tx_row[0] if last_tx_row else None

            # Calculate transaction frequency
            tx_frequency = 0.0
            if first_seen and last_seen:
                days_active = (last_seen - first_seen).total_seconds() / 86400
                if days_active > 0:
                    tx_frequency = tx_sent / days_active

            stats = {
                "tx_sent": tx_sent,
                "tx_received": tx_received,
                "total_tx": tx_sent + tx_received,
                "unique_counterparties": unique_counterparties,
                "sent_volume_ubbn": sent_volume,
                "received_volume_ubbn": received_volume,
                "total_volume_ubbn": total_volume,
                "balance_ubbn": current_balance,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "tx_frequency_per_day": tx_frequency,
            }

            logger.log_metric("address_stats_calculated", 1, "count", stats)

            return stats

    async def _check_exchange(self, address: str, stats: Dict) -> Tuple[bool, float]:
        """
        Check if address is an exchange

        Criteria:
        - High transaction count
        - Many unique counterparties
        - High volume
        """
        logger.debug(f"Checking exchange heuristic for {address[:16]}...")

        score = 0.0
        max_score = 3.0

        # Check transaction count
        if stats['tx_sent'] >= self.THRESHOLDS['exchange_min_tx_count']:
            score += 1.0
            logger.debug(f"  ✓ High tx count: {stats['tx_sent']}")

        # Check unique counterparties
        if stats['unique_counterparties'] >= self.THRESHOLDS['exchange_min_counterparties']:
            score += 1.0
            logger.debug(f"  ✓ Many counterparties: {stats['unique_counterparties']}")

        # Check volume
        if stats['total_volume_ubbn'] >= self.THRESHOLDS['exchange_min_volume']:
            score += 1.0
            logger.debug(f"  ✓ High volume: {stats['total_volume_ubbn']/1e9:.2f} BABY")

        confidence = score / max_score
        is_exchange = confidence >= 0.67  # Need 2 out of 3 criteria

        return is_exchange, confidence

    async def _check_whale(self, address: str, stats: Dict) -> Tuple[bool, float]:
        """
        Check if address is a whale (large holder)

        Criteria:
        - Large balance
        - Large transaction amounts
        """
        logger.debug(f"Checking whale heuristic for {address[:16]}...")

        score = 0.0
        max_score = 2.0

        # Check balance
        if stats['balance_ubbn'] >= self.THRESHOLDS['whale_min_balance']:
            score += 1.0
            logger.debug(f"  ✓ Large balance: {stats['balance_ubbn']/1e9:.2f} BABY")

        # Check average transaction size
        avg_tx_amount = stats['sent_volume_ubbn'] / stats['tx_sent'] if stats['tx_sent'] > 0 else 0
        if avg_tx_amount >= self.THRESHOLDS['whale_min_tx_amount']:
            score += 1.0
            logger.debug(f"  ✓ Large avg tx: {avg_tx_amount/1e9:.2f} BABY")

        confidence = score / max_score
        is_whale = confidence >= 0.5  # Need 1 out of 2 criteria

        return is_whale, confidence

    async def _check_bot(self, address: str, stats: Dict) -> Tuple[bool, float]:
        """
        Check if address is a bot

        Criteria:
        - High transaction frequency
        - Consistent patterns
        """
        logger.debug(f"Checking bot heuristic for {address[:16]}...")

        score = 0.0
        max_score = 2.0

        # Check transaction frequency
        if stats['tx_frequency_per_day'] >= self.THRESHOLDS['bot_min_tx_frequency']:
            score += 1.0
            logger.debug(f"  ✓ High frequency: {stats['tx_frequency_per_day']:.2f} txs/day")

        # Check minimum transaction count
        if stats['tx_sent'] >= self.THRESHOLDS['bot_min_tx_count']:
            score += 1.0
            logger.debug(f"  ✓ Many transactions: {stats['tx_sent']}")

        confidence = score / max_score
        is_bot = confidence >= 0.5

        return is_bot, confidence

    async def _check_validator(self, address: str, stats: Dict) -> Tuple[bool, float]:
        """
        Check if address is a validator

        Criteria:
        - Receives staking rewards
        - Participates in governance
        - Has validator metadata

        Note: This is a placeholder. Full implementation requires
        checking validator set and delegations from RPC/chain state.
        """
        logger.debug(f"Checking validator heuristic for {address[:16]}...")

        # Placeholder: would need to query validator set from RPC
        # For now, return False

        # TODO: Implement validator checking:
        # 1. Query /cosmos/staking/v1beta1/validators
        # 2. Check if address is in validator set
        # 3. Check delegation amounts

        return False, 0.0

    async def _check_relayer(self, address: str, stats: Dict) -> Tuple[bool, float]:
        """
        Check if address is an IBC relayer or bridge

        Criteria:
        - High number of transfers
        - Cross-chain activity patterns
        """
        logger.debug(f"Checking relayer heuristic for {address[:16]}...")

        # Check if high number of transfers (both sent and received)
        total_transfers = stats['tx_sent'] + stats['tx_received']

        if total_transfers >= self.THRESHOLDS['relayer_min_transfers']:
            # Additional check: transfers should be bidirectional
            ratio = min(stats['tx_sent'], stats['tx_received']) / max(stats['tx_sent'], stats['tx_received']) if max(stats['tx_sent'], stats['tx_received']) > 0 else 0

            if ratio > 0.3:  # At least 30% balance between sent/received
                logger.debug(f"  ✓ Bidirectional transfers: {total_transfers} total")
                return True, 0.7 + (0.3 * ratio)

        return False, 0.0

    async def label_all_addresses(self, batch_size: int = 100, limit: Optional[int] = None):
        """
        Label all addresses in the database

        Args:
            batch_size: Number of addresses to process per batch
            limit: Maximum number of addresses to process (None = all)
        """
        print("\n" + "="*80)
        print("🚀 Starting Batch Address Labeling")
        print("="*80)

        logger.info("Starting batch address labeling", batch_size=batch_size, limit=limit)

        # Get all unique addresses (from transactions and transfers)
        print("📊 Fetching unique addresses from database...")

        async with self.db.get_session() as session:
            # Get unique senders
            senders_result = await session.execute(
                select(Transaction.sender.distinct())
                .where(Transaction.sender.isnot(None))
            )
            senders = [row[0] for row in senders_result.all()]

            # Get unique transfer addresses
            from_addrs_result = await session.execute(
                select(Transfer.from_address.distinct())
            )
            from_addrs = [row[0] for row in from_addrs_result.all()]

            to_addrs_result = await session.execute(
                select(Transfer.to_address.distinct())
            )
            to_addrs = [row[0] for row in to_addrs_result.all()]

            # Combine and deduplicate
            all_addresses = list(set(senders + from_addrs + to_addrs))

            print(f"✓ Found {len(all_addresses):,} unique addresses")
            logger.info(f"Found {len(all_addresses):,} unique addresses to label")

        # Apply limit if specified
        if limit:
            all_addresses = all_addresses[:limit]
            print(f"  (Limited to first {limit:,} addresses)")

        # Process in batches
        total_labeled = 0
        total_unlabeled = 0
        label_distribution = {}

        print("\n🔄 Processing addresses in batches...")
        print("="*80)

        for i in range(0, len(all_addresses), batch_size):
            batch = all_addresses[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(all_addresses) + batch_size - 1) // batch_size

            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} addresses)")
            print("-"*80)

            for address in batch:
                labels, confidence = await self.label_address(address)

                if labels:
                    # Save to database
                    await self.save_labels(address, labels, confidence)
                    total_labeled += 1

                    # Track label distribution
                    for label in labels:
                        label_distribution[label] = label_distribution.get(label, 0) + 1
                else:
                    total_unlabeled += 1

            # Progress update
            progress_pct = ((i + len(batch)) / len(all_addresses)) * 100
            print(f"\n📊 Progress: {i + len(batch):,}/{len(all_addresses):,} ({progress_pct:.1f}%)")
            print(f"  ✓ Labeled: {total_labeled:,} | Unlabeled: {total_unlabeled:,}")

        # Final summary
        print("\n" + "="*80)
        print("✅ Batch Labeling Complete!")
        print("="*80)
        print(f"Total addresses processed: {len(all_addresses):,}")
        print(f"Labeled addresses: {total_labeled:,}")
        print(f"Unlabeled addresses: {total_unlabeled:,}")
        print(f"\n🏷️  Label Distribution:")
        for label, count in sorted(label_distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {label.upper()}: {count:,}")
        print("="*80 + "\n")

        logger.log_metric("batch_labeling_complete", len(all_addresses), "addresses", {
            "labeled": total_labeled,
            "unlabeled": total_unlabeled,
            "distribution": label_distribution
        })

    async def save_labels(self, address: str, labels: List[str], confidence: float):
        """
        Save address labels to database

        Args:
            address: Address to label
            labels: List of label strings
            confidence: Confidence score (0.0-1.0)
        """
        logger.debug(f"💾 Saving labels for {address[:16]}...", labels=labels, confidence=confidence)

        # Get current stats to populate metadata
        stats = await self.get_address_stats(address)

        if not stats:
            logger.warning(f"Cannot save labels - no stats for {address[:16]}")
            return

        async with self.db.get_session() as session:
            # Check if metadata exists
            result = await session.execute(
                select(AddressMetadata).where(AddressMetadata.address == address)
            )
            metadata = result.scalar_one_or_none()

            if metadata:
                # Update existing
                metadata.label_type = labels[0] if labels else None  # Primary label
                metadata.label_confidence = confidence
                metadata.tags = {"all_labels": labels} if len(labels) > 1 else None
                metadata.total_transactions_sent = stats['tx_sent']
                metadata.total_transactions_received = stats['tx_received']
                metadata.total_sent = stats['sent_volume_ubbn']
                metadata.total_received = stats['received_volume_ubbn']
                metadata.current_balance = stats['balance_ubbn']
                metadata.first_seen = stats['first_seen']
                metadata.last_seen = stats['last_seen']
                metadata.updated_at = datetime.utcnow()

                logger.debug(f"  ✓ Updated existing metadata for {address[:16]}")
            else:
                # Create new
                metadata = AddressMetadata(
                    address=address,
                    label_type=labels[0] if labels else None,
                    label_confidence=confidence,
                    tags={"all_labels": labels} if len(labels) > 1 else None,
                    total_transactions_sent=stats['tx_sent'],
                    total_transactions_received=stats['tx_received'],
                    total_sent=stats['sent_volume_ubbn'],
                    total_received=stats['received_volume_ubbn'],
                    current_balance=stats['balance_ubbn'],
                    first_seen=stats['first_seen'],
                    last_seen=stats['last_seen'],
                    is_contract=False,  # TODO: Implement contract detection
                    is_validator=('validator' in labels),
                )
                session.add(metadata)
                logger.debug(f"  ✓ Created new metadata for {address[:16]}")

            await session.commit()
            logger.info(f"✓ Labels saved for {address[:16]}", labels=labels)


print("✓ Heuristic-based address labeler loaded successfully!")
print("="*80)
