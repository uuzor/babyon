"""
SQLAlchemy Database Models for Babylon Analytics
All models with extensive logging and documentation
"""
from sqlalchemy import Column, String, BigInteger, Integer, Float, Text, Boolean, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

print("=" * 80)
print("📊 Loading Babylon Analytics Database Models")
print("=" * 80)

Base = declarative_base()


class Block(Base):
    """
    Block model - stores blockchain block data

    Indexes optimized for:
    - Height lookups (primary key)
    - Timestamp range queries (for analytics)
    - Hash lookups (for verification)
    """
    __tablename__ = 'blocks'

    height = Column(BigInteger, primary_key=True, comment="Block height (block number)")
    hash = Column(String(64), nullable=False, unique=True, index=True, comment="Block hash (hex)")
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True, comment="Block timestamp")
    proposer_address = Column(String(64), index=True, comment="Validator who proposed this block")
    num_transactions = Column(Integer, default=0, comment="Number of transactions in block")
    gas_used = Column(BigInteger, comment="Total gas used in block")
    gas_wanted = Column(BigInteger, comment="Total gas wanted in block")
    chain_id = Column(String(32), comment="Chain ID (bbn-test-5, bbn-1, etc)")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="When record was created")

    __table_args__ = (
        Index('idx_blocks_timestamp_desc', timestamp.desc()),
        Index('idx_blocks_proposer_timestamp', proposer_address, timestamp.desc()),
        {'comment': 'Blockchain blocks with timestamps and proposer info'}
    )

    def __repr__(self):
        return f"<Block(height={self.height}, hash={self.hash[:16]}..., txs={self.num_transactions})>"


class Transaction(Base):
    """
    Transaction model - stores blockchain transaction data

    Optimized for:
    - Transaction hash lookups
    - Sender address queries
    - Time-range analytics
    - Status filtering (success/failed)
    """
    __tablename__ = 'transactions'

    hash = Column(String(64), primary_key=True, comment="Transaction hash (hex)")
    block_height = Column(BigInteger, ForeignKey('blocks.height'), nullable=False, index=True, comment="Block height")
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True, comment="Transaction timestamp")
    tx_index = Column(Integer, comment="Transaction index in block")
    sender = Column(String(64), index=True, comment="Transaction sender address")
    fee_amount = Column(BigInteger, comment="Transaction fee amount")
    fee_denom = Column(String(32), comment="Fee denomination (ubbn, etc)")
    gas_used = Column(BigInteger, comment="Gas used by transaction")
    gas_wanted = Column(BigInteger, comment="Gas wanted by transaction")
    status = Column(String(16), index=True, comment="Transaction status: success or failed")
    code = Column(Integer, default=0, comment="Result code (0 = success)")
    memo = Column(Text, comment="Transaction memo")
    messages = Column(JSONB, comment="Transaction messages (JSON)")
    events = Column(JSONB, comment="Transaction events (JSON)")
    raw_log = Column(Text, comment="Raw transaction log")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="When record was created")

    __table_args__ = (
        Index('idx_tx_timestamp_desc', timestamp.desc()),
        Index('idx_tx_sender_timestamp', sender, timestamp.desc()),
        Index('idx_tx_block_index', block_height, tx_index),
        Index('idx_tx_status_timestamp', status, timestamp.desc()),
        CheckConstraint("status IN ('success', 'failed')", name='check_tx_status'),
        {'comment': 'Blockchain transactions with full event data'}
    )

    def __repr__(self):
        return f"<Transaction(hash={self.hash[:16]}..., sender={self.sender[:16] if self.sender else 'N/A'}..., status={self.status})>"


class Transfer(Base):
    """
    Transfer model - stores token transfer events extracted from transactions

    Optimized for:
    - Address balance calculations
    - Transfer history queries
    - Amount-based analytics
    """
    __tablename__ = 'transfers'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    tx_hash = Column(String(64), ForeignKey('transactions.hash'), nullable=False, index=True, comment="Transaction hash")
    block_height = Column(BigInteger, ForeignKey('blocks.height'), nullable=False, comment="Block height")
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True, comment="Transfer timestamp")
    from_address = Column(String(64), nullable=False, index=True, comment="Sender address")
    to_address = Column(String(64), nullable=False, index=True, comment="Recipient address")
    amount = Column(BigInteger, nullable=False, comment="Transfer amount (in base units)")
    denom = Column(String(32), nullable=False, index=True, comment="Token denomination")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="When record was created")

    __table_args__ = (
        Index('idx_transfer_from_timestamp', from_address, timestamp.desc()),
        Index('idx_transfer_to_timestamp', to_address, timestamp.desc()),
        Index('idx_transfer_timestamp_desc', timestamp.desc()),
        Index('idx_transfer_denom_amount', denom, amount.desc()),
        {'comment': 'Token transfers extracted from transaction events'}
    )

    def __repr__(self):
        return f"<Transfer(from={self.from_address[:16]}..., to={self.to_address[:16]}..., amount={self.amount} {self.denom})>"


