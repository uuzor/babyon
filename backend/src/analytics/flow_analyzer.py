"""
Transaction Flow Analyzer
Traces money flow between addresses, detects wash trading and circular flows
"""
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import networkx as nx
from sqlalchemy import select, and_, or_

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import Transfer, AddressMetadata

logger = DebugLogger("flow_analyzer")

print("="*80)
print("🔄 Loading Transaction Flow Analyzer")
print("="*80)


class TransactionFlowAnalyzer:
    """
    Analyze transaction flows and detect suspicious patterns

    Features:
    - Money flow tracing
    - Circular flow detection (wash trading)
    - Flow path analysis
    - Suspicious pattern detection
    """

    def __init__(self, db: Database):
        """Initialize flow analyzer"""
        print("\n" + "="*80)
        print("🔄 Initializing Transaction Flow Analyzer")
        print("="*80)

        self.db = db

        logger.log_startup("TransactionFlowAnalyzer", {
            "features": ["flow_tracing", "cycle_detection", "wash_trading_detection"]
        })

        print("✓ Transaction flow analyzer initialized")
        print("="*80 + "\n")

    async def trace_flow(
        self,
        origin_address: str,
        max_depth: int = 5,
        min_amount: int = 0,
        denom: str = 'ubbn',
        time_window_hours: Optional[int] = None
    ) -> nx.DiGraph:
        """
        Trace money flow from origin address

        Args:
            origin_address: Starting address
            max_depth: Maximum depth to trace
            min_amount: Minimum transfer amount to include
            denom: Token denomination
            time_window_hours: Optional time window (from now backwards)

        Returns:
            Directed graph of money flows
        """
        logger.info(f"🔍 Tracing flow from {origin_address[:16]}... (depth: {max_depth})")
        print(f"\n🔍 Tracing Money Flow")
        print("="*80)
        print(f"Origin: {origin_address[:16]}...")
        print(f"Max depth: {max_depth}")
        print(f"Min amount: {min_amount/1e9:.2f} BABY" if denom == 'ubbn' else f"{min_amount}")
        print(f"Token: {denom}")

        flow_graph = nx.DiGraph()
        visited = set()
        to_explore = deque([(origin_address, 0)])  # (address, depth)

        # Build time filter if specified
        time_filter = None
        if time_window_hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            print(f"Time window: Last {time_window_hours} hours")

        transfers_found = 0

        async with self.db.get_session() as session:
            while to_explore:
                current_address, depth = to_explore.popleft()

                if depth > max_depth or current_address in visited:
                    continue

                visited.add(current_address)

                # Get outgoing transfers
                query = select(Transfer).where(and_(
                    Transfer.from_address == current_address,
                    Transfer.denom == denom,
                    Transfer.amount >= min_amount
                ))

                if time_window_hours:
                    query = query.where(Transfer.timestamp >= cutoff_time)

                result = await session.execute(query.limit(1000))  # Limit for performance
                transfers = result.scalars().all()

                for transfer in transfers:
                    # Add edge to graph
                    flow_graph.add_edge(
                        transfer.from_address,
                        transfer.to_address,
                        amount=transfer.amount,
                        timestamp=transfer.timestamp,
                        tx_hash=transfer.tx_hash,
                        denom=transfer.denom
                    )

                    transfers_found += 1

                    # Add destination to exploration queue
                    if depth < max_depth:
                        to_explore.append((transfer.to_address, depth + 1))

        print(f"\n✓ Flow graph constructed:")
        print(f"  Nodes (addresses): {flow_graph.number_of_nodes()}")
        print(f"  Edges (transfers): {flow_graph.number_of_edges()}")
        print(f"  Max depth reached: {max_depth}")
        print(f"  Transfers traced: {transfers_found}")

        logger.log_metric("flow_traced", transfers_found, "transfers", {
            "origin": origin_address[:16],
            "nodes": flow_graph.number_of_nodes(),
            "edges": flow_graph.number_of_edges()
        })

        return flow_graph

    async def detect_circular_flows(
        self,
        flow_graph: nx.DiGraph,
        max_cycle_length: int = 5
    ) -> List[Dict]:
        """
        Detect circular money flows (potential wash trading)

        Args:
            flow_graph: Transaction flow graph
            max_cycle_length: Maximum cycle length to detect

        Returns:
            List of detected cycles with analysis
        """
        logger.info(f"🔄 Detecting circular flows (max length: {max_cycle_length})...")
        print(f"\n🔄 Detecting Circular Flows")
        print("="*80)
        print(f"Max cycle length: {max_cycle_length}")

        try:
            # Find all simple cycles
            cycles = list(nx.simple_cycles(flow_graph))

            # Filter by length
            cycles = [c for c in cycles if len(c) <= max_cycle_length]

            print(f"\n✓ Found {len(cycles)} cycles")

            suspicious_cycles = []

            for cycle in cycles:
                # Calculate cycle metrics
                cycle_analysis = await self._analyze_cycle(flow_graph, cycle)

                # Cycles are suspicious if:
                # 1. Short length (2-3 addresses)
                # 2. High volume
                # 3. Rapid execution
                # 4. Balanced flow (money returns to origin)

                suspicion_score = 0

                # Short cycle (+30 points)
                if len(cycle) <= 3:
                    suspicion_score += 30

                # High volume (+30 points if > 1000 BABY)
                if cycle_analysis['total_volume'] > 1000 * 1e9:
                    suspicion_score += 30

                # Rapid execution (+20 points if < 1 hour)
                if cycle_analysis['duration_seconds'] < 3600:
                    suspicion_score += 20

                # Balanced flow (+20 points if balance > 90%)
                if cycle_analysis['balance_ratio'] > 0.9:
                    suspicion_score += 20

                cycle_analysis['suspicion_score'] = suspicion_score

                if suspicion_score >= 50:  # Threshold
                    suspicious_cycles.append(cycle_analysis)

            # Sort by suspicion score
            suspicious_cycles.sort(key=lambda x: x['suspicion_score'], reverse=True)

            print(f"\n⚠️  Suspicious cycles: {len(suspicious_cycles)}")

            # Display top suspicious cycles
            for i, cycle_data in enumerate(suspicious_cycles[:10], 1):
                print(f"\n  {i}. Cycle with {len(cycle_data['cycle'])} addresses")
                print(f"     Suspicion score: {cycle_data['suspicion_score']}/100")
                print(f"     Total volume: {cycle_data['total_volume']/1e9:,.2f} BABY")
                print(f"     Duration: {cycle_data['duration_seconds']/60:.1f} minutes")
                print(f"     Balance ratio: {cycle_data['balance_ratio']*100:.1f}%")
                print(f"     Addresses: {' → '.join([addr[:8] for addr in cycle_data['cycle'][:3]])}...")

            print("="*80)

            logger.log_metric("circular_flows_detected", len(suspicious_cycles), "cycles", {
                "total_cycles": len(cycles),
                "suspicious_cycles": len(suspicious_cycles)
            })

            return suspicious_cycles

        except Exception as e:
            logger.error("Failed to detect circular flows", exc=e)
            print(f"❌ Error detecting cycles: {e}")
            return []

    async def _analyze_cycle(self, flow_graph: nx.DiGraph, cycle: List[str]) -> Dict:
        """
        Analyze a cycle in detail

        Args:
            flow_graph: Transaction flow graph
            cycle: List of addresses forming a cycle

        Returns:
            Cycle analysis dict
        """
        # Reconstruct cycle with first address repeated at end
        full_cycle = cycle + [cycle[0]]

        total_volume = 0
        timestamps = []
        tx_hashes = []

        # Trace edges in cycle
        for i in range(len(full_cycle) - 1):
            from_addr = full_cycle[i]
            to_addr = full_cycle[i + 1]

            if flow_graph.has_edge(from_addr, to_addr):
                edge_data = flow_graph[from_addr][to_addr]
                total_volume += edge_data.get('amount', 0)
                timestamps.append(edge_data.get('timestamp'))
                tx_hashes.append(edge_data.get('tx_hash'))

        # Calculate duration
        if timestamps:
            timestamps = [ts for ts in timestamps if ts]
            if timestamps:
                duration_seconds = (max(timestamps) - min(timestamps)).total_seconds()
            else:
                duration_seconds = 0
        else:
            duration_seconds = 0

        # Calculate balance ratio (how much money returns to origin)
        # Simplified: assume equal distribution
        balance_ratio = 1.0 / len(cycle)  # Perfect balance would be 1.0

        return {
            "cycle": cycle,
            "length": len(cycle),
            "total_volume": total_volume,
            "duration_seconds": duration_seconds,
            "balance_ratio": balance_ratio,
            "tx_hashes": tx_hashes,
            "first_timestamp": min(timestamps) if timestamps else None,
            "last_timestamp": max(timestamps) if timestamps else None
        }

    async def find_common_paths(
        self,
        addresses: List[str],
        max_path_length: int = 5,
        denom: str = 'ubbn'
    ) -> List[Dict]:
        """
        Find common transaction paths between addresses

        Args:
            addresses: List of addresses to analyze
            max_path_length: Maximum path length
            denom: Token denomination

        Returns:
            List of common paths
        """
        logger.info(f"🛤️  Finding common paths between {len(addresses)} addresses...")
        print(f"\n🛤️  Finding Common Transaction Paths")
        print("="*80)
        print(f"Addresses: {len(addresses)}")
        print(f"Max path length: {max_path_length}")

        # Build combined flow graph
        combined_graph = nx.DiGraph()

        for address in addresses:
            # Trace flow for each address
            flow_graph = await self.trace_flow(
                address,
                max_depth=max_path_length,
                denom=denom
            )

            # Merge into combined graph
            combined_graph = nx.compose(combined_graph, flow_graph)

        print(f"\n✓ Combined graph:")
        print(f"  Total nodes: {combined_graph.number_of_nodes()}")
        print(f"  Total edges: {combined_graph.number_of_edges()}")

        # Find paths between each pair of input addresses
        common_paths = []

        for i, source in enumerate(addresses):
            for target in addresses[i+1:]:
                if source == target:
                    continue

                try:
                    # Find shortest path
                    if nx.has_path(combined_graph, source, target):
                        path = nx.shortest_path(combined_graph, source, target)

                        if len(path) <= max_path_length + 1:
                            # Calculate path metrics
                            total_volume = 0
                            for j in range(len(path) - 1):
                                if combined_graph.has_edge(path[j], path[j+1]):
                                    edge_data = combined_graph[path[j]][path[j+1]]
                                    total_volume += edge_data.get('amount', 0)

                            common_paths.append({
                                "source": source,
                                "target": target,
                                "path": path,
                                "length": len(path) - 1,  # Number of hops
                                "total_volume": total_volume
                            })

                except nx.NetworkXNoPath:
                    pass

        print(f"\n✓ Found {len(common_paths)} common paths")

        # Display top paths
        common_paths.sort(key=lambda x: x['total_volume'], reverse=True)

        for i, path_data in enumerate(common_paths[:5], 1):
            print(f"\n  {i}. {path_data['source'][:8]}... → {path_data['target'][:8]}...")
            print(f"     Hops: {path_data['length']}")
            print(f"     Volume: {path_data['total_volume']/1e9:,.2f} BABY")
            print(f"     Path: {' → '.join([addr[:8] for addr in path_data['path'][:4]])}...")

        print("="*80)

        logger.log_metric("common_paths_found", len(common_paths), "paths", {
            "addresses": len(addresses),
            "max_length": max_path_length
        })

        return common_paths

    async def detect_wash_trading(
        self,
        address: str,
        time_window_hours: int = 24,
        min_cycle_count: int = 3
    ) -> Dict:
        """
        Detect wash trading patterns for an address

        Args:
            address: Address to analyze
            time_window_hours: Time window for analysis
            min_cycle_count: Minimum number of cycles to flag

        Returns:
            Wash trading analysis
        """
        logger.info(f"🔍 Detecting wash trading for {address[:16]}...")
        print(f"\n🔍 Wash Trading Detection")
        print("="*80)
        print(f"Address: {address[:16]}...")
        print(f"Time window: {time_window_hours} hours")

        # Trace flow
        flow_graph = await self.trace_flow(
            address,
            max_depth=3,  # Short depth for wash trading
            denom='ubbn',
            time_window_hours=time_window_hours
        )

        # Detect cycles
        suspicious_cycles = await self.detect_circular_flows(
            flow_graph,
            max_cycle_length=3
        )

        # Wash trading indicators
        is_wash_trading = len(suspicious_cycles) >= min_cycle_count

        analysis = {
            "address": address,
            "time_window_hours": time_window_hours,
            "is_wash_trading": is_wash_trading,
            "cycle_count": len(suspicious_cycles),
            "min_cycle_threshold": min_cycle_count,
            "suspicious_cycles": suspicious_cycles,
            "risk_score": min(len(suspicious_cycles) * 20, 100)  # 20 points per cycle, max 100
        }

        # Display results
        if is_wash_trading:
            print(f"\n⚠️  WASH TRADING DETECTED")
            print(f"   Suspicious cycles: {len(suspicious_cycles)}")
            print(f"   Risk score: {analysis['risk_score']}/100")
        else:
            print(f"\n✅ No wash trading detected")
            print(f"   Cycles found: {len(suspicious_cycles)} (threshold: {min_cycle_count})")

        print("="*80)

        logger.log_metric("wash_trading_detected", 1 if is_wash_trading else 0, "address", analysis)

        return analysis


print("✓ Transaction flow analyzer loaded successfully!")
print("="*80)
