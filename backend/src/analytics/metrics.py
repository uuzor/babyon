"""
Network Metrics Calculator
Calculates on-chain metrics like transaction volume, active addresses, network growth
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, distinct
from sqlalchemy.sql import text

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import Block, Transaction, Transfer, AddressMetadata

logger = DebugLogger("metrics")

print("="*80)
print("📊 Loading Network Metrics Calculator")
print("="*80)


class NetworkMetrics:
    """
    Calculate network-wide metrics and statistics

    Features:
    - Transaction volume metrics
    - Active address tracking
    - Network growth metrics
    - Gas usage analytics
    - Transfer volume tracking
    """

    def __init__(self, db: Database):
        """Initialize metrics calculator"""
        print("\n" + "="*80)
        print("📊 Initializing Network Metrics Calculator")
        print("="*80)

        self.db = db

        logger.log_startup("NetworkMetrics", {
            "features": ["transaction_volume", "active_addresses", "network_growth", "gas_analytics"]
        })

        print("✓ Network metrics calculator initialized")
        print("="*80 + "\n")

    async def get_transaction_metrics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get transaction metrics for a time period

        Args:
            from_date: Start date (default: 24 hours ago)
            to_date: End date (default: now)

        Returns:
            Transaction metrics
        """
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=1)
        if not to_date:
            to_date = datetime.utcnow()

        logger.info(f"📊 Calculating transaction metrics from {from_date} to {to_date}...")
        print(f"\n📊 Transaction Metrics")
        print("="*80)
        print(f"Period: {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}")

        async with self.db.get_session() as session:
            # Total transactions
            total_tx_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(
                    Transaction.timestamp >= from_date,
                    Transaction.timestamp <= to_date
                ))
            )
            total_tx = total_tx_result.scalar() or 0

            # Successful vs failed
            success_result = await session.execute(
                select(func.count(Transaction.hash))
                .where(and_(
                    Transaction.timestamp >= from_date,
                    Transaction.timestamp <= to_date,
                    Transaction.status == 'success'
                ))
            )
            successful_tx = success_result.scalar() or 0
            failed_tx = total_tx - successful_tx

            # Gas metrics
            gas_result = await session.execute(
                select(
                    func.sum(Transaction.gas_used),
                    func.avg(Transaction.gas_used),
                    func.max(Transaction.gas_used),
                    func.sum(Transaction.gas_wanted)
                )
                .where(and_(
                    Transaction.timestamp >= from_date,
                    Transaction.timestamp <= to_date
                ))
            )
            gas_stats = gas_result.first()

            # Time-based metrics
            duration_seconds = (to_date - from_date).total_seconds()
            duration_hours = duration_seconds / 3600
            tx_per_hour = total_tx / duration_hours if duration_hours > 0 else 0

        metrics = {
            "period_start": from_date,
            "period_end": to_date,
            "total_transactions": total_tx,
            "successful_transactions": successful_tx,
            "failed_transactions": failed_tx,
            "success_rate": (successful_tx / total_tx * 100) if total_tx > 0 else 0,
            "gas_used_total": gas_stats[0] or 0,
            "gas_used_avg": gas_stats[1] or 0,
            "gas_used_max": gas_stats[2] or 0,
            "gas_wanted_total": gas_stats[3] or 0,
            "gas_efficiency": ((gas_stats[0] / gas_stats[3]) * 100) if gas_stats[3] and gas_stats[3] > 0 else 0,
            "transactions_per_hour": tx_per_hour
        }

        # Display
        print(f"\n📈 Volume:")
        print(f"   Total transactions: {total_tx:,}")
        print(f"   Successful: {successful_tx:,} ({metrics['success_rate']:.1f}%)")
        print(f"   Failed: {failed_tx:,}")
        print(f"   Tx/hour: {tx_per_hour:.1f}")

        print(f"\n⛽ Gas Metrics:")
        print(f"   Total gas used: {metrics['gas_used_total']:,}")
        print(f"   Average gas used: {metrics['gas_used_avg']:,.0f}")
        print(f"   Max gas used: {metrics['gas_used_max']:,}")
        print(f"   Gas efficiency: {metrics['gas_efficiency']:.1f}%")

        print("="*80 + "\n")

        logger.log_metric("transaction_metrics_calculated", total_tx, "transactions", metrics)

        return metrics

    async def get_active_addresses(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get active address metrics

        Args:
            from_date: Start date (default: 24 hours ago)
            to_date: End date (default: now)

        Returns:
            Active address metrics
        """
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=1)
        if not to_date:
            to_date = datetime.utcnow()

        logger.info(f"👥 Calculating active addresses from {from_date} to {to_date}...")
        print(f"\n👥 Active Addresses")
        print("="*80)
        print(f"Period: {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}")

        async with self.db.get_session() as session:
            # Active senders
            senders_result = await session.execute(
                select(func.count(Transaction.sender.distinct()))
                .where(and_(
                    Transaction.timestamp >= from_date,
                    Transaction.timestamp <= to_date,
                    Transaction.sender.isnot(None)
                ))
            )
            active_senders = senders_result.scalar() or 0

            # Active receivers (from transfers)
            receivers_result = await session.execute(
                select(func.count(Transfer.to_address.distinct()))
                .where(and_(
                    Transfer.timestamp >= from_date,
                    Transfer.timestamp <= to_date
                ))
            )
            active_receivers = receivers_result.scalar() or 0

            # Unique active addresses (senders + receivers, deduplicated)
            # Note: This is an approximation - for exact count we'd need UNION
            unique_active = active_senders + active_receivers  # Upper bound

            # New addresses (first transaction in this period)
            new_addresses_result = await session.execute(
                select(func.count(func.distinct(Transaction.sender)))
                .where(and_(
                    Transaction.timestamp >= from_date,
                    Transaction.timestamp <= to_date,
                    # Subquery: addresses that had NO transactions before from_date
                    ~Transaction.sender.in_(
                        select(Transaction.sender.distinct())
                        .where(Transaction.timestamp < from_date)
                    )
                ))
            )
            new_addresses = new_addresses_result.scalar() or 0

        metrics = {
            "period_start": from_date,
            "period_end": to_date,
            "active_senders": active_senders,
            "active_receivers": active_receivers,
            "unique_active_approx": unique_active,
            "new_addresses": new_addresses
        }

        # Display
        print(f"\n📊 Address Activity:")
        print(f"   Active senders: {active_senders:,}")
        print(f"   Active receivers: {active_receivers:,}")
        print(f"   Total unique (approx): {unique_active:,}")
        print(f"   New addresses: {new_addresses:,}")

        print("="*80 + "\n")

        logger.log_metric("active_addresses_calculated", unique_active, "addresses", metrics)

        return metrics

    async def get_transfer_metrics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        denom: Optional[str] = None
    ) -> Dict:
        """
        Get transfer volume metrics

        Args:
            from_date: Start date (default: 24 hours ago)
            to_date: End date (default: now)
            denom: Token denomination filter (optional)

        Returns:
            Transfer metrics
        """
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=1)
        if not to_date:
            to_date = datetime.utcnow()

        logger.info(f"💸 Calculating transfer metrics from {from_date} to {to_date}...")
        print(f"\n💸 Transfer Volume Metrics")
        print("="*80)
        print(f"Period: {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}")
        if denom:
            print(f"Token: {denom}")

        async with self.db.get_session() as session:
            # Build base query
            base_query = select(
                func.count(Transfer.id),
                func.sum(Transfer.amount),
                func.avg(Transfer.amount),
                func.max(Transfer.amount),
                func.count(Transfer.from_address.distinct()),
                func.count(Transfer.to_address.distinct())
            ).where(and_(
                Transfer.timestamp >= from_date,
                Transfer.timestamp <= to_date
            ))

            if denom:
                base_query = base_query.where(Transfer.denom == denom)

            result = await session.execute(base_query)
            stats = result.first()

            # Get top tokens by volume
            top_tokens_result = await session.execute(
                select(
                    Transfer.denom,
                    func.count(Transfer.id).label('transfer_count'),
                    func.sum(Transfer.amount).label('total_volume')
                )
                .where(and_(
                    Transfer.timestamp >= from_date,
                    Transfer.timestamp <= to_date
                ))
                .group_by(Transfer.denom)
                .order_by(text('total_volume DESC'))
                .limit(10)
            )
            top_tokens = top_tokens_result.all()

        metrics = {
            "period_start": from_date,
            "period_end": to_date,
            "denom_filter": denom,
            "total_transfers": stats[0] or 0,
            "total_volume": stats[1] or 0,
            "average_transfer_size": stats[2] or 0,
            "max_transfer_size": stats[3] or 0,
            "unique_senders": stats[4] or 0,
            "unique_receivers": stats[5] or 0,
            "top_tokens": [
                {
                    "denom": row[0],
                    "transfer_count": row[1],
                    "total_volume": row[2]
                }
                for row in top_tokens
            ]
        }

        # Display
        print(f"\n📊 Transfer Statistics:")
        print(f"   Total transfers: {metrics['total_transfers']:,}")
        print(f"   Total volume: {metrics['total_volume']:,}")
        print(f"   Average size: {metrics['average_transfer_size']:,.0f}")
        print(f"   Max transfer: {metrics['max_transfer_size']:,}")
        print(f"   Unique senders: {metrics['unique_senders']:,}")
        print(f"   Unique receivers: {metrics['unique_receivers']:,}")

        if top_tokens:
            print(f"\n🏆 Top Tokens by Volume:")
            for i, token in enumerate(top_tokens[:5], 1):
                if token[0] == 'ubbn':
                    print(f"   {i}. {token[0]}: {token[2]/1e9:,.2f} BABY ({token[1]:,} transfers)")
                else:
                    print(f"   {i}. {token[0]}: {token[2]:,} ({token[1]:,} transfers)")

        print("="*80 + "\n")

        logger.log_metric("transfer_metrics_calculated", metrics['total_transfers'], "transfers", metrics)

        return metrics

    async def get_network_growth(
        self,
        days: int = 30,
        interval_days: int = 1
    ) -> List[Dict]:
        """
        Get network growth metrics over time

        Args:
            days: Number of days to analyze
            interval_days: Sampling interval

        Returns:
            List of daily growth metrics
        """
        logger.info(f"📈 Calculating network growth over last {days} days...")
        print(f"\n📈 Network Growth Analysis")
        print("="*80)
        print(f"Period: Last {days} days")
        print(f"Interval: {interval_days} day(s)")

        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days)

        growth_data = []

        async with self.db.get_session() as session:
            current = from_date
            interval_delta = timedelta(days=interval_days)

            while current <= to_date:
                next_date = min(current + interval_delta, to_date)

                # Transactions in this interval
                tx_result = await session.execute(
                    select(func.count(Transaction.hash))
                    .where(and_(
                        Transaction.timestamp >= current,
                        Transaction.timestamp < next_date
                    ))
                )
                tx_count = tx_result.scalar() or 0

                # Active addresses
                active_result = await session.execute(
                    select(func.count(Transaction.sender.distinct()))
                    .where(and_(
                        Transaction.timestamp >= current,
                        Transaction.timestamp < next_date,
                        Transaction.sender.isnot(None)
                    ))
                )
                active_addresses = active_result.scalar() or 0

                # Transfer volume
                volume_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.timestamp >= current,
                        Transfer.timestamp < next_date,
                        Transfer.denom == 'ubbn'
                    ))
                )
                volume = volume_result.scalar() or 0

                growth_data.append({
                    "date": current,
                    "transactions": tx_count,
                    "active_addresses": active_addresses,
                    "transfer_volume_ubbn": volume
                })

                current = next_date

        # Calculate growth rates
        for i in range(1, len(growth_data)):
            prev = growth_data[i-1]
            curr = growth_data[i]

            curr["tx_growth_pct"] = ((curr["transactions"] - prev["transactions"]) / prev["transactions"] * 100) if prev["transactions"] > 0 else 0
            curr["address_growth_pct"] = ((curr["active_addresses"] - prev["active_addresses"]) / prev["active_addresses"] * 100) if prev["active_addresses"] > 0 else 0
            curr["volume_growth_pct"] = ((curr["transfer_volume_ubbn"] - prev["transfer_volume_ubbn"]) / prev["transfer_volume_ubbn"] * 100) if prev["transfer_volume_ubbn"] > 0 else 0

        # Display summary
        print(f"\n📊 Growth Summary:")
        print(f"   Total data points: {len(growth_data)}")
        if len(growth_data) >= 2:
            first = growth_data[0]
            last = growth_data[-1]

            print(f"\n   First day ({first['date'].strftime('%Y-%m-%d')}):")
            print(f"     Transactions: {first['transactions']:,}")
            print(f"     Active addresses: {first['active_addresses']:,}")
            print(f"     Volume: {first['transfer_volume_ubbn']/1e9:,.2f} BABY")

            print(f"\n   Last day ({last['date'].strftime('%Y-%m-%d')}):")
            print(f"     Transactions: {last['transactions']:,}")
            print(f"     Active addresses: {last['active_addresses']:,}")
            print(f"     Volume: {last['transfer_volume_ubbn']/1e9:,.2f} BABY")

            if 'tx_growth_pct' in last:
                print(f"\n   Latest growth rates:")
                print(f"     Transactions: {last['tx_growth_pct']:+.1f}%")
                print(f"     Active addresses: {last['address_growth_pct']:+.1f}%")
                print(f"     Volume: {last['volume_growth_pct']:+.1f}%")

        print("="*80 + "\n")

        logger.log_metric("network_growth_calculated", len(growth_data), "datapoints", {
            "days": days,
            "interval_days": interval_days
        })

        return growth_data

    async def get_blockchain_overview(self) -> Dict:
        """
        Get comprehensive blockchain overview

        Returns:
            Blockchain statistics overview
        """
        logger.info("📊 Generating blockchain overview...")
        print(f"\n{'='*80}")
        print("📊 BLOCKCHAIN OVERVIEW")
        print(f"{'='*80}")

        async with self.db.get_session() as session:
            # Block stats
            block_stats_result = await session.execute(
                select(
                    func.count(Block.height),
                    func.max(Block.height),
                    func.min(Block.timestamp),
                    func.max(Block.timestamp)
                )
            )
            block_stats = block_stats_result.first()

            # Transaction stats
            tx_stats_result = await session.execute(
                select(
                    func.count(Transaction.hash),
                    func.count(Transaction.hash).filter(Transaction.status == 'success'),
                    func.sum(Transaction.gas_used)
                )
            )
            tx_stats = tx_stats_result.first()

            # Transfer stats
            transfer_stats_result = await session.execute(
                select(
                    func.count(Transfer.id),
                    func.count(Transfer.denom.distinct()),
                    func.sum(Transfer.amount).filter(Transfer.denom == 'ubbn')
                )
            )
            transfer_stats = transfer_stats_result.first()

            # Address stats
            address_stats_result = await session.execute(
                select(
                    func.count(Transaction.sender.distinct()),
                    func.count(AddressMetadata.address),
                    func.count(AddressMetadata.address).filter(AddressMetadata.label_type.isnot(None))
                )
            )
            address_stats = address_stats_result.first()

        # Calculate chain age
        chain_age_days = (block_stats[3] - block_stats[2]).days if (block_stats[2] and block_stats[3]) else 0

        overview = {
            "generated_at": datetime.utcnow(),
            "blocks": {
                "total": block_stats[0] or 0,
                "latest_height": block_stats[1] or 0,
                "first_block_time": block_stats[2],
                "latest_block_time": block_stats[3],
                "chain_age_days": chain_age_days
            },
            "transactions": {
                "total": tx_stats[0] or 0,
                "successful": tx_stats[1] or 0,
                "failed": (tx_stats[0] or 0) - (tx_stats[1] or 0),
                "success_rate": ((tx_stats[1] / tx_stats[0]) * 100) if tx_stats[0] and tx_stats[0] > 0 else 0,
                "total_gas_used": tx_stats[2] or 0
            },
            "transfers": {
                "total": transfer_stats[0] or 0,
                "unique_tokens": transfer_stats[1] or 0,
                "total_volume_ubbn": transfer_stats[2] or 0
            },
            "addresses": {
                "unique_active": address_stats[0] or 0,
                "in_metadata_table": address_stats[1] or 0,
                "labeled": address_stats[2] or 0
            }
        }

        # Display
        print(f"\n⛓️  Blockchain:")
        print(f"   Total blocks: {overview['blocks']['total']:,}")
        print(f"   Latest height: {overview['blocks']['latest_height']:,}")
        print(f"   Chain age: {chain_age_days} days")

        print(f"\n📊 Transactions:")
        print(f"   Total: {overview['transactions']['total']:,}")
        print(f"   Successful: {overview['transactions']['successful']:,} ({overview['transactions']['success_rate']:.1f}%)")
        print(f"   Failed: {overview['transactions']['failed']:,}")
        print(f"   Total gas: {overview['transactions']['total_gas_used']:,}")

        print(f"\n💸 Transfers:")
        print(f"   Total transfers: {overview['transfers']['total']:,}")
        print(f"   Unique tokens: {overview['transfers']['unique_tokens']}")
        print(f"   Total BABY volume: {overview['transfers']['total_volume_ubbn']/1e9:,.2f}")

        print(f"\n👥 Addresses:")
        print(f"   Unique active: {overview['addresses']['unique_active']:,}")
        print(f"   In metadata: {overview['addresses']['in_metadata_table']:,}")
        print(f"   Labeled: {overview['addresses']['labeled']:,} ({(overview['addresses']['labeled']/overview['addresses']['in_metadata_table']*100) if overview['addresses']['in_metadata_table'] > 0 else 0:.1f}%)")

        print(f"{'='*80}\n")

        logger.log_metric("blockchain_overview_generated", 1, "overview", overview)

        return overview


print("✓ Network metrics calculator loaded successfully!")
print("="*80)