class AddressMetadata(Base):
    """
    Address metadata - enriched address information

    Stores:
    - Activity statistics (tx counts, volumes)
    - Balance information
    - Address labels and classifications
    - Smart money scores
    """
    __tablename__ = 'address_metadata'

    address = Column(String(64), primary_key=True, comment="Babylon address")
    first_seen = Column(TIMESTAMP(timezone=True), comment="First activity timestamp")
    last_seen = Column(TIMESTAMP(timezone=True), comment="Last activity timestamp")
    total_transactions_sent = Column(Integer, default=0, comment="Total transactions sent")
    total_transactions_received = Column(Integer, default=0, comment="Total transactions received")
    total_sent = Column(BigInteger, default=0, comment="Total amount sent (ubbn)")
    total_received = Column(BigInteger, default=0, comment="Total amount received (ubbn)")
    current_balance = Column(BigInteger, default=0, comment="Current balance (ubbn)")
    label_type = Column(String(32), index=True, comment="Address label: exchange, validator, whale, bot, contract, etc")
    label_confidence = Column(Float, comment="Label confidence (0.0 to 1.0)")
    tags = Column(JSONB, comment="Additional metadata tags (JSON)")
    is_contract = Column(Boolean, default=False, index=True, comment="Is this a smart contract address")
    is_validator = Column(Boolean, default=False, index=True, comment="Is this a validator address")
    smart_money_score = Column(Integer, comment="Smart money score (0-100)")
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    __table_args__ = (
        Index('idx_address_label', label_type),
        Index('idx_address_smart_money', smart_money_score.desc().nulls_last()),
        Index('idx_address_balance', current_balance.desc()),
        Index('idx_address_last_seen', last_seen.desc()),
        CheckConstraint('label_confidence >= 0.0 AND label_confidence <= 1.0', name='check_label_confidence'),
        CheckConstraint('smart_money_score >= 0 AND smart_money_score <= 100', name='check_smart_money_score'),
        {'comment': 'Enriched address metadata with labels and statistics'}
    )

    def __repr__(self):
        return f"<AddressMetadata(address={self.address[:16]}..., label={self.label_type}, smart_score={self.smart_money_score})>"


class SmartMoneyIndicator(Base):
    """
    Smart Money Indicators - detailed smart money analysis

    Stores:
    - Composite smart money score
    - Individual component scores
    - Notable trades and patterns
    - Performance metrics
    """
    __tablename__ = 'smart_money_indicators'

    address = Column(String(64), ForeignKey('address_metadata.address'), primary_key=True, comment="Address")
    score = Column(Integer, nullable=False, comment="Overall smart money score (0-100)")
    profitability_score = Column(Float, comment="Profitability component (0.0-1.0)")
    early_adoption_score = Column(Float, comment="Early adoption component (0.0-1.0)")
    volume_score = Column(Float, comment="Volume component (0.0-1.0)")
    win_rate = Column(Float, comment="Win rate percentage")
    influence_score = Column(Float, comment="Influence component (0.0-1.0)")
    total_trades = Column(Integer, default=0, comment="Total number of trades")
    profitable_trades = Column(Integer, default=0, comment="Number of profitable trades")
    total_volume = Column(BigInteger, default=0, comment="Total trading volume (ubbn)")
    notable_trades = Column(JSONB, comment="Array of notable trades (JSON)")
    metrics = Column(JSONB, comment="Additional metrics (JSON)")
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    __table_args__ = (
        Index('idx_smart_money_score_desc', score.desc()),
        Index('idx_smart_money_win_rate', win_rate.desc().nulls_last()),
        Index('idx_smart_money_volume', total_volume.desc()),
        CheckConstraint('score >= 0 AND score <= 100', name='check_score_range'),
        CheckConstraint('profitability_score >= 0.0 AND profitability_score <= 1.0', name='check_profitability'),
        CheckConstraint('early_adoption_score >= 0.0 AND early_adoption_score <= 1.0', name='check_early_adoption'),
        CheckConstraint('volume_score >= 0.0 AND volume_score <= 1.0', name='check_volume'),
        CheckConstraint('influence_score >= 0.0 AND influence_score <= 1.0', name='check_influence'),
        {'comment': 'Smart money detection indicators and scores'}
    )

    def __repr__(self):
        return f"<SmartMoneyIndicator(address={self.address[:16]}..., score={self.score}, win_rate={self.win_rate})>"


# Print model summary
print(f"✓ Loaded {len(Base.metadata.tables)} database models:")
for table_name in Base.metadata.tables.keys():
    table = Base.metadata.tables[table_name]
    print(f"  - {table_name:25} ({len(table.columns)} columns, {len(table.indexes)} indexes)")

print("=" * 80)
print("✓ Database models loaded successfully!")
print("=" * 80)


# Utility functions for database operations
def get_model_summary():
    """Get summary of all database models"""
    summary = {}
    for table_name, table in Base.metadata.tables.items():
        summary[table_name] = {
            'columns': len(table.columns),
            'indexes': len(table.indexes),
            'foreign_keys': len(table.foreign_keys),
            'comment': table.comment
        }
    return summary


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Database Models Summary")
    print("=" * 80 + "\n")

    summary = get_model_summary()
    for table_name, info in summary.items():
        print(f"📊 {table_name}")
        print(f"   Columns: {info['columns']}")
        print(f"   Indexes: {info['indexes']}")
        print(f"   Foreign Keys: {info['foreign_keys']}")
        print(f"   Description: {info['comment']}")
        print()

    print("=" * 80)
    print("✓ Model summary complete!")
    print("=" * 80)
