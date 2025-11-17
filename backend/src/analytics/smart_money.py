"""
Smart Money Detection and Scoring
Identifies and scores addresses demonstrating sophisticated trading behavior
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import (
    Transaction, Transfer, AddressMetadata, SmartMoneyIndicator
)

logger = DebugLogger("smart_money")

print("="*80)
print("🧠 Loading Smart Money Detection System")
print("="*80)


class SmartMoneyScorer:
    """
    Detect and score 'smart money' addresses

    Smart money indicators:
    - High profitability
    - Early adoption patterns
    - Large volume
    - Consistent win rate
    - Network influence

    Composite score: 0-100
    """

    # Score weights
    WEIGHTS = {
        "profitability": 0.30,     # 30%
        "early_adoption": 0.20,    # 20%
        "volume": 0.25,            # 25%
        "win_rate": 0.15,          # 15%
        "influence": 0.10          # 10%
    }

    def __init__(self, db: Database):
        """Initialize smart money scorer"""
        print("\n" + "="*80)
        print("🧠 Initializing Smart Money Scorer")
        print("="*80)

        self.db = db

        logger.log_startup("SmartMoneyScorer", {
            "weights": self.WEIGHTS,
            "max_score": 100
        })

        print("✓ Score weights:")
        for metric, weight in self.WEIGHTS.items():
            print(f"  • {metric}: {weight*100:.0f}%")
        print("="*80 + "\n")

    async def calculate_profitability_score(self, address: str) -> Tuple[float, Dict]:
        """
        Calculate profitability score (0-100)

        Based on:
        - Current holdings vs total invested
        - Growth rate
        - Portfolio performance

        Args:
            address: Babylon address

        Returns:
            (score, details dict)
        """
        logger.debug(f"💹 Calculating profitability for {address[:16]}...")

        async with self.db.get_session() as session:
            # Get all transfers for BABY token
            received_result = await session.execute(
                select(func.sum(Transfer.amount))
                .where(and_(
                    Transfer.to_address == address,
                    Transfer.denom == 'ubbn'
                ))
            )
            total_received = received_result.scalar() or 0

            sent_result = await session.execute(
                select(func.sum(Transfer.amount))
                .where(and_(
                    Transfer.from_address == address,
                    Transfer.denom == 'ubbn'
                ))
            )
            total_sent = sent_result.scalar() or 0

            current_balance = total_received - total_sent

            # Simple profitability metric: current holdings relative to total flow
            total_flow = total_received + total_sent
            if total_flow > 0:
                # If balance is positive and growing, score higher
                balance_ratio = current_balance / total_received if total_received > 0 else 0

                # Score: addresses that hold more than they spent score higher
                # 0% held = 0 score, 100% held = 100 score
                score = min(balance_ratio * 100, 100)
            else:
                score = 0

        details = {
            "total_received": total_received,
            "total_sent": total_sent,
            "current_balance": current_balance,
            "balance_ratio": (current_balance / total_received * 100) if total_received > 0 else 0
        }

        logger.debug(f"  Profitability score: {score:.1f}/100")

        return score, details

    async def calculate_early_adoption_score(self, address: str) -> Tuple[float, Dict]:
        """
        Calculate early adoption score (0-100)

        Based on:
        - How early the address became active
        - Participation in early blocks/transactions

        Args:
            address: Babylon address

        Returns:
            (score, details dict)
        """
        logger.debug(f"🚀 Calculating early adoption for {address[:16]}...")

        async with self.db.get_session() as session:
            # Get first transaction timestamp
            first_tx_result = await session.execute(
                select(Transaction.timestamp, Transaction.block_height)
                .where(Transaction.sender == address)
                .order_by(Transaction.timestamp.asc())
                .limit(1)
            )
            first_tx = first_tx_result.first()

            if not first_tx:
                return 0, {"reason": "no_transactions"}

            first_timestamp = first_tx[0]
            first_height = first_tx[1]

            # Get earliest timestamp in database
            earliest_result = await session.execute(
                select(func.min(Transaction.timestamp), func.min(Transaction.block_height))
            )
            earliest = earliest_result.first()
            earliest_timestamp = earliest[0]
            earliest_height = earliest[1]

            # Get latest timestamp
            latest_result = await session.execute(
                select(func.max(Transaction.timestamp), func.max(Transaction.block_height))
            )
            latest = latest_result.first()
            latest_timestamp = latest[0]
            latest_height = latest[1]

            if not earliest_timestamp or not latest_timestamp:
                return 0, {"reason": "insufficient_data"}

            # Calculate how early (as percentage of chain history)
            chain_duration = (latest_timestamp - earliest_timestamp).total_seconds()
            time_since_start = (first_timestamp - earliest_timestamp).total_seconds()

            if chain_duration > 0:
                early_pct = (1 - (time_since_start / chain_duration)) * 100
                score = max(0, min(early_pct, 100))  # Clamp to 0-100
            else:
                score = 0

        details = {
            "first_tx_timestamp": first_timestamp,
            "first_tx_height": first_height,
            "chain_start": earliest_timestamp,
            "joined_at_pct": 100 - score  # What % into chain history they joined
        }

        logger.debug(f"  Early adoption score: {score:.1f}/100")

        return score, details

    async def calculate_volume_score(self, address: str) -> Tuple[float, Dict]:
        """
        Calculate volume score (0-100)

        Based on:
        - Total transaction volume
        - Relative to network average

        Args:
            address: Babylon address

        Returns:
            (score, details dict)
        """
        logger.debug(f"💰 Calculating volume for {address[:16]}...")

        async with self.db.get_session() as session:
            # Address volume
            addr_volume_result = await session.execute(
                select(func.sum(Transfer.amount))
                .where(and_(
                    Transfer.from_address == address,
                    Transfer.denom == 'ubbn'
                ))
            )
            addr_volume = addr_volume_result.scalar() or 0

            # Network average volume
            avg_volume_result = await session.execute(
                select(func.avg(func.sum(Transfer.amount)))
                .where(Transfer.denom == 'ubbn')
                .group_by(Transfer.from_address)
            )
            avg_volume = avg_volume_result.scalar() or 0

            # Score based on how much above average
            if avg_volume > 0:
                volume_ratio = addr_volume / avg_volume

                # Logarithmic scoring: 1x avg = 50, 10x avg = 75, 100x avg = 100
                import math
                if volume_ratio >= 1:
                    score = 50 + (min(math.log10(volume_ratio), 2) / 2 * 50)
                else:
                    score = volume_ratio * 50  # Below average scales linearly
            else:
                score = 0

        details = {
            "address_volume": addr_volume,
            "network_avg_volume": avg_volume,
            "volume_ratio": (addr_volume / avg_volume) if avg_volume > 0 else 0
        }

        logger.debug(f"  Volume score: {score:.1f}/100")

        return score, details

    async def calculate_win_rate_score(self, address: str) -> Tuple[float, Dict]:
        """
        Calculate win rate score (0-100)

        Based on:
        - Ratio of successful to total transactions
        - Consistency of success

        Args:
            address: Babylon address

        Returns:
            (score, details dict)
        """
        logger.debug(f"✓ Calculating win rate for {address[:16]}...")

        async with self.db.get_session() as session:
            # Total transactions
            total_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(Transaction.sender == address)
            )
            total_tx = total_result.scalar() or 0

            # Successful transactions
            success_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(
                    Transaction.sender == address,
                    Transaction.status == 'success'
                ))
            )
            successful_tx = success_result.scalar() or 0

            if total_tx > 0:
                win_rate = (successful_tx / total_tx) * 100
                score = win_rate  # Direct mapping: 100% success = 100 score
            else:
                score = 0

        details = {
            "total_transactions": total_tx,
            "successful_transactions": successful_tx,
            "failed_transactions": total_tx - successful_tx,
            "win_rate_pct": score
        }

        logger.debug(f"  Win rate score: {score:.1f}/100")

        return score, details

    async def calculate_influence_score(self, address: str) -> Tuple[float, Dict]:
        """
        Calculate influence score (0-100)

        Based on:
        - Number of unique counterparties
        - Network connections

        Args:
            address: Babylon address

        Returns:
            (score, details dict)
        """
        logger.debug(f"🌐 Calculating influence for {address[:16]}...")

        async with self.db.get_session() as session:
            # Unique receivers (out-degree)
            receivers_result = await session.execute(
                select(func.count(Transfer.to_address.distinct()))
                .where(Transfer.from_address == address)
            )
            unique_receivers = receivers_result.scalar() or 0

            # Unique senders (in-degree)
            senders_result = await session.execute(
                select(func.count(Transfer.from_address.distinct()))
                .where(Transfer.to_address == address)
            )
            unique_senders = senders_result.scalar() or 0

            # Total connections
            total_connections = unique_receivers + unique_senders

            # Score based on number of connections
            # Logarithmic: 10 connections = 50, 100 = 75, 1000 = 100
            import math
            if total_connections > 0:
                score = min(math.log10(total_connections + 1) / 3 * 100, 100)
            else:
                score = 0

        details = {
            "unique_receivers": unique_receivers,
            "unique_senders": unique_senders,
            "total_connections": total_connections
        }

        logger.debug(f"  Influence score: {score:.1f}/100")

        return score, details

    async def calculate_smart_money_score(self, address: str) -> Tuple[int, Dict]:
        """
        Calculate composite smart money score (0-100)

        Args:
            address: Babylon address

        Returns:
            (composite_score, all_details dict)
        """
        logger.info(f"🧠 Calculating smart money score for {address[:16]}...")
        print(f"\n🧠 Smart Money Analysis: {address[:16]}...")
        print("="*80)

        # Calculate individual scores
        profitability_score, profitability_details = await self.calculate_profitability_score(address)
        early_adoption_score, early_adoption_details = await self.calculate_early_adoption_score(address)
        volume_score, volume_details = await self.calculate_volume_score(address)
        win_rate_score, win_rate_details = await self.calculate_win_rate_score(address)
        influence_score, influence_details = await self.calculate_influence_score(address)

        # Calculate weighted composite score
        composite_score = (
            profitability_score * self.WEIGHTS["profitability"] +
            early_adoption_score * self.WEIGHTS["early_adoption"] +
            volume_score * self.WEIGHTS["volume"] +
            win_rate_score * self.WEIGHTS["win_rate"] +
            influence_score * self.WEIGHTS["influence"]
        )

        composite_score = int(round(composite_score))

        # Compile all details
        all_details = {
            "address": address,
            "composite_score": composite_score,
            "profitability_score": profitability_score,
            "early_adoption_score": early_adoption_score,
            "volume_score": volume_score,
            "win_rate_score": win_rate_score,
            "influence_score": influence_score,
            "profitability": profitability_details,
            "early_adoption": early_adoption_details,
            "volume": volume_details,
            "win_rate": win_rate_details,
            "influence": influence_details,
            "calculated_at": datetime.utcnow()
        }

        # Display
        print(f"\n📊 Component Scores:")
        print(f"   💹 Profitability: {profitability_score:.1f}/100 (weight: {self.WEIGHTS['profitability']*100:.0f}%)")
        print(f"   🚀 Early Adoption: {early_adoption_score:.1f}/100 (weight: {self.WEIGHTS['early_adoption']*100:.0f}%)")
        print(f"   💰 Volume: {volume_score:.1f}/100 (weight: {self.WEIGHTS['volume']*100:.0f}%)")
        print(f"   ✓ Win Rate: {win_rate_score:.1f}/100 (weight: {self.WEIGHTS['win_rate']*100:.0f}%)")
        print(f"   🌐 Influence: {influence_score:.1f}/100 (weight: {self.WEIGHTS['influence']*100:.0f}%)")

        print(f"\n🎯 Composite Smart Money Score: {composite_score}/100")

        if composite_score >= 75:
            print(f"   🌟 Rating: ELITE SMART MONEY")
        elif composite_score >= 60:
            print(f"   ⭐ Rating: SMART MONEY")
        elif composite_score >= 40:
            print(f"   ✓ Rating: ABOVE AVERAGE")
        else:
            print(f"   • Rating: AVERAGE")

        print("="*80 + "\n")

        logger.log_metric("smart_money_score_calculated", composite_score, "score", {
            "address": address[:16],
            "composite_score": composite_score
        })

        return composite_score, all_details

    async def save_smart_money_score(self, address: str, score: int, details: Dict):
        """
        Save smart money score to database

        Args:
            address: Babylon address
            score: Composite score (0-100)
            details: Score details
        """
        logger.debug(f"💾 Saving smart money score for {address[:16]}...")

        async with self.db.get_session() as session:
            # Check if exists
            result = await session.execute(
                select(SmartMoneyIndicator)
                .where(SmartMoneyIndicator.address == address)
            )
            indicator = result.scalar_one_or_none()

            if indicator:
                # Update
                indicator.score = score
                indicator.profitability_score = details['profitability_score']
                indicator.early_adoption_score = details['early_adoption_score']
                indicator.volume_score = details['volume_score']
                indicator.win_rate = details['win_rate']['win_rate_pct'] if 'win_rate' in details else 0
                indicator.influence_score = details['influence_score']
                indicator.total_volume = details['volume']['address_volume']
                indicator.metrics = {
                    "profitability": details['profitability'],
                    "early_adoption": details['early_adoption'],
                    "volume": details['volume'],
                    "win_rate": details['win_rate'],
                    "influence": details['influence']
                }
                indicator.updated_at = datetime.utcnow()
            else:
                # Create
                indicator = SmartMoneyIndicator(
                    address=address,
                    score=score,
                    profitability_score=details['profitability_score'],
                    early_adoption_score=details['early_adoption_score'],
                    volume_score=details['volume_score'],
                    win_rate=details['win_rate']['win_rate_pct'] if 'win_rate' in details else 0,
                    influence_score=details['influence_score'],
                    total_volume=details['volume']['address_volume'],
                    total_trades=details['win_rate']['total_transactions'] if 'win_rate' in details else 0,
                    profitable_trades=details['win_rate']['successful_transactions'] if 'win_rate' in details else 0,
                    metrics={
                        "profitability": details['profitability'],
                        "early_adoption": details['early_adoption'],
                        "volume": details['volume'],
                        "win_rate": details['win_rate'],
                        "influence": details['influence']
                    }
                )
                session.add(indicator)

            await session.commit()

        logger.info(f"✓ Smart money score saved for {address[:16]}")

    async def get_top_smart_money(self, limit: int = 100, min_score: int = 50) -> List[Dict]:
        """
        Get top smart money addresses

        Args:
            limit: Number of addresses to return
            min_score: Minimum smart money score

        Returns:
            List of top smart money addresses
        """
        logger.info(f"🏆 Finding top {limit} smart money addresses (min score: {min_score})...")
        print(f"\n🏆 Top Smart Money Addresses")
        print("="*80)
        print(f"Minimum score: {min_score}/100")
        print(f"Limit: {limit}")

        async with self.db.get_session() as session:
            result = await session.execute(
                select(SmartMoneyIndicator)
                .where(SmartMoneyIndicator.score >= min_score)
                .order_by(desc(SmartMoneyIndicator.score))
                .limit(limit)
            )
            indicators = result.scalars().all()

        print(f"\n✓ Found {len(indicators)} smart money addresses")
        print("-"*80)

        top_addresses = []
        for i, ind in enumerate(indicators[:20], 1):  # Show top 20
            # Get label if available
            async with self.db.get_session() as session:
                label_result = await session.execute(
                    select(AddressMetadata.label_type)
                    .where(AddressMetadata.address == ind.address)
                )
                label_row = label_result.first()
                label = label_row[0] if label_row else None

            addr_info = {
                "rank": i,
                "address": ind.address,
                "score": ind.score,
                "label": label,
                "profitability_score": ind.profitability_score,
                "early_adoption_score": ind.early_adoption_score,
                "volume_score": ind.volume_score,
                "win_rate": ind.win_rate,
                "influence_score": ind.influence_score,
                "total_volume": ind.total_volume
            }

            top_addresses.append(addr_info)

            # Display
            label_str = f"({label.upper()})" if label else ""
            print(f"  {i:3}. {ind.address[:16]}... Score: {ind.score}/100 {label_str}")
            print(f"       💹 Profit: {ind.profitability_score:.0f} | 🚀 Early: {ind.early_adoption_score:.0f} | 💰 Vol: {ind.volume_score:.0f} | ✓ Win: {ind.win_rate:.0f}% | 🌐 Influence: {ind.influence_score:.0f}")

        print("="*80 + "\n")

        logger.log_metric("top_smart_money_retrieved", len(top_addresses), "addresses", {
            "min_score": min_score,
            "limit": limit
        })

        return top_addresses


print("✓ Smart money detection system loaded successfully!")
print("="*80)
