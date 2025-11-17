"""
RPC Client Factory - Auto-selects between Real and Mock RPC
Attempts real RPC first, falls back to mock if unavailable
"""
import asyncio
from typing import Union
from .logger import DebugLogger
from .config import get_settings
from .rpc_client import BabylonRPCClient
from .mock_rpc import MockBabylonRPCClient

logger = DebugLogger("rpc_factory")


async def create_rpc_client(force_mock: bool = False) -> Union[BabylonRPCClient, MockBabylonRPCClient]:
    """
    Create RPC client - tries real RPC first, falls back to mock

    Args:
        force_mock: Force mock mode even if real RPC is available

    Returns:
        RPC client instance (real or mock)
    """
    settings = get_settings()

    print("\n" + "=" * 80)
    print("🔌 Initializing Babylon RPC Client")
    print("=" * 80)

    if force_mock:
        logger.info("⚠️  MOCK mode forced via configuration")
        print("⚠️  Using MOCK RPC (forced)")
        print("=" * 80 + "\n")
        return MockBabylonRPCClient()

    # Try real RPC first
    logger.info("🔍 Testing real RPC endpoint...", url=settings.babylon_rpc_url)
    print(f"🔍 Testing: {settings.babylon_rpc_url}")

    try:
        client = BabylonRPCClient()

        # Test connection
        logger.debug("Testing RPC connection with /status endpoint...")
        print("   Testing connection...")

        height = await asyncio.wait_for(client.get_latest_height(), timeout=10.0)

        logger.info(f"✅ Real RPC connected successfully! Height: {height}")
        print(f"✅ Real RPC connected! Current height: {height}")
        print("=" * 80 + "\n")

        return client

    except asyncio.TimeoutError:
        logger.warning("⏱️  RPC connection timeout - falling back to mock")
        print("⏱️  Connection timeout")
        await client.close()

    except Exception as e:
        logger.warning(f"❌ Real RPC unavailable: {type(e).__name__}", error=str(e)[:100])
        print(f"❌ RPC Error: {type(e).__name__}: {str(e)[:80]}")
        try:
            await client.close()
        except:
            pass

    # Fall back to mock
    logger.info("🎭 Falling back to MOCK RPC for development")
    print("🎭 Using MOCK RPC (real RPC unavailable)")
    print("💡 This is normal for development/testing")
    print("=" * 80 + "\n")

    return MockBabylonRPCClient()


async def test_rpc_factory():
    """Test the RPC factory"""
    print("\n" + "=" * 80)
    print("Testing RPC Factory")
    print("=" * 80 + "\n")

    # Test auto-detection
    print("📝 Test 1: Auto-detect (will try real, fall back to mock)")
    print("-" * 80)
    client = await create_rpc_client()

    # Test a few operations
    print("\n📊 Getting latest height...")
    height = await client.get_latest_height()
    print(f"✓ Height: {height}")

    print("\n📦 Getting block...")
    block = await client.get_block(height - 1 if height > 1 else 1)
    if block:
        print(f"✓ Block fetched: {block['block_id']['hash'][:32]}...")

    print("\n👥 Getting validators...")
    validators = await client.get_validators()
    print(f"✓ Validators: {len(validators)}")

    # Get stats
    stats = client.get_stats()
    print("\n📈 RPC Stats:")
    print(f"  Mode: {stats.get('mode', 'REAL')}")
    if 'total_requests' in stats:
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Success Rate: {stats['success_rate']}%")

    await client.close()

    print("\n" + "=" * 80)
    print("✓ RPC Factory test complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_rpc_factory())
