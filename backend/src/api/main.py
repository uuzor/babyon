"""
Babylon Genesis On-Chain Analytics API
FastAPI application with REST endpoints for analytics data
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional, List
import uvicorn

from ..utils.logger import DebugLogger
from ..utils.config import get_settings
from ..database.connection import Database
from ..analytics.portfolio import PortfolioTracker
from ..analytics.metrics import NetworkMetrics
from ..analytics.smart_money import SmartMoneyScorer

logger = DebugLogger("api")

print("="*80)
print("🚀 Initializing Babylon Analytics API")
print("="*80)

# Initialize FastAPI app
app = FastAPI(
    title="Babylon Genesis Analytics API",
    description="On-chain analytics for Babylon Genesis Chain",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and analytics modules
db = Database()
portfolio_tracker = PortfolioTracker(db)
network_metrics = NetworkMetrics(db)
smart_money_scorer = SmartMoneyScorer(db)

settings = get_settings()

print("✓ FastAPI application initialized")
print(f"✓ API documentation: http://localhost:8000/docs")
print("="*80 + "\n")


# ============================================================================
# Health Check & Info Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    logger.info("📍 Root endpoint accessed")

    return {
        "name": "Babylon Genesis Analytics API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "blockchain": "/blockchain/overview",
            "addresses": "/addresses/{address}",
            "portfolio": "/portfolio/{address}",
            "smart_money": "/smart-money/top",
            "metrics": "/metrics/transactions"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("🏥 Health check")

    try:
        # Test database connection
        async with db.get_session() as session:
            await session.execute("SELECT 1")

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "chain_id": settings.chain_id
        }
    except Exception as e:
        logger.error("Health check failed", exc=e)
        raise HTTPException(status_code=503, detail="Service unavailable")


# ============================================================================
# Blockchain Overview Endpoints
# ============================================================================

@app.get("/blockchain/overview")
async def get_blockchain_overview():
    """Get comprehensive blockchain statistics"""
    logger.info("📊 GET /blockchain/overview")
    print("\n📊 API Request: GET /blockchain/overview")

    try:
        overview = await network_metrics.get_blockchain_overview()

        logger.log_api_response(200, "/blockchain/overview", len(str(overview)), 0)

        return overview

    except Exception as e:
        logger.error("Failed to get blockchain overview", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Address Endpoints
# ============================================================================

@app.get("/addresses/{address}")
async def get_address_info(address: str):
    """Get address information and portfolio summary"""
    logger.info(f"📍 GET /addresses/{address[:16]}...")
    print(f"\n📍 API Request: GET /addresses/{address[:16]}...")

    try:
        summary = await portfolio_tracker.get_portfolio_summary(address)

        logger.log_api_response(200, f"/addresses/{address[:16]}", len(str(summary)), 0)

        return summary

    except Exception as e:
        logger.error(f"Failed to get address info for {address[:16]}", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/addresses/{address}/holdings")
async def get_address_holdings(address: str):
    """Get current token holdings for an address"""
    logger.info(f"💰 GET /addresses/{address[:16]}/holdings")
    print(f"\n💰 API Request: GET /addresses/{address[:16]}/holdings")

    try:
        holdings = await portfolio_tracker.get_current_holdings(address)

        logger.log_api_response(200, f"/addresses/{address[:16]}/holdings", len(str(holdings)), 0)

        return {
            "address": address,
            "holdings": holdings,
            "num_tokens": len(holdings)
        }

    except Exception as e:
        logger.error(f"Failed to get holdings for {address[:16]}", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/addresses/{address}/history")
async def get_address_history(
    address: str,
    denom: str = Query(default="ubbn", description="Token denomination"),
    days: int = Query(default=30, description="Number of days of history"),
    interval_hours: int = Query(default=24, description="Sampling interval in hours")
):
    """Get historical balance for an address"""
    logger.info(f"📈 GET /addresses/{address[:16]}/history")
    print(f"\n📈 API Request: GET /addresses/{address[:16]}/history")

    try:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days)

        history = await portfolio_tracker.get_historical_balance(
            address,
            denom=denom,
            from_date=from_date,
            to_date=to_date,
            interval_hours=interval_hours
        )

        logger.log_api_response(200, f"/addresses/{address[:16]}/history", len(str(history)), 0)

        return {
            "address": address,
            "denom": denom,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "interval_hours": interval_hours,
            "snapshots": history
        }

    except Exception as e:
        logger.error(f"Failed to get history for {address[:16]}", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Portfolio Endpoints
# ============================================================================

@app.get("/portfolio/{address}/pnl")
async def get_portfolio_pnl(
    address: str,
    denom: str = Query(default="ubbn", description="Token denomination")
):
    """Get profit/loss analysis for an address"""
    logger.info(f"💹 GET /portfolio/{address[:16]}/pnl")
    print(f"\n💹 API Request: GET /portfolio/{address[:16]}/pnl")

    try:
        pnl = await portfolio_tracker.calculate_pnl(address, denom=denom)

        logger.log_api_response(200, f"/portfolio/{address[:16]}/pnl", len(str(pnl)), 0)

        return pnl

    except Exception as e:
        logger.error(f"Failed to get PnL for {address[:16]}", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/top-holders")
async def get_top_holders(
    denom: str = Query(default="ubbn", description="Token denomination"),
    limit: int = Query(default=100, description="Number of top holders")
):
    """Get top token holders"""
    logger.info(f"🏆 GET /portfolio/top-holders")
    print(f"\n🏆 API Request: GET /portfolio/top-holders")

    try:
        holders = await portfolio_tracker.get_top_holders(denom=denom, limit=limit)

        logger.log_api_response(200, "/portfolio/top-holders", len(str(holders)), 0)

        return {
            "denom": denom,
            "limit": limit,
            "holders": holders
        }

    except Exception as e:
        logger.error("Failed to get top holders", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Metrics Endpoints
# ============================================================================

@app.get("/metrics/transactions")
async def get_transaction_metrics(
    hours: int = Query(default=24, description="Time period in hours")
):
    """Get transaction metrics for a time period"""
    logger.info(f"📊 GET /metrics/transactions")
    print(f"\n📊 API Request: GET /metrics/transactions")

    try:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(hours=hours)

        metrics = await network_metrics.get_transaction_metrics(from_date, to_date)

        logger.log_api_response(200, "/metrics/transactions", len(str(metrics)), 0)

        return metrics

    except Exception as e:
        logger.error("Failed to get transaction metrics", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/addresses")
async def get_address_metrics(
    hours: int = Query(default=24, description="Time period in hours")
):
    """Get active address metrics"""
    logger.info(f"👥 GET /metrics/addresses")
    print(f"\n👥 API Request: GET /metrics/addresses")

    try:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(hours=hours)

        metrics = await network_metrics.get_active_addresses(from_date, to_date)

        logger.log_api_response(200, "/metrics/addresses", len(str(metrics)), 0)

        return metrics

    except Exception as e:
        logger.error("Failed to get address metrics", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/transfers")
async def get_transfer_metrics(
    hours: int = Query(default=24, description="Time period in hours"),
    denom: Optional[str] = Query(default=None, description="Token denomination filter")
):
    """Get transfer volume metrics"""
    logger.info(f"💸 GET /metrics/transfers")
    print(f"\n💸 API Request: GET /metrics/transfers")

    try:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(hours=hours)

        metrics = await network_metrics.get_transfer_metrics(from_date, to_date, denom=denom)

        logger.log_api_response(200, "/metrics/transfers", len(str(metrics)), 0)

        return metrics

    except Exception as e:
        logger.error("Failed to get transfer metrics", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/growth")
async def get_network_growth(
    days: int = Query(default=30, description="Number of days"),
    interval_days: int = Query(default=1, description="Sampling interval in days")
):
    """Get network growth metrics over time"""
    logger.info(f"📈 GET /metrics/growth")
    print(f"\n📈 API Request: GET /metrics/growth")

    try:
        growth = await network_metrics.get_network_growth(days=days, interval_days=interval_days)

        logger.log_api_response(200, "/metrics/growth", len(str(growth)), 0)

        return {
            "days": days,
            "interval_days": interval_days,
            "data": growth
        }

    except Exception as e:
        logger.error("Failed to get network growth", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Smart Money Endpoints
# ============================================================================

@app.get("/smart-money/{address}")
async def get_smart_money_score(address: str):
    """Get smart money score for an address"""
    logger.info(f"🧠 GET /smart-money/{address[:16]}")
    print(f"\n🧠 API Request: GET /smart-money/{address[:16]}")

    try:
        score, details = await smart_money_scorer.calculate_smart_money_score(address)

        # Save to database
        await smart_money_scorer.save_smart_money_score(address, score, details)

        logger.log_api_response(200, f"/smart-money/{address[:16]}", len(str(details)), 0)

        return details

    except Exception as e:
        logger.error(f"Failed to get smart money score for {address[:16]}", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/smart-money/top")
async def get_top_smart_money(
    limit: int = Query(default=100, description="Number of addresses to return"),
    min_score: int = Query(default=50, description="Minimum smart money score")
):
    """Get top smart money addresses"""
    logger.info(f"🏆 GET /smart-money/top")
    print(f"\n🏆 API Request: GET /smart-money/top")

    try:
        top_addresses = await smart_money_scorer.get_top_smart_money(limit=limit, min_score=min_score)

        logger.log_api_response(200, "/smart-money/top", len(str(top_addresses)), 0)

        return {
            "limit": limit,
            "min_score": min_score,
            "count": len(top_addresses),
            "addresses": top_addresses
        }

    except Exception as e:
        logger.error("Failed to get top smart money", exc=e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.log_startup("FastAPI", {
        "title": app.title,
        "version": app.version,
        "docs": "/docs"
    })

    print("\n" + "="*80)
    print("✅ Babylon Analytics API Started")
    print("="*80)
    print(f"📚 Documentation: http://localhost:8000/docs")
    print(f"📊 API Status: http://localhost:8000/")
    print(f"🏥 Health Check: http://localhost:8000/health")
    print("="*80 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.log_shutdown("FastAPI", "Application shutting down")

    await db.close()

    print("\n" + "="*80)
    print("👋 Babylon Analytics API Stopped")
    print("="*80 + "\n")


# ============================================================================
# Run Server
# ============================================================================

def main():
    """Run the FastAPI server"""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )


if __name__ == "__main__":
    main()


print("✓ FastAPI application loaded successfully!")
print("="*80)
