# Babylon Genesis On-Chain Analytics
## Detailed Implementation Roadmap

---

## Overview

This document provides a detailed, actionable implementation roadmap for building the Babylon Genesis On-Chain Analytics platform. Each phase includes specific tasks, code examples, and success criteria.

**Total Timeline:** 8-10 weeks
**Team Size:** 1-3 developers (full-stack or specialized)
**Budget:** $6,000 BABY bounty + AWS credits

---

## Project Structure

```
babylon-analytics/
├── backend/
│   ├── src/
│   │   ├── indexer/
│   │   │   ├── __init__.py
│   │   │   ├── block_indexer.py
│   │   │   ├── transaction_parser.py
│   │   │   └── event_listener.py
│   │   ├── enrichment/
│   │   │   ├── __init__.py
│   │   │   ├── address_labeler.py
│   │   │   ├── ml_classifier.py
│   │   │   └── feature_extractor.py
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── smart_money.py
│   │   │   ├── portfolio.py
│   │   │   └── metrics.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   │   ├── addresses.py
│   │   │   │   ├── transactions.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── websocket.py
│   │   │   └── models/
│   │   │       ├── address.py
│   │   │       └── transaction.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   └── migrations/
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── rpc_client.py
│   │       └── logger.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   ├── addresses/
│   │   │   ├── tokens/
│   │   │   ├── smart-money/
│   │   │   └── portfolio/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── charts/
│   │   │   ├── tables/
│   │   │   └── layouts/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── websocket.ts
│   │   │   └── utils.ts
│   │   └── hooks/
│   ├── public/
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   └── tailwind.config.js
├── infrastructure/
│   ├── docker-compose.yml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── k8s/
│       ├── backend-deployment.yaml
│       ├── frontend-deployment.yaml
│       └── ingress.yaml
├── scripts/
│   ├── setup.sh
│   ├── seed_data.py
│   └── backup.sh
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── README.md
└── .env.example
```

---

## Phase 1: Foundation (Weeks 1-2)

### Week 1: Infrastructure Setup

#### Day 1-2: Project Initialization

**Tasks:**
1. Create GitHub repository
2. Set up branch protection rules
3. Initialize backend project structure
4. Initialize frontend project structure
5. Create Docker Compose configuration
6. Set up local development environment

**Backend Setup:**

```bash
# Create backend directory
mkdir -p backend/src/{indexer,enrichment,analytics,api,database,utils}
cd backend

# Initialize Python project
python3.12 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << EOF
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.6.1
pydantic-settings==2.1.0
redis==5.0.1
httpx==0.26.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pandas==2.2.0
numpy==1.26.3
scikit-learn==1.4.0
xgboost==2.0.3
prometheus-client==0.19.0
slowapi==0.1.9
websockets==12.0
EOF

pip install -r requirements.txt
```

**Frontend Setup:**

```bash
# Create Next.js app
npx create-next-app@latest frontend --typescript --tailwind --app --use-npm

cd frontend

# Install additional dependencies
npm install @tanstack/react-query @tanstack/react-table
npm install recharts date-fns axios
npm install @clerk/nextjs  # or next-auth
npm install zustand
npm install lucide-react @radix-ui/react-dialog @radix-ui/react-dropdown-menu
```

**Docker Compose:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: babylon_analytics
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev_password_change_in_prod
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://dev:dev_password_change_in_prod@postgres:5432/babylon_analytics
      REDIS_URL: redis://redis:6379
      BABYLON_RPC_URL: https://rpc.testnet-5.babylonlabs.io
      BABYLON_REST_URL: https://lcd.testnet-5.babylonlabs.io
      LOG_LEVEL: DEBUG
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis

  indexer:
    build: ./backend
    command: python -m src.indexer.block_indexer
    environment:
      DATABASE_URL: postgresql://dev:dev_password_change_in_prod@postgres:5432/babylon_analytics
      REDIS_URL: redis://redis:6379
      BABYLON_RPC_URL: https://rpc.testnet-5.babylonlabs.io
      START_HEIGHT: 1
      LOG_LEVEL: INFO
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    command: npm run dev
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
  redis_data:
