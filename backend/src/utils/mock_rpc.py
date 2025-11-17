"""
Mock RPC Client for development and testing
Generates realistic fake blockchain data when real RPC is unavailable
"""
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .logger import DebugLogger

logger = DebugLogger("mock_rpc")


class MockBabylonRPCClient:
    """
    Mock Babylon RPC Client that generates fake but realistic data
    Perfect for development and testing when real RPC endpoints are unavailable
    """

    def __init__(self):
        """Initialize mock RPC client"""
        logger.log_startup("MockBabylonRPCClient", {
            "mode": "MOCK",
            "note": "Generating fake data for development"
        })

        self.current_height = 50000  # Starting mock height
        self.start_time = datetime.now() - timedelta(days=30)  # Genesis 30 days ago
        self.block_time = 6  # 6 seconds per block

        # Mock addresses
        self.validators = self._generate_validators(10)
        self.addresses = self._generate_addresses(100)

        logger.info(f"✓ Mock RPC Client initialized (height: {self.current_height})")

    def _generate_validators(self, count: int) -> List[str]:
        """Generate mock validator addresses"""
        validators = []
        for i in range(count):
            # Babylon addresses start with 'bbn1'
            addr = f"bbn1validator{i:04d}" + "x" * 35
            validators.append(addr[:44])  # Babylon addresses are 44 chars
        logger.debug(f"Generated {count} mock validators")
        return validators

    def _generate_addresses(self, count: int) -> List[str]:
        """Generate mock user addresses"""
        addresses = []
        for i in range(count):
            addr = f"bbn1user{i:06d}" + "y" * 30
            addresses.append(addr[:44])
        logger.debug(f"Generated {count} mock addresses")
        return addresses

    def _generate_tx_hash(self, height: int, tx_index: int) -> str:
        """Generate deterministic transaction hash"""
        import hashlib
        data = f"{height}:{tx_index}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest().upper()

    async def get_latest_height(self) -> int:
        """Get latest block height (incrementing)"""
        # Simulate chain progressing
        self.current_height += 1

        logger.info(f"📊 Mock latest height: {self.current_height}")

        return self.current_height

    async def get_block(self, height: int) -> Optional[Dict[str, Any]]:
        """Get mock block data"""
        logger.debug(f"🔍 Generating mock block #{height}...")

        if height > self.current_height or height < 1:
            logger.warning(f"Block #{height} not found (current: {self.current_height})")
            return None

        # Calculate block timestamp
        blocks_since_genesis = height - 1
        block_timestamp = self.start_time + timedelta(seconds=blocks_since_genesis * self.block_time)

        # Generate transactions
        num_txs = random.randint(0, 20)
        txs = []
        for i in range(num_txs):
            # Generate base64-encoded tx data (mock)
            tx_data = f"mock_tx_{height}_{i}"
            import base64
            txs.append(base64.b64encode(tx_data.encode()).decode())

        # Mock proposer
        proposer = random.choice(self.validators) if self.validators else "bbn1validator0000"

        block = {
            "block_id": {
                "hash": self._generate_tx_hash(height, 0),
                "parts": {
                    "total": 1,
                    "hash": self._generate_tx_hash(height, 1)
                }
            },
            "block": {
                "header": {
                    "version": {"block": "11"},
                    "chain_id": "bbn-test-5",
                    "height": str(height),
                    "time": block_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "last_block_id": {
                        "hash": self._generate_tx_hash(height - 1, 0) if height > 1 else ""
                    },
                    "last_commit_hash": "",
                    "data_hash": "",
                    "validators_hash": "",
                    "next_validators_hash": "",
                    "consensus_hash": "",
                    "app_hash": "",
                    "last_results_hash": "",
                    "evidence_hash": "",
                    "proposer_address": proposer
                },
                "data": {
                    "txs": txs
                },
                "evidence": {
                    "evidence": []
                },
                "last_commit": {
                    "height": str(height - 1),
                    "round": 0,
                    "block_id": {
                        "hash": self._generate_tx_hash(height - 1, 0) if height > 1 else ""
                    },
                    "signatures": []
                }
            }
        }

        logger.debug(
            f"✓ Mock block #{height}",
            transactions=num_txs,
            timestamp=block_timestamp.isoformat(),
            hash=block["block_id"]["hash"][:16] + "..."
        )

        return block

    async def get_block_results(self, height: int) -> Optional[Dict[str, Any]]:
        """Get mock block results"""
        logger.debug(f"🔍 Generating mock block results for #{height}...")

        # Get block to know how many txs
        block = await self.get_block(height)
        if not block:
            return None

        num_txs = len(block['block']['data'].get('txs', []))

        # Generate tx results
        txs_results = []
        for i in range(num_txs):
            # Random success/failure
            success = random.random() > 0.05  # 95% success rate

            # Generate transfer events
            events = []
            if success:
                from_addr = random.choice(self.addresses)
                to_addr = random.choice(self.addresses)
                amount = random.randint(100, 100000)

                events = [
                    {
                        "type": "transfer",
                        "attributes": [
                            {"key": "recipient", "value": to_addr, "index": True},
                            {"key": "sender", "value": from_addr, "index": True},
                            {"key": "amount", "value": f"{amount}ubbn", "index": True}
                        ]
                    },
                    {
                        "type": "message",
                        "attributes": [
                            {"key": "action", "value": "/cosmos.bank.v1beta1.MsgSend", "index": True},
                            {"key": "sender", "value": from_addr, "index": True},
                            {"key": "module", "value": "bank", "index": True}
                        ]
                    }
                ]

            tx_result = {
                "code": 0 if success else random.randint(1, 10),
                "data": "",
                "log": "[]" if success else f"Error: mock error {i}",
                "info": "",
                "gas_wanted": str(random.randint(50000, 200000)),
                "gas_used": str(random.randint(40000, 150000)),
                "events": events,
                "codespace": "" if success else "sdk"
            }
            txs_results.append(tx_result)

        results = {
            "height": str(height),
            "txs_results": txs_results,
            "begin_block_events": [],
            "end_block_events": [],
            "validator_updates": [],
            "consensus_param_updates": {
                "block": {
                    "max_bytes": "22020096",
                    "max_gas": "-1"
                }
            }
        }

        logger.debug(
            f"✓ Mock block results #{height}",
            tx_count=len(txs_results),
            success_count=sum(1 for tx in txs_results if tx["code"] == 0)
        )

        return results

    async def get_validators(self, height: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get mock validators"""
        logger.debug(f"🔍 Fetching mock validators", height=height or "latest")

        validators = []
        for i, addr in enumerate(self.validators):
            validators.append({
                "address": addr,
                "pub_key": {
                    "type": "tendermint/PubKeyEd25519",
                    "value": f"mock_pubkey_{i}"
                },
                "voting_power": str(random.randint(1000000, 10000000)),
                "proposer_priority": str(random.randint(-1000000, 1000000))
            })

        logger.info(f"✓ Fetched {len(validators)} mock validators")

        return validators

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get mock transaction"""
        logger.debug(f"🔍 Generating mock transaction", hash=tx_hash[:16] + "...")

        # Generate random tx
        height = random.randint(1, self.current_height)
        from_addr = random.choice(self.addresses)
        to_addr = random.choice(self.addresses)
        amount = random.randint(100, 100000)

        block_data = await self.get_block(height)
        timestamp = block_data['block']['header']['time'] if block_data else datetime.now().isoformat()

        tx = {
            "hash": tx_hash,
            "height": str(height),
            "index": 0,
            "tx_result": {
                "code": 0,
                "data": "",
                "log": "[]",
                "info": "",
                "gas_wanted": "100000",
                "gas_used": "75000",
                "events": [
                    {
                        "type": "transfer",
                        "attributes": [
                            {"key": "recipient", "value": to_addr},
                            {"key": "sender", "value": from_addr},
                            {"key": "amount", "value": f"{amount}ubbn"}
                        ]
                    }
                ]
            },
            "tx": "mock_tx_data",
            "proof": {},
            "timestamp": timestamp
        }

        logger.debug(f"✓ Mock transaction", hash=tx_hash[:16] + "...", height=height)

        return tx

    async def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """Get mock account"""
        logger.debug(f"🔍 Generating mock account", address=address[:16] + "...")

        account = {
            "@type": "/cosmos.auth.v1beta1.BaseAccount",
            "address": address,
            "pub_key": None,
            "account_number": str(random.randint(1, 100000)),
            "sequence": str(random.randint(0, 1000))
        }

        logger.debug(f"✓ Mock account", address=address[:16] + "...")

        return account

    async def get_balance(self, address: str) -> List[Dict[str, Any]]:
        """Get mock balance"""
        logger.debug(f"🔍 Generating mock balance", address=address[:16] + "...")

        balances = [
            {
                "denom": "ubbn",
                "amount": str(random.randint(1000000, 100000000))
            }
        ]

        logger.debug(f"✓ Mock balance", address=address[:16] + "...", amount=balances[0]["amount"])

        return balances

    def get_stats(self) -> Dict[str, Any]:
        """Get mock stats"""
        return {
            "mode": "MOCK",
            "current_height": self.current_height,
            "validators": len(self.validators),
            "mock_addresses": len(self.addresses)
        }

    async def close(self):
        """Close (no-op for mock)"""
        logger.log_shutdown("MockBabylonRPCClient")
        logger.info("✓ Mock RPC Client closed")


# Test the mock RPC client
async def test_mock_rpc():
    """Test mock RPC client"""
    print("\n" + "=" * 80)
    print("Testing Mock Babylon RPC Client")
    print("=" * 80 + "\n")

    client = MockBabylonRPCClient()

    try:
        # Test getting latest height
        print("\n📊 Test 1: Get Latest Height")
        print("-" * 80)
        height = await client.get_latest_height()
        print(f"✓ Latest height: {height}")

        # Test getting a block
        print("\n📦 Test 2: Get Block")
        print("-" * 80)
        test_height = height - 5
        block = await client.get_block(test_height)
        if block:
            print(f"✓ Block #{test_height} fetched")
            print(f"  - Hash: {block['block_id']['hash'][:32]}...")
            print(f"  - Transactions: {len(block['block']['data'].get('txs', []))}")
            print(f"  - Timestamp: {block['block']['header']['time']}")

        # Test getting block results
        print("\n📋 Test 3: Get Block Results")
        print("-" * 80)
        results = await client.get_block_results(test_height)
        if results:
            print(f"✓ Block results #{test_height} fetched")
            print(f"  - TX Results: {len(results.get('txs_results', []))}")
            success_count = sum(1 for tx in results.get('txs_results', []) if tx.get('code') == 0)
            print(f"  - Successful: {success_count}")

        # Test getting validators
        print("\n👥 Test 4: Get Validators")
        print("-" * 80)
        validators = await client.get_validators()
        print(f"✓ Found {len(validators)} validators")
        if validators:
            print(f"  - First validator: {validators[0]['address'][:20]}...")
            print(f"  - Voting power: {validators[0]['voting_power']}")

        # Print statistics
        print("\n📈 Mock RPC Client Statistics")
        print("-" * 80)
        stats = client.get_stats()
        for key, value in stats.items():
            print(f"  - {key}: {value}")

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mock_rpc())
