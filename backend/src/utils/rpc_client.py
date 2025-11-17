"""
Babylon RPC Client with extensive logging and debugging
Handles all communication with Babylon Genesis Chain
"""
import httpx
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from .logger import DebugLogger
from .config import get_settings

logger = DebugLogger("rpc_client")


class BabylonRPCClient:
    """
    Babylon Genesis Chain RPC Client
    Provides async methods for querying blockchain data with extensive logging
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        rest_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize RPC client

        Args:
            rpc_url: RPC endpoint URL (defaults to config)
            rest_url: REST API endpoint URL (defaults to config)
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self.rpc_url = rpc_url or settings.babylon_rpc_url
        self.rest_url = rest_url or settings.babylon_rest_url
        self.timeout = timeout

        logger.log_startup("BabylonRPCClient", {
            "rpc_url": self.rpc_url,
            "rest_url": self.rest_url,
            "timeout": timeout
        })

        # Create async HTTP client
        self.session = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
        }

        logger.info("✓ RPC Client initialized successfully")

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries and extensive logging

        Args:
            method: HTTP method (GET, POST)
            url: Full URL
            params: Query parameters
            retries: Number of retry attempts

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: On request failure after retries
        """
        logger.log_api_request(method, url, params=params)

        start_time = time.time()
        self.stats["total_requests"] += 1

        for attempt in range(retries):
            try:
                logger.debug(f"🔄 Attempt {attempt + 1}/{retries}", url=url[:80])

                if method == "GET":
                    response = await self.session.get(url, params=params)
                elif method == "POST":
                    response = await self.session.post(url, json=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                duration_ms = (time.time() - start_time) * 1000

                # Check response
                response.raise_for_status()

                # Parse JSON
                data = response.json()
                response_size = len(response.content)

                # Update stats
                self.stats["successful_requests"] += 1
                self.stats["total_duration_ms"] += duration_ms

                # Log success
                logger.log_api_response(
                    response.status_code,
                    url,
                    response_size,
                    duration_ms
                )

                logger.log_performance("api_request", duration_ms, items_processed=1)

                return data

            except httpx.HTTPStatusError as e:
                duration_ms = (time.time() - start_time) * 1000

                if e.response.status_code == 404:
                    logger.warning(f"❌ Resource not found (404)", url=url[:80])
                    return None

                logger.error(
                    f"HTTP Error: {e.response.status_code}",
                    exc=e,
                    url=url[:80],
                    attempt=attempt + 1
                )

                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.stats["failed_requests"] += 1
                    raise

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"Request failed",
                    exc=e,
                    url=url[:80],
                    attempt=attempt + 1,
                    duration_ms=round(duration_ms, 2)
                )

                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.stats["failed_requests"] += 1
                    raise

    async def get_latest_height(self) -> int:
        """
        Get the latest block height

        Returns:
            Latest block height

        Raises:
            Exception: On API error
        """
        logger.debug("🔍 Fetching latest block height...")

        try:
            data = await self._make_request("GET", f"{self.rpc_url}/status")

            if not data or 'result' not in data:
                logger.error("Invalid response structure", data_keys=list(data.keys()) if data else None)
                raise ValueError("Invalid response from status endpoint")

            height = int(data['result']['sync_info']['latest_block_height'])

            logger.info(f"📊 Latest height: {height}")

            return height

        except Exception as e:
            logger.error("Failed to get latest height", exc=e)
            raise

    async def get_block(self, height: int) -> Optional[Dict[str, Any]]:
        """
        Get block by height

        Args:
            height: Block height

        Returns:
            Block data dict or None if not found
        """
        logger.debug(f"🔍 Fetching block #{height}...")

        try:
            data = await self._make_request(
                "GET",
                f"{self.rpc_url}/block",
                params={'height': height}
            )

            if data is None:
                logger.warning(f"Block #{height} not found")
                return None

            if 'result' not in data:
                logger.error(f"Invalid block response", height=height)
                return None

            block = data['result']

            # Log block details
            tx_count = len(block['block']['data'].get('txs', []))
            timestamp = block['block']['header']['time']

            logger.debug(
                f"✓ Block #{height}",
                transactions=tx_count,
                timestamp=timestamp,
                hash=block['block_id']['hash'][:16] + "..."
            )

            return block

        except Exception as e:
            logger.error(f"Failed to get block #{height}", exc=e)
            raise

    async def get_block_results(self, height: int) -> Optional[Dict[str, Any]]:
        """
        Get block results (transaction results, events)

        Args:
            height: Block height

        Returns:
            Block results dict or None if not found
        """
        logger.debug(f"🔍 Fetching block results for #{height}...")

        try:
            data = await self._make_request(
                "GET",
                f"{self.rpc_url}/block_results",
                params={'height': height}
            )

            if data is None:
                logger.warning(f"Block results #{height} not found")
                return None

            if 'result' not in data:
                logger.error(f"Invalid block results response", height=height)
                return None

            results = data['result']

            # Log results info
            tx_results = results.get('txs_results', [])
            logger.debug(
                f"✓ Block results #{height}",
                tx_count=len(tx_results),
                has_begin_block=bool(results.get('begin_block_events')),
                has_end_block=bool(results.get('end_block_events'))
            )

            return results

        except Exception as e:
            logger.error(f"Failed to get block results #{height}", exc=e)
            raise

    async def get_validators(self, height: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get validators at specific height

        Args:
            height: Block height (latest if None)

        Returns:
            List of validator info
        """
        logger.debug(f"🔍 Fetching validators", height=height or "latest")

        try:
            params = {'height': height} if height else {}
            data = await self._make_request(
                "GET",
                f"{self.rpc_url}/validators",
                params=params
            )

            if not data or 'result' not in data:
                logger.error("Invalid validators response")
                return []

            validators = data['result'].get('validators', [])

            logger.info(
                f"✓ Fetched {len(validators)} validators",
                height=height or "latest"
            )

            return validators

        except Exception as e:
            logger.error("Failed to get validators", exc=e, height=height)
            raise

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction by hash

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data or None if not found
        """
        logger.debug(f"🔍 Fetching transaction", hash=tx_hash[:16] + "...")

        try:
            data = await self._make_request(
                "GET",
                f"{self.rpc_url}/tx",
                params={'hash': f"0x{tx_hash}"}
            )

            if data is None:
                logger.warning(f"Transaction not found", hash=tx_hash[:16] + "...")
                return None

            if 'result' not in data:
                logger.error("Invalid transaction response", hash=tx_hash[:16] + "...")
                return None

            tx = data['result']

            logger.debug(
                f"✓ Transaction found",
                hash=tx_hash[:16] + "...",
                height=tx.get('height')
            )

            return tx

        except Exception as e:
            logger.error("Failed to get transaction", exc=e, hash=tx_hash[:16] + "...")
            raise

    async def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get account information

        Args:
            address: Babylon address

        Returns:
            Account data or None if not found
        """
        logger.debug(f"🔍 Fetching account", address=address[:16] + "...")

        try:
            data = await self._make_request(
                "GET",
                f"{self.rest_url}/cosmos/auth/v1beta1/accounts/{address}"
            )

            if data is None:
                logger.warning(f"Account not found", address=address[:16] + "...")
                return None

            account = data.get('account')

            logger.debug(
                f"✓ Account found",
                address=address[:16] + "...",
                type=account.get('@type', 'unknown') if account else None
            )

            return account

        except Exception as e:
            logger.error("Failed to get account", exc=e, address=address[:16] + "...")
            return None

    async def get_balance(self, address: str) -> List[Dict[str, Any]]:
        """
        Get account balances

        Args:
            address: Babylon address

        Returns:
            List of balance objects
        """
        logger.debug(f"🔍 Fetching balance", address=address[:16] + "...")

        try:
            data = await self._make_request(
                "GET",
                f"{self.rest_url}/cosmos/bank/v1beta1/balances/{address}"
            )

            if data is None:
                logger.warning(f"Balance not found", address=address[:16] + "...")
                return []

            balances = data.get('balances', [])

            logger.debug(
                f"✓ Balance fetched",
                address=address[:16] + "...",
                num_denoms=len(balances)
            )

            return balances

        except Exception as e:
            logger.error("Failed to get balance", exc=e, address=address[:16] + "...")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get RPC client statistics"""
        avg_duration = (
            self.stats["total_duration_ms"] / self.stats["successful_requests"]
            if self.stats["successful_requests"] > 0
            else 0
        )

        stats = {
            **self.stats,
            "avg_duration_ms": round(avg_duration, 2),
            "success_rate": (
                round(self.stats["successful_requests"] / self.stats["total_requests"] * 100, 2)
                if self.stats["total_requests"] > 0
                else 0
            )
        }

        logger.log_metric("rpc_stats", stats["total_requests"], "requests", stats)

        return stats

    async def close(self):
        """Close HTTP session"""
        logger.log_shutdown("BabylonRPCClient", "Closing HTTP session")
        await self.session.aclose()
        logger.info("✓ RPC Client closed")


# Test the RPC client
async def test_rpc_client():
    """Test RPC client functionality"""
    print("\n" + "=" * 80)
    print("Testing Babylon RPC Client")
    print("=" * 80 + "\n")

    client = BabylonRPCClient()

    try:
        # Test getting latest height
        print("\n📊 Test 1: Get Latest Height")
        print("-" * 80)
        height = await client.get_latest_height()
        print(f"✓ Latest height: {height}")

        # Test getting a block
        print("\n📦 Test 2: Get Block")
        print("-" * 80)
        test_height = max(1, height - 10)  # Get a recent block
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

        # Test getting validators
        print("\n👥 Test 4: Get Validators")
        print("-" * 80)
        validators = await client.get_validators()
        print(f"✓ Found {len(validators)} validators")

        # Print statistics
        print("\n📈 RPC Client Statistics")
        print("-" * 80)
        stats = client.get_stats()
        for key, value in stats.items():
            print(f"  - {key}: {value}")

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_rpc_client())