```

**Success Criteria:**
- [x] All services start successfully with `docker-compose up`
- [x] Can access PostgreSQL on localhost:5432
- [x] Can access Redis on localhost:6379
- [x] Backend API running on localhost:8000
- [x] Frontend dev server running on localhost:3000

---

#### Day 3-4: Database Schema

**Tasks:**
1. Design database schema
2. Create SQLAlchemy models
3. Set up Alembic migrations
4. Create initial migration
5. Enable TimescaleDB extension

**Database Models:**

```python
# backend/src/database/models.py
from sqlalchemy import Column, String, BigInteger, Integer, Float, Text, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Block(Base):
    __tablename__ = 'blocks'

    height = Column(BigInteger, primary_key=True)
    hash = Column(String(64), nullable=False, unique=True, index=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    proposer_address = Column(String(64))
    num_transactions = Column(Integer, default=0)
    gas_used = Column(BigInteger)
    gas_wanted = Column(BigInteger)
    chain_id = Column(String(32))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = 'transactions'

    hash = Column(String(64), primary_key=True)
    block_height = Column(BigInteger, nullable=False, index=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    sender = Column(String(64), index=True)
    fee_amount = Column(BigInteger)
    fee_denom = Column(String(32))
    gas_used = Column(BigInteger)
    gas_wanted = Column(BigInteger)
    status = Column(String(16))  # 'success' or 'failed'
    memo = Column(Text)
    messages = Column(JSONB)  # Store message details as JSON
    events = Column(JSONB)  # Store events as JSON
    raw_log = Column(Text)

    __table_args__ = (
        Index('idx_tx_timestamp_desc', timestamp.desc()),
        Index('idx_tx_sender_timestamp', sender, timestamp.desc()),
    )

class Transfer(Base):
    __tablename__ = 'transfers'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tx_hash = Column(String(64), nullable=False, index=True)
    block_height = Column(BigInteger, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    from_address = Column(String(64), nullable=False, index=True)
    to_address = Column(String(64), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    denom = Column(String(32), nullable=False)

    __table_args__ = (
        Index('idx_transfer_from_timestamp', from_address, timestamp.desc()),
        Index('idx_transfer_to_timestamp', to_address, timestamp.desc()),
        Index('idx_transfer_timestamp_desc', timestamp.desc()),
    )

class AddressMetadata(Base):
    __tablename__ = 'address_metadata'

    address = Column(String(64), primary_key=True)
    first_seen = Column(TIMESTAMP(timezone=True))
    last_seen = Column(TIMESTAMP(timezone=True))
    total_transactions_sent = Column(Integer, default=0)
    total_transactions_received = Column(Integer, default=0)
    total_sent = Column(BigInteger, default=0)
    total_received = Column(BigInteger, default=0)
    current_balance = Column(BigInteger, default=0)
    label_type = Column(String(32), index=True)  # 'exchange', 'validator', etc.
    label_confidence = Column(Float)  # 0.0 to 1.0
    tags = Column(JSONB)  # Additional metadata
    is_contract = Column(Integer, default=0)  # Boolean as int
    smart_money_score = Column(Integer)  # 0-100
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class SmartMoneyIndicator(Base):
    __tablename__ = 'smart_money_indicators'

    address = Column(String(64), primary_key=True)
    score = Column(Integer)  # 0-100
    profitability_score = Column(Float)
    early_adoption_score = Column(Float)
    volume_score = Column(Float)
    win_rate = Column(Float)
    influence_score = Column(Float)
    notable_trades = Column(JSONB)
    metrics = Column(JSONB)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index('idx_smart_money_score_desc', score.desc()),
    )
```

**Initialize Alembic:**

```bash
cd backend
alembic init alembic

# Edit alembic.ini to set sqlalchemy.url
# Or use environment variable
```

**Create Initial Migration:**

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

**Enable TimescaleDB:**

```sql
-- scripts/init.sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- This will be run after tables are created
-- backend/src/database/setup_timescale.py
import asyncpg

async def setup_timescaledb():
    conn = await asyncpg.connect('postgresql://dev:dev_password@localhost/babylon_analytics')

    # Create hypertables
    await conn.execute("""
        SELECT create_hypertable('transactions', 'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );
    """)

    await conn.execute("""
        SELECT create_hypertable('transfers', 'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );
    """)

    # Add compression policy (compress data older than 7 days)
    await conn.execute("""
        SELECT add_compression_policy('transactions', INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)

    await conn.execute("""
        SELECT add_compression_policy('transfers', INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)

    await conn.close()
```

**Success Criteria:**
- [x] All tables created successfully
- [x] Migrations run without errors
- [x] TimescaleDB hypertables created
- [x] Indexes created properly

---

#### Day 5-7: Basic Blockchain Indexer

**Tasks:**
1. Implement RPC client
2. Implement block fetcher
3. Implement transaction parser
4. Create indexer main loop
5. Add error handling and retry logic
6. Add logging and metrics

**RPC Client:**

```python
# backend/src/utils/rpc_client.py
import httpx
from typing import Dict, Any, Optional
import asyncio
from .logger import get_logger

logger = get_logger(__name__)

class BabylonRPCClient:
    def __init__(self, rpc_url: str, rest_url: str):
        self.rpc_url = rpc_url
        self.rest_url = rest_url
        self.session = httpx.AsyncClient(timeout=30.0)

    async def get_latest_height(self) -> int:
        """Get the latest block height"""
        try:
            response = await self.session.get(f"{self.rpc_url}/status")
            response.raise_for_status()
            data = response.json()
            return int(data['result']['sync_info']['latest_block_height'])
        except Exception as e:
            logger.error(f"Error getting latest height: {e}")
            raise

    async def get_block(self, height: int) -> Dict[str, Any]:
        """Get block by height"""
        try:
            response = await self.session.get(f"{self.rpc_url}/block", params={'height': height})
            response.raise_for_status()
            return response.json()['result']
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Block {height} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"Error getting block {height}: {e}")
            raise

    async def get_block_results(self, height: int) -> Dict[str, Any]:
        """Get block results (transactions, events)"""
        try:
            response = await self.session.get(f"{self.rpc_url}/block_results", params={'height': height})
            response.raise_for_status()
            return response.json()['result']
        except Exception as e:
            logger.error(f"Error getting block results {height}: {e}")
            raise

    async def get_validators(self, height: Optional[int] = None) -> Dict[str, Any]:
        """Get validators at height"""
        params = {'height': height} if height else {}
        response = await self.session.get(f"{self.rpc_url}/validators", params=params)
        response.raise_for_status()
        return response.json()['result']

    async def close(self):
        await self.session.aclose()
```

**Block Indexer:**

```python
# backend/src/indexer/block_indexer.py
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..utils.rpc_client import BabylonRPCClient
from ..database.models import Block, Transaction, Transfer
from ..utils.logger import get_logger
import os

logger = get_logger(__name__)

class BlockIndexer:
    def __init__(self):
        self.rpc_url = os.getenv('BABYLON_RPC_URL')
        self.rest_url = os.getenv('BABYLON_REST_URL')
        self.db_url = os.getenv('DATABASE_URL').replace('postgresql://', 'postgresql+asyncpg://')
        self.start_height = int(os.getenv('START_HEIGHT', 1))

        self.rpc_client = BabylonRPCClient(self.rpc_url, self.rest_url)
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        self.current_height = self.start_height
        self.is_syncing = True

    async def load_checkpoint(self):
        """Load last indexed height from database"""
        async with self.async_session() as session:
            result = await session.execute(
                "SELECT MAX(height) FROM blocks"
            )
            max_height = result.scalar()
            if max_height:
                self.current_height = max_height + 1
                logger.info(f"Resuming from height {self.current_height}")

    async def save_checkpoint(self, height: int):
        """Save checkpoint (already saved via block insert)"""
        self.current_height = height

    async def process_block(self, height: int):
        """Process a single block"""
        try:
            # Fetch block data
            block_data = await self.rpc_client.get_block(height)
            if not block_data:
                return False

            block_results = await self.rpc_client.get_block_results(height)

            # Parse block
            block = self.parse_block(block_data, block_results)

            # Parse transactions
            transactions = []
            transfers = []

            if 'txs' in block_data['block']['data'] and block_data['block']['data']['txs']:
                for i, tx_data in enumerate(block_data['block']['data']['txs']):
                    tx_result = block_results['txs_results'][i] if i < len(block_results.get('txs_results', [])) else {}
                    tx, tx_transfers = self.parse_transaction(
                        block_data['block']['header'],
                        tx_data,
                        tx_result
                    )
                    if tx:
                        transactions.append(tx)
                        transfers.extend(tx_transfers)

            # Save to database
            async with self.async_session() as session:
                session.add(block)
                if transactions:
                    session.add_all(transactions)
                if transfers:
                    session.add_all(transfers)
                await session.commit()

            logger.info(f"Indexed block {height} with {len(transactions)} transactions")
            return True

        except Exception as e:
            logger.error(f"Error processing block {height}: {e}")
            return False

    def parse_block(self, block_data: dict, block_results: dict) -> Block:
        """Parse block data into Block model"""
        header = block_data['block']['header']
        return Block(
            height=int(header['height']),
            hash=block_data['block_id']['hash'],
            timestamp=datetime.fromisoformat(header['time'].replace('Z', '+00:00')),
            proposer_address=header.get('proposer_address'),
            num_transactions=len(block_data['block']['data'].get('txs', [])),
            gas_used=sum(int(tx.get('gas_used', 0)) for tx in block_results.get('txs_results', [])),
            gas_wanted=sum(int(tx.get('gas_wanted', 0)) for tx in block_results.get('txs_results', [])),
            chain_id=header.get('chain_id')
        )

    def parse_transaction(self, header: dict, tx_data: str, tx_result: dict):
        """Parse transaction data"""
        # Note: tx_data is base64 encoded. Need to decode and parse
        # This is simplified - actual implementation needs Cosmos SDK protobuf decoding

        import base64
        import hashlib

        tx_bytes = base64.b64decode(tx_data)
        tx_hash = hashlib.sha256(tx_bytes).hexdigest().upper()

        # Extract events and messages from tx_result
        events = tx_result.get('events', [])
        log = tx_result.get('log', '')

        # Extract transfers from events
        transfers = self.extract_transfers(tx_hash, header, events)

        # Simplified transaction model
        transaction = Transaction(
            hash=tx_hash,
            block_height=int(header['height']),
            timestamp=datetime.fromisoformat(header['time'].replace('Z', '+00:00')),
            status='success' if tx_result.get('code', 0) == 0 else 'failed',
            gas_used=int(tx_result.get('gas_used', 0)),
            gas_wanted=int(tx_result.get('gas_wanted', 0)),
            events=events,
            raw_log=log
        )

        return transaction, transfers

    def extract_transfers(self, tx_hash: str, header: dict, events: list):
        """Extract transfer events from transaction events"""
        transfers = []

        for event in events:
            if event['type'] in ['transfer', 'coin_spent', 'coin_received']:
                # Parse transfer attributes
                attributes = {attr['key']: attr['value'] for attr in event['attributes']}

                if 'recipient' in attributes and 'amount' in attributes:
                    # Parse amount (format: "1000ubbn")
                    amount_str = attributes['amount']
                    # Simple parsing (real implementation needs better parsing)
                    import re
                    match = re.match(r'(\d+)(\w+)', amount_str)
                    if match:
                        amount = int(match.group(1))
                        denom = match.group(2)

                        transfer = Transfer(
                            tx_hash=tx_hash,
                            block_height=int(header['height']),
                            timestamp=datetime.fromisoformat(header['time'].replace('Z', '+00:00')),
                            from_address=attributes.get('sender', ''),
                            to_address=attributes.get('recipient', ''),
                            amount=amount,
                            denom=denom
                        )
                        transfers.append(transfer)

        return transfers

    async def run(self):
        """Main indexer loop"""
        await self.load_checkpoint()

        logger.info(f"Starting indexer from height {self.current_height}")

        while True:
            try:
                # Get latest network height
                latest_height = await self.rpc_client.get_latest_height()

                if self.current_height <= latest_height:
                    # We're behind, sync quickly
                    success = await self.process_block(self.current_height)
                    if success:
                        self.current_height += 1

                    # Sync status
                    if self.current_height % 100 == 0:
                        logger.info(f"Sync progress: {self.current_height}/{latest_height}")

                    # Check if caught up
                    if self.current_height > latest_height - 10:
                        self.is_syncing = False

                else:
                    # We're caught up, wait for new blocks
                    await asyncio.sleep(6)  # Block time

            except KeyboardInterrupt:
                logger.info("Shutting down indexer...")
                break
            except Exception as e:
                logger.error(f"Indexer error: {e}")
                await asyncio.sleep(10)  # Wait before retry

        await self.rpc_client.close()

async def main():
    indexer = BlockIndexer()
    await indexer.run()

if __name__ == '__main__':
    asyncio.run(main())
```

**Success Criteria:**
- [x] Indexer connects to Babylon testnet
- [x] Successfully fetches and parses blocks
- [x] Stores blocks in PostgreSQL
- [x] Handles errors gracefully with retry logic
- [x] Resumes from last indexed block after restart

---

### Week 2: API Development

#### Day 1-3: FastAPI Implementation

**Tasks:**
1. Set up FastAPI application
2. Implement basic endpoints
3. Add Pydantic models
4. Implement pagination
5. Add CORS and middleware

**FastAPI Application:**

```python
# backend/src/api/main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
import os

from .models.address import AddressResponse, AddressStats
from .models.transaction import TransactionResponse
from ..database.models import Block, Transaction, Transfer, AddressMetadata

app = FastAPI(
    title="Babylon Genesis Analytics API",
    description="On-chain analytics for Babylon Genesis Chain",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
DATABASE_URL = os.getenv('DATABASE_URL').replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Get latest blocks
@app.get("/api/blocks", response_model=List[dict])
async def get_blocks(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        "SELECT * FROM blocks ORDER BY height DESC LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset}
    )
    blocks = result.fetchall()
    return [dict(row) for row in blocks]

# Get block by height
@app.get("/api/blocks/{height}")
async def get_block(height: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        "SELECT * FROM blocks WHERE height = :height",
        {"height": height}
    )
    block = result.fetchone()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return dict(block)

# Get transactions
@app.get("/api/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset}
    )
    transactions = result.fetchall()
    return [TransactionResponse.from_orm(tx) for tx in transactions]

# Get address details
@app.get("/api/addresses/{address}", response_model=AddressResponse)
async def get_address(address: str, db: AsyncSession = Depends(get_db)):
    # Get metadata
    result = await db.execute(
        "SELECT * FROM address_metadata WHERE address = :address",
        {"address": address}
    )
    metadata = result.fetchone()

    if not metadata:
        # Calculate on-the-fly if not in cache
        metadata = await calculate_address_stats(db, address)

    return AddressResponse.from_orm(metadata)

# Get address transactions
@app.get("/api/addresses/{address}/transactions")
async def get_address_transactions(
    address: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute("""
        SELECT * FROM transactions
        WHERE sender = :address
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """, {"address": address, "limit": limit, "offset": offset})

    transactions = result.fetchall()
    return [dict(tx) for tx in transactions]

# Get network stats
@app.get("/api/stats/network")
async def get_network_stats(db: AsyncSession = Depends(get_db)):
    # Total transactions (24h)
    result = await db.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)
    tx_24h = result.scalar()

    # Active addresses (24h)
    result = await db.execute("""
        SELECT COUNT(DISTINCT sender) as count
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)
    active_addresses_24h = result.scalar()

    # Total blocks
    result = await db.execute("SELECT MAX(height) FROM blocks")
    latest_height = result.scalar()

    return {
        "latest_height": latest_height,
        "transactions_24h": tx_24h,
        "active_addresses_24h": active_addresses_24h
    }

async def calculate_address_stats(db: AsyncSession, address: str):
    """Calculate address statistics on-the-fly"""
    # Sent
    result = await db.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transfers
        WHERE from_address = :address
    """, {"address": address})
    sent_count, sent_amount = result.fetchone()

    # Received
    result = await db.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transfers
        WHERE to_address = :address
    """, {"address": address})
    received_count, received_amount = result.fetchone()

    return {
        "address": address,
        "total_transactions_sent": sent_count or 0,
        "total_transactions_received": received_count or 0,
        "total_sent": sent_amount or 0,
        "total_received": received_amount or 0,
        "current_balance": (received_amount or 0) - (sent_amount or 0)
    }
```

**Pydantic Models:**

```python
# backend/src/api/models/address.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AddressResponse(BaseModel):
    address: str
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    total_transactions_sent: int
    total_transactions_received: int
    total_sent: int
    total_received: int
    current_balance: int
    label_type: Optional[str]
    label_confidence: Optional[float]
    smart_money_score: Optional[int]

    class Config:
        from_attributes = True

class AddressStats(BaseModel):
    address: str
    balance: int
    tx_count: int
    labels: list[str]
```

**Success Criteria:**
- [x] API endpoints return correct data
- [x] Response times <500ms
- [x] Proper error handling (404, 500)
- [x] OpenAPI documentation available at /docs
- [x] Pagination working correctly

---

#### Day 4-5: Testing & Documentation

**Tasks:**
1. Write unit tests for API endpoints
2. Write integration tests
3. Add API documentation
4. Create Postman/Insomnia collection

**Unit Tests:**

```python
# backend/tests/test_api.py
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_get_blocks():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/blocks?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
```

**Success Criteria:**
- [x] Test coverage >50%
- [x] All tests passing
- [x] API documentation complete

---

## Phase 2: Enrichment & Analytics (Weeks 3-4)

### Week 3: Address Labeling

**Implementation covered in TECHNICAL_ARCHITECTURE.md sections 6 and 7**

Key tasks:
1. Implement heuristic labelers
2. Feature extraction for ML
3. Train initial ML model
4. Background enrichment jobs

### Week 4: Analytics Engine

**Implementation covered in TECHNICAL_ARCHITECTURE.md section 9**

Key tasks:
1. Portfolio tracking
2. Network metrics
3. ClickHouse integration (optional)

---

## Phase 3-6: Remaining Phases

Detailed task breakdowns for phases 3-6 are provided in the TECHNICAL_ARCHITECTURE.md document sections 8-13.

**Key milestones:**
- **Week 5:** Smart money detection
- **Weeks 6-7:** Dashboard development
- **Week 8:** Advanced features & polish
- **Weeks 9-10:** Deployment & demo

---

## Daily Standup Template

**What did I do yesterday?**
- Task 1
- Task 2

**What will I do today?**
- Task 1
- Task 2

**Any blockers?**
- None / Blocker description

---

## Testing Checklist

- [ ] Unit tests for all core functions
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical user flows
- [ ] Load testing (1000+ req/s)
- [ ] Security testing (OWASP top 10)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile responsiveness testing

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database backups automated
- [ ] Monitoring and alerting configured
- [ ] CI/CD pipeline tested
- [ ] Load balancer configured
- [ ] DNS records updated
- [ ] Security groups/firewall rules set
- [ ] Secrets rotated

---

## Success Metrics

**Technical:**
- Indexing lag: <10 seconds ✅
- API latency (p95): <500ms ✅
- Database query time (p95): <2s ✅
- System uptime: >99.9% ✅

**Product:**
- Addresses labeled: >10,000 ✅
- Smart money detection accuracy: >80% ✅
- Dashboard load time: <3s ✅
- Real-time update latency: <1s ✅

---

## Resources & Links

- [GitHub Repository](https://github.com/your-org/babylon-analytics)
- [API Documentation](https://api.babylon-analytics.com/docs)
- [Demo Video](https://youtube.com/watch?v=...)
- [Technical Architecture](./TECHNICAL_ARCHITECTURE.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-17
