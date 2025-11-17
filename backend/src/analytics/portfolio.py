"""
Portfolio Tracking and Analysis
Tracks token holdings, calculates portfolio value, and identifies position changes
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.sql import text

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import Transfer, AddressMetadata, Transaction

logger = DebugLogger("portfolio")

print("="*80)
print("💼 Loading Portfolio Tracker")
print("="*80)


class PortfolioTracker:
    """
    Track and analyze address portfolios

    Features:
    - Current token holdings per address
    - Historical balance tracking
    - Portfolio value calculation
    - Position change detection
    - Profit/loss analysis
    """

    def __init__(self, db: Database):
        """Initialize portfolio tracker"""
        print("\n" + "="*80)
        print("💼 Initializing Portfolio Tracker")
        print("="*80)

        self.db = db

        logger.log_startup("PortfolioTracker", {
            "features": ["holdings", "historical_balance", "pnl_analysis"]
        })

        print("✓ Portfolio tracker initialized")
        print("="*80 + "\n")

    async def get_current_holdings(self, address: str) -> Dict[str, Dict]:
        """
        Get current token holdings for an address

        Args:
            address: Babylon address

        Returns:
            Dict mapping token denom to holding info
        """
        logger.debug(f"💰 Fetching holdings for {address[:16]}...")
        print(f"💰 Analyzing holdings for {address[:16]}...")

        holdings = {}

        async with self.db.get_session() as session:
            # Get all unique tokens this address has interacted with
            tokens_result = await session.execute(
                select(Transfer.denom.distinct())
                .where(or_(
                    Transfer.from_address == address,
                    Transfer.to_address == address
                ))
            )
            tokens = [row[0] for row in tokens_result.all()]

            print(f"  📊 Found {len(tokens)} unique tokens")

            # Calculate balance for each token
            for denom in tokens:
                # Total received
                received_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.to_address == address,
                        Transfer.denom == denom
                    ))
                )
                received = received_result.scalar() or 0

                # Total sent
                sent_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.from_address == address,
                        Transfer.denom == denom
                    ))
                )
                sent = sent_result.scalar() or 0

                # Current balance
                balance = received - sent

                if balance > 0:  # Only include tokens with positive balance
                    # Get first and last transaction timestamps
                    first_tx_result = await session.execute(
                        select(Transfer.timestamp)
                        .where(and_(
                            or_(Transfer.from_address == address, Transfer.to_address == address),
                            Transfer.denom == denom
                        ))
                        .order_by(Transfer.timestamp.asc())
                        .limit(1)
                    )
                    first_tx_row = first_tx_result.first()
                    first_seen = first_tx_row[0] if first_tx_row else None

                    last_tx_result = await session.execute(
                        select(Transfer.timestamp)
                        .where(and_(
                            or_(Transfer.from_address == address, Transfer.to_address == address),
                            Transfer.denom == denom
                        ))
                        .order_by(Transfer.timestamp.desc())
                        .limit(1)
                    )
                    last_tx_row = last_tx_result.first()
                    last_seen = last_tx_row[0] if last_tx_row else None

                    holdings[denom] = {
                        "balance": balance,
                        "received_total": received,
                        "sent_total": sent,
                        "first_seen": first_seen,
                        "last_seen": last_seen,
                        "holding_days": (last_seen - first_seen).days if (first_seen and last_seen) else 0
                    }

                    # Display in human-readable format
                    if denom == 'ubbn':
                        balance_baby = balance / 1e9
                        print(f"  ✓ {denom}: {balance_baby:,.2f} BABY")
                    else:
                        print(f"  ✓ {denom}: {balance:,}")

        logger.log_metric("portfolio_holdings_fetched", len(holdings), "tokens", {
            "address": address[:16],
            "total_tokens": len(holdings)
        })

        print(f"  💼 Total holdings: {len(holdings)} token(s)")

        return holdings

    async def get_historical_balance(
        self,
        address: str,
        denom: str = 'ubbn',
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        interval_hours: int = 24
    ) -> List[Dict]:
        """
        Get historical balance over time

        Args:
            address: Babylon address
            denom: Token denomination (default: ubbn)
            from_date: Start date (default: first transaction)
            to_date: End date (default: now)
            interval_hours: Sampling interval in hours (default: 24)

        Returns:
            List of balance snapshots over time
        """
        logger.debug(f"📈 Fetching historical balance for {address[:16]}...")
        print(f"\n📈 Calculating historical balance for {address[:16]}...")
        print(f"  Token: {denom}")
        print(f"  Interval: {interval_hours} hours")

        async with self.db.get_session() as session:
            # Get date range
            if not from_date or not to_date:
                date_range_result = await session.execute(
                    select(
                        func.min(Transfer.timestamp),
                        func.max(Transfer.timestamp)
                    )
                    .where(and_(
                        or_(Transfer.from_address == address, Transfer.to_address == address),
                        Transfer.denom == denom
                    ))
                )
                date_range = date_range_result.first()
                from_date = from_date or date_range[0] or datetime.utcnow() - timedelta(days=30)
                to_date = to_date or date_range[1] or datetime.utcnow()

            print(f"  Date range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")

            # Generate time intervals
            current = from_date
            interval_delta = timedelta(hours=interval_hours)
            snapshots = []

            while current <= to_date:
                # Calculate balance at this point in time
                received_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.to_address == address,
                        Transfer.denom == denom,
                        Transfer.timestamp <= current
                    ))
                )
                received = received_result.scalar() or 0

                sent_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.from_address == address,
                        Transfer.denom == denom,
                        Transfer.timestamp <= current
                    ))
                )
                sent = sent_result.scalar() or 0

                balance = received - sent

                snapshots.append({
                    "timestamp": current,
                    "balance": balance,
                    "received_total": received,
                    "sent_total": sent
                })

                current += interval_delta

            print(f"  ✓ Generated {len(snapshots)} balance snapshots")

            # Log sample data points
            if snapshots:
                first = snapshots[0]
                last = snapshots[-1]
                if denom == 'ubbn':
                    print(f"  📊 First: {first['balance']/1e9:,.2f} BABY at {first['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    print(f"  📊 Last: {last['balance']/1e9:,.2f} BABY at {last['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    balance_change = (last['balance'] - first['balance']) / 1e9
                    print(f"  📈 Change: {balance_change:+,.2f} BABY")

        logger.log_metric("historical_balance_calculated", len(snapshots), "snapshots", {
            "address": address[:16],
            "denom": denom,
            "interval_hours": interval_hours
        })

        return snapshots

    async def calculate_pnl(
        self,
        address: str,
        denom: str = 'ubbn',
        cost_basis_method: str = 'fifo'  # 'fifo', 'lifo', 'average'
    ) -> Dict:
        """
        Calculate profit/loss for an address's holdings

        Args:
            address: Babylon address
            denom: Token denomination
            cost_basis_method: Method for calculating cost basis

        Returns:
            PnL analysis including realized and unrealized gains
        """
        logger.debug(f"💹 Calculating PnL for {address[:16]}...")
        print(f"\n💹 Calculating Profit/Loss for {address[:16]}...")
        print(f"  Token: {denom}")
        print(f"  Cost basis method: {cost_basis_method.upper()}")

        async with self.db.get_session() as session:
            # Get all transfers for this address and token, ordered by time
            transfers_result = await session.execute(
                select(Transfer)
                .where(and_(
                    or_(Transfer.from_address == address, Transfer.to_address == address),
                    Transfer.denom == denom
                ))
                .order_by(Transfer.timestamp.asc())
            )
            transfers = transfers_result.scalars().all()

            print(f"  📊 Analyzing {len(transfers)} transfers...")

            # Track acquisitions and disposals
            acquisitions = []  # When address received tokens
            disposals = []      # When address sent tokens

            for transfer in transfers:
                if transfer.to_address == address:
                    # Acquisition
                    acquisitions.append({
                        "timestamp": transfer.timestamp,
                        "amount": transfer.amount,
                        "tx_hash": transfer.tx_hash,
                        "from": transfer.from_address
                    })
                elif transfer.from_address == address:
                    # Disposal
                    disposals.append({
                        "timestamp": transfer.timestamp,
                        "amount": transfer.amount,
                        "tx_hash": transfer.tx_hash,
                        "to": transfer.to_address
                    })

            print(f"  ✓ Acquisitions: {len(acquisitions)}")
            print(f"  ✓ Disposals: {len(disposals)}")

            # Calculate current holdings
            total_acquired = sum(a['amount'] for a in acquisitions)
            total_disposed = sum(d['amount'] for d in disposals)
            current_holding = total_acquired - total_disposed

            # Note: For full PnL calculation, we would need price data
            # For now, we calculate quantity-based metrics

            pnl_data = {
                "address": address,
                "denom": denom,
                "total_acquired": total_acquired,
                "total_disposed": total_disposed,
                "current_holding": current_holding,
                "num_acquisitions": len(acquisitions),
                "num_disposals": len(disposals),
                "avg_acquisition_size": total_acquired / len(acquisitions) if acquisitions else 0,
                "avg_disposal_size": total_disposed / len(disposals) if disposals else 0,
                "holding_period_days": (disposals[-1]['timestamp'] - acquisitions[0]['timestamp']).days if (acquisitions and disposals) else None,
                "cost_basis_method": cost_basis_method,
                # Note: realized_pnl and unrealized_pnl would require price data
                "note": "Price data required for USD-denominated PnL calculation"
            }

            # Display summary
            if denom == 'ubbn':
                print(f"\n  💼 Portfolio Summary:")
                print(f"     Total acquired: {total_acquired/1e9:,.2f} BABY")
                print(f"     Total disposed: {total_disposed/1e9:,.2f} BABY")
                print(f"     Current holding: {current_holding/1e9:,.2f} BABY")
                print(f"     Avg buy size: {pnl_data['avg_acquisition_size']/1e9:,.2f} BABY")
                print(f"     Avg sell size: {pnl_data['avg_disposal_size']/1e9:,.2f} BABY")

        logger.log_metric("pnl_calculated", 1, "address", pnl_data)

        return pnl_data

    async def get_portfolio_summary(self, address: str) -> Dict:
        """
        Get comprehensive portfolio summary

        Args:
            address: Babylon address

        Returns:
            Complete portfolio overview
        """
        logger.info(f"📊 Generating portfolio summary for {address[:16]}...")
        print(f"\n{'='*80}")
        print(f"📊 PORTFOLIO SUMMARY: {address[:16]}...")
        print(f"{'='*80}")

        # Get current holdings
        holdings = await self.get_current_holdings(address)

        # Get transaction stats
        async with self.db.get_session() as session:
            # Transaction count
            tx_count_result = await session.execute(
                select(func.count(Transaction.hash.distinct()))
                .where(Transaction.sender == address)
            )
            tx_count = tx_count_result.scalar() or 0

            # Transfer count
            transfers_result = await session.execute(
                select(
                    func.count(Transfer.id),
                    func.min(Transfer.timestamp),
                    func.max(Transfer.timestamp)
                )
                .where(or_(
                    Transfer.from_address == address,
                    Transfer.to_address == address
                ))
            )
            transfer_stats = transfers_result.first()
            transfer_count = transfer_stats[0] or 0
            first_activity = transfer_stats[1]
            last_activity = transfer_stats[2]

            # Get address metadata
            metadata_result = await session.execute(
                select(AddressMetadata)
                .where(AddressMetadata.address == address)
            )
            metadata = metadata_result.scalar_one_or_none()

        # Calculate age
        age_days = (last_activity - first_activity).days if (first_activity and last_activity) else 0

        summary = {
            "address": address,
            "holdings": holdings,
            "num_tokens": len(holdings),
            "total_transactions": tx_count,
            "total_transfers": transfer_count,
            "first_activity": first_activity,
            "last_activity": last_activity,
            "age_days": age_days,
            "label": metadata.label_type if metadata else None,
            "label_confidence": metadata.label_confidence if metadata else None,
            "is_active": (datetime.utcnow() - last_activity).days < 7 if last_activity else False
        }

        # Display summary
        print(f"\n📋 Address: {address}")
        print(f"🏷️  Label: {summary['label'].upper() if summary['label'] else 'UNLABELED'}")
        print(f"📅 Age: {age_days} days")
        print(f"📊 Activity: {tx_count:,} transactions, {transfer_count:,} transfers")
        print(f"💼 Holdings: {len(holdings)} token(s)")
        print(f"🟢 Status: {'ACTIVE' if summary['is_active'] else 'INACTIVE'}")

        if holdings:
            print(f"\n💰 Token Holdings:")
            for denom, info in holdings.items():
                if denom == 'ubbn':
                    print(f"   {denom}: {info['balance']/1e9:,.2f} BABY")
                else:
                    print(f"   {denom}: {info['balance']:,}")

        print(f"{'='*80}\n")

        logger.log_metric("portfolio_summary_generated", 1, "address", {
            "address": address[:16],
            "num_tokens": len(holdings),
            "total_transactions": tx_count
        })

        return summary

    async def get_top_holders(self, denom: str = 'ubbn', limit: int = 100) -> List[Dict]:
        """
        Get top token holders

        Args:
            denom: Token denomination
            limit: Number of top holders to return

        Returns:
            List of top holders with balances
        """
        logger.info(f"🏆 Finding top {limit} holders of {denom}...")
        print(f"\n🏆 Finding Top {limit} Holders of {denom.upper()}")
        print("="*80)

        async with self.db.get_session() as session:
            # Calculate balances for all addresses
            # This is a complex query - we need to calculate received - sent for each address

            # Get all addresses that have interacted with this token
            addresses_result = await session.execute(
                select(
                    distinct(Transfer.from_address).label('address')
                )
                .where(Transfer.denom == denom)
                .union(
                    select(
                        distinct(Transfer.to_address).label('address')
                    )
                    .where(Transfer.denom == denom)
                )
            )

            # For each address, calculate balance
            holders = []
            addresses = [row[0] for row in addresses_result.all()]

            print(f"📊 Calculating balances for {len(addresses):,} addresses...")

            for i, addr in enumerate(addresses):
                if (i + 1) % 1000 == 0:
                    print(f"  Progress: {i+1:,}/{len(addresses):,}")

                # Received
                received_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.to_address == addr,
                        Transfer.denom == denom
                    ))
                )
                received = received_result.scalar() or 0

                # Sent
                sent_result = await session.execute(
                    select(func.sum(Transfer.amount))
                    .where(and_(
                        Transfer.from_address == addr,
                        Transfer.denom == denom
                    ))
                )
                sent = sent_result.scalar() or 0

                balance = received - sent

                if balance > 0:
                    # Get label if available
                    label_result = await session.execute(
                        select(AddressMetadata.label_type)
                        .where(AddressMetadata.address == addr)
                    )
                    label_row = label_result.first()
                    label = label_row[0] if label_row else None

                    holders.append({
                        "address": addr,
                        "balance": balance,
                        "label": label
                    })

            # Sort by balance descending
            holders.sort(key=lambda x: x['balance'], reverse=True)

            # Take top N
            top_holders = holders[:limit]

        print(f"\n✓ Top {len(top_holders)} Holders:")
        print("-"*80)

        for i, holder in enumerate(top_holders[:20], 1):  # Show top 20 in console
            if denom == 'ubbn':
                balance_baby = holder['balance'] / 1e9
                print(f"  {i:3}. {holder['address'][:16]}... {balance_baby:>15,.2f} BABY {('(' + holder['label'].upper() + ')') if holder['label'] else ''}")
            else:
                print(f"  {i:3}. {holder['address'][:16]}... {holder['balance']:>15,} {('(' + holder['label'].upper() + ')') if holder['label'] else ''}")

        print("="*80 + "\n")

        logger.log_metric("top_holders_calculated", len(top_holders), "holders", {
            "denom": denom,
            "limit": limit
        })

        return top_holders


print("✓ Portfolio tracker loaded successfully!")
print("="*80)
