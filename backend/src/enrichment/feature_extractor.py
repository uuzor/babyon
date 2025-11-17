"""
Feature Extractor for ML-Based Address Classification
Extracts 30+ features from address transaction history
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import Counter, defaultdict
from sqlalchemy import select, func, and_

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import Transaction, Transfer, Block

logger = DebugLogger("feature_extractor")

print("="*80)
print("🔬 Loading ML Feature Extractor")
print("="*80)


class FeatureExtractor:
    """
    Extract features from address transaction history for ML classification

    Features (35 total):
    - Transaction features (10)
    - Temporal features (8)
    - Network features (7)
    - Balance features (5)
    - Token features (5)
    """

    def __init__(self, db: Database):
        """Initialize feature extractor"""
        print("\n" + "="*80)
        print("🔬 Initializing Feature Extractor")
        print("="*80)

        self.db = db

        # Feature names for reference
        self.feature_names = [
            # Transaction features (10)
            "tx_count_7d",
            "tx_count_30d",
            "tx_count_all",
            "avg_tx_value",
            "std_tx_value",
            "tx_frequency_per_day",
            "sent_received_ratio",
            "unique_senders",
            "unique_receivers",
            "unique_counterparties",

            # Temporal features (8)
            "hour_entropy",
            "day_of_week_entropy",
            "days_since_first_tx",
            "days_since_last_tx",
            "tx_velocity_7d",
            "tx_velocity_30d",
            "active_days_ratio",
            "avg_time_between_txs",

            # Network features (7)
            "in_degree",
            "out_degree",
            "degree_centrality",
            "sent_volume",
            "received_volume",
            "net_flow",
            "volume_ratio",

            # Balance features (5)
            "current_balance",
            "max_balance",
            "balance_volatility",
            "avg_balance",
            "balance_growth_rate",

            # Token/Activity features (5)
            "num_tokens",
            "gas_used_total",
            "gas_used_avg",
            "failed_tx_ratio",
            "round_number_ratio",
        ]

        logger.log_startup("FeatureExtractor", {
            "num_features": len(self.feature_names)
        })

        print(f"✓ Feature extractor initialized")
        print(f"✓ Total features: {len(self.feature_names)}")
        print("="*80 + "\n")

    async def extract(self, address: str) -> Optional[np.ndarray]:
        """
        Extract feature vector for an address

        Args:
            address: Babylon address

        Returns:
            NumPy array of features or None if insufficient data
        """
        logger.debug(f"🔍 Extracting features for {address[:16]}...")
        print(f"🔬 Extracting {len(self.feature_names)} features for {address[:16]}...")

        try:
            # Get raw data from database
            data = await self._fetch_address_data(address)

            if not data or data['tx_count_all'] == 0:
                logger.warning(f"Insufficient data for {address[:16]}")
                print(f"  ⚠️  Insufficient data for feature extraction")
                return None

            # Extract features
            features = []

            # Transaction features (10)
            features.extend([
                data['tx_count_7d'],
                data['tx_count_30d'],
                data['tx_count_all'],
                data['avg_tx_value'],
                data['std_tx_value'],
                data['tx_frequency'],
                data['sent_received_ratio'],
                data['unique_senders'],
                data['unique_receivers'],
                data['unique_counterparties'],
            ])

            # Temporal features (8)
            features.extend([
                data['hour_entropy'],
                data['day_entropy'],
                data['days_since_first'],
                data['days_since_last'],
                data['tx_velocity_7d'],
                data['tx_velocity_30d'],
                data['active_days_ratio'],
                data['avg_time_between_txs'],
            ])

            # Network features (7)
            features.extend([
                data['in_degree'],
                data['out_degree'],
                data['degree_centrality'],
                data['sent_volume'],
                data['received_volume'],
                data['net_flow'],
                data['volume_ratio'],
            ])

            # Balance features (5)
            features.extend([
                data['current_balance'],
                data['max_balance'],
                data['balance_volatility'],
                data['avg_balance'],
                data['balance_growth_rate'],
            ])

            # Token/Activity features (5)
            features.extend([
                data['num_tokens'],
                data['gas_used_total'],
                data['gas_used_avg'],
                data['failed_tx_ratio'],
                data['round_number_ratio'],
            ])

            feature_array = np.array(features, dtype=np.float32)

            logger.log_metric("features_extracted", len(features), "count", {
                "address": address[:16],
                "feature_summary": {
                    "tx_count": int(data['tx_count_all']),
                    "avg_tx_value": float(data['avg_tx_value']),
                    "balance": float(data['current_balance']),
                }
            })

            print(f"  ✓ Extracted {len(features)} features successfully")

            return feature_array

        except Exception as e:
            logger.error(f"Feature extraction failed for {address[:16]}", exc=e)
            print(f"  ❌ Feature extraction failed: {type(e).__name__}")
            return None

    async def _fetch_address_data(self, address: str) -> Optional[Dict]:
        """
        Fetch raw address data from database

        Returns:
            Dictionary with all computed features
        """
        logger.debug(f"📊 Fetching raw data for {address[:16]}...")

        async with self.db.get_session() as session:
            now = datetime.utcnow()
            seven_days_ago = now - timedelta(days=7)
            thirty_days_ago = now - timedelta(days=30)

            # === Transaction Counts ===

            # All time tx count
            tx_all_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(Transaction.sender == address)
            )
            tx_count_all = tx_all_result.scalar() or 0

            if tx_count_all == 0:
                return None  # No transactions

            # 7-day tx count
            tx_7d_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(
                    Transaction.sender == address,
                    Transaction.timestamp >= seven_days_ago
                ))
            )
            tx_count_7d = tx_7d_result.scalar() or 0

            # 30-day tx count
            tx_30d_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(
                    Transaction.sender == address,
                    Transaction.timestamp >= thirty_days_ago
                ))
            )
            tx_count_30d = tx_30d_result.scalar() or 0

            # === Transfer Values ===

            # Sent transfers
            sent_result = await session.execute(
                select(
                    func.count(Transfer.id),
                    func.sum(Transfer.amount),
                    func.avg(Transfer.amount),
                    func.stddev(Transfer.amount)
                )
                .where(and_(Transfer.from_address == address, Transfer.denom == 'ubbn'))
            )
            sent_row = sent_result.first()
            sent_count = sent_row[0] or 0
            sent_volume = sent_row[1] or 0
            avg_sent = sent_row[2] or 0
            std_sent = sent_row[3] or 0

            # Received transfers
            received_result = await session.execute(
                select(
                    func.count(Transfer.id),
                    func.sum(Transfer.amount),
                )
                .where(and_(Transfer.to_address == address, Transfer.denom == 'ubbn'))
            )
            received_row = received_result.first()
            received_count = received_row[0] or 0
            received_volume = received_row[1] or 0

            # === Unique Counterparties ===

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

            # === Temporal Features ===

            # Get all transaction timestamps
            tx_timestamps_result = await session.execute(
                select(Transaction.timestamp)
                .where(Transaction.sender == address)
                .order_by(Transaction.timestamp)
            )
            tx_timestamps = [row[0] for row in tx_timestamps_result.all()]

            if not tx_timestamps:
                return None

            first_tx = tx_timestamps[0]
            last_tx = tx_timestamps[-1]
            days_active = (last_tx - first_tx).total_seconds() / 86400 if len(tx_timestamps) > 1 else 1
            days_since_first = (now - first_tx).total_seconds() / 86400
            days_since_last = (now - last_tx).total_seconds() / 86400

            # Calculate hour/day distributions for entropy
            hours = [ts.hour for ts in tx_timestamps]
            days_of_week = [ts.weekday() for ts in tx_timestamps]

            hour_entropy = self._calculate_entropy(hours, 24)
            day_entropy = self._calculate_entropy(days_of_week, 7)

            # Active days ratio
            unique_days = len(set(ts.date() for ts in tx_timestamps))
            active_days_ratio = unique_days / max(days_active, 1)

            # Average time between transactions
            if len(tx_timestamps) > 1:
                time_diffs = [(tx_timestamps[i+1] - tx_timestamps[i]).total_seconds() for i in range(len(tx_timestamps)-1)]
                avg_time_between = np.mean(time_diffs) / 86400  # In days
            else:
                avg_time_between = 0

            # Transaction velocity
            tx_velocity_7d = tx_count_7d / 7 if tx_count_7d > 0 else 0
            tx_velocity_30d = tx_count_30d / 30 if tx_count_30d > 0 else 0

            # === Gas Features ===

            gas_result = await session.execute(
                select(
                    func.sum(Transaction.gas_used),
                    func.avg(Transaction.gas_used)
                )
                .where(Transaction.sender == address)
            )
            gas_row = gas_result.first()
            gas_used_total = gas_row[0] or 0
            gas_used_avg = gas_row[1] or 0

            # Failed transaction ratio
            failed_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(Transaction.sender == address, Transaction.status == 'failed'))
            )
            failed_count = failed_result.scalar() or 0
            failed_tx_ratio = failed_count / tx_count_all if tx_count_all > 0 else 0

            # === Token Diversity ===

            # Count unique token denominations
            token_result = await session.execute(
                select(func.count(Transfer.denom.distinct()))
                .where(Transfer.from_address == address)
            )
            num_tokens = token_result.scalar() or 1

            # === Round Number Ratio ===

            # Get all sent amounts and check for round numbers
            amounts_result = await session.execute(
                select(Transfer.amount)
                .where(Transfer.from_address == address)
            )
            amounts = [row[0] for row in amounts_result.all()]

            round_numbers = sum(1 for amt in amounts if self._is_round_number(amt))
            round_number_ratio = round_numbers / len(amounts) if amounts else 0

            # === Balance Features ===

            current_balance = received_volume - sent_volume
            max_balance = current_balance  # Simplified (would need historical data)
            avg_balance = current_balance / 2  # Simplified
            balance_volatility = std_sent  # Simplified
            balance_growth_rate = (current_balance - avg_balance) / max(avg_balance, 1) if avg_balance > 0 else 0

            # === Compile Features ===

            tx_frequency = tx_count_all / days_active if days_active > 0 else 0
            sent_received_ratio = sent_count / max(received_count, 1)
            in_degree = unique_senders
            out_degree = unique_receivers
            degree_centrality = (in_degree + out_degree) / max(unique_counterparties, 1) if unique_counterparties > 0 else 0
            net_flow = received_volume - sent_volume
            volume_ratio = sent_volume / max(received_volume, 1) if received_volume > 0 else 1

            data = {
                # Transaction features
                "tx_count_7d": float(tx_count_7d),
                "tx_count_30d": float(tx_count_30d),
                "tx_count_all": float(tx_count_all),
                "avg_tx_value": float(avg_sent),
                "std_tx_value": float(std_sent),
                "tx_frequency": float(tx_frequency),
                "sent_received_ratio": float(sent_received_ratio),
                "unique_senders": float(unique_senders),
                "unique_receivers": float(unique_receivers),
                "unique_counterparties": float(unique_counterparties),

                # Temporal features
                "hour_entropy": float(hour_entropy),
                "day_entropy": float(day_entropy),
                "days_since_first": float(days_since_first),
                "days_since_last": float(days_since_last),
                "tx_velocity_7d": float(tx_velocity_7d),
                "tx_velocity_30d": float(tx_velocity_30d),
                "active_days_ratio": float(active_days_ratio),
                "avg_time_between_txs": float(avg_time_between),

                # Network features
                "in_degree": float(in_degree),
                "out_degree": float(out_degree),
                "degree_centrality": float(degree_centrality),
                "sent_volume": float(sent_volume),
                "received_volume": float(received_volume),
                "net_flow": float(net_flow),
                "volume_ratio": float(volume_ratio),

                # Balance features
                "current_balance": float(current_balance),
                "max_balance": float(max_balance),
                "balance_volatility": float(balance_volatility),
                "avg_balance": float(avg_balance),
                "balance_growth_rate": float(balance_growth_rate),

                # Token/Activity features
                "num_tokens": float(num_tokens),
                "gas_used_total": float(gas_used_total),
                "gas_used_avg": float(gas_used_avg),
                "failed_tx_ratio": float(failed_tx_ratio),
                "round_number_ratio": float(round_number_ratio),
            }

            logger.log_metric("raw_data_fetched", 1, "address", {
                "tx_count": tx_count_all,
                "features_count": len(data)
            })

            return data

    @staticmethod
    def _calculate_entropy(values: List[int], num_bins: int) -> float:
        """
        Calculate Shannon entropy of value distribution

        Args:
            values: List of integer values
            num_bins: Number of possible bins (e.g., 24 for hours, 7 for days)

        Returns:
            Entropy value (0.0 = completely predictable, higher = more random)
        """
        if not values:
            return 0.0

        # Count occurrences
        counts = Counter(values)

        # Calculate probabilities
        total = len(values)
        probabilities = [counts.get(i, 0) / total for i in range(num_bins)]

        # Calculate entropy
        entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in probabilities)

        return float(entropy)

    @staticmethod
    def _is_round_number(amount: int) -> bool:
        """
        Check if amount is a round number

        Round numbers: multiples of 10^6 (1 BABY), 10^7, 10^8, etc.
        """
        if amount == 0:
            return False

        # Check if divisible by 10^6 (1 BABY in ubbn)
        for power in [6, 7, 8, 9]:
            divisor = 10 ** power
            if amount % divisor == 0:
                return True

        return False

    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return self.feature_names.copy()

    async def extract_batch(self, addresses: List[str]) -> Dict[str, Optional[np.ndarray]]:
        """
        Extract features for multiple addresses

        Args:
            addresses: List of addresses

        Returns:
            Dictionary mapping address -> feature vector
        """
        print(f"\n🔬 Extracting features for {len(addresses)} addresses...")
        logger.info(f"Batch feature extraction for {len(addresses)} addresses")

        results = {}

        for i, address in enumerate(addresses):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(addresses)} ({(i+1)/len(addresses)*100:.1f}%)")

            features = await self.extract(address)
            results[address] = features

        successful = sum(1 for v in results.values() if v is not None)
        print(f"  ✓ Successfully extracted features for {successful}/{len(addresses)} addresses")

        return results


print("✓ ML feature extractor loaded successfully!")
print("="*80)
