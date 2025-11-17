"""
Address Clustering System
Groups addresses that likely belong to the same entity
"""
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import networkx as nx
import numpy as np

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️  scikit-learn not available - clustering will use heuristics only")

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import Transaction, Transfer
from ..enrichment.feature_extractor import FeatureExtractor
from sqlalchemy import select, and_, or_, func

logger = DebugLogger("address_clustering")

print("="*80)
print("🔗 Loading Address Clustering System")
print("="*80)


class AddressClusterer:
    """
    Cluster addresses that likely belong to the same entity

    Methods:
    - Multi-input heuristic (addresses in same transaction)
    - Temporal correlation (addresses that transact together)
    - Behavioral similarity (using ML features)
    - Co-spending analysis
    """

    def __init__(self, db: Database):
        """Initialize address clusterer"""
        print("\n" + "="*80)
        print("🔗 Initializing Address Clusterer")
        print("="*80)

        self.db = db
        self.feature_extractor = FeatureExtractor(db)

        logger.log_startup("AddressClusterer", {
            "sklearn_available": SKLEARN_AVAILABLE,
            "methods": ["multi_input", "temporal", "behavioral"]
        })

        print("✓ Address clusterer initialized")
        print("✓ Methods: Multi-input, Temporal, Behavioral")
        print("="*80 + "\n")

    async def cluster_by_multi_input(
        self,
        min_cluster_size: int = 2
    ) -> List[Set[str]]:
        """
        Cluster addresses using multi-input heuristic

        If multiple addresses appear as inputs in the same transaction,
        they likely belong to the same entity (common in UTXO-like models)

        Args:
            min_cluster_size: Minimum cluster size to return

        Returns:
            List of address clusters (sets)
        """
        logger.info("🔍 Clustering by multi-input heuristic...")
        print(f"\n🔍 Multi-Input Clustering")
        print("="*80)

        # Build co-spending graph
        G = nx.Graph()

        print("📊 Building co-spending graph...")

        async with self.db.get_session() as session:
            # Get all transactions with their senders
            # Note: In Cosmos SDK, typically one sender per tx, but we'll check for patterns
            result = await session.execute(
                select(Transaction.hash, Transaction.sender)
                .where(Transaction.sender.isnot(None))
            )
            transactions = result.all()

            print(f"✓ Loaded {len(transactions):,} transactions")

            # Group addresses that appear together
            # In Cosmos, we look for patterns like:
            # - Same sender across multiple related transactions
            # - Addresses that frequently transfer to each other

            # Build transfer connections
            transfer_result = await session.execute(
                select(Transfer.from_address, Transfer.to_address, func.count(Transfer.id).label('count'))
                .group_by(Transfer.from_address, Transfer.to_address)
                .having(func.count(Transfer.id) > 3)  # At least 3 transfers
            )
            frequent_transfers = transfer_result.all()

            print(f"✓ Found {len(frequent_transfers):,} frequent transfer pairs")

            # Add edges for frequent transfers (bidirectional)
            for from_addr, to_addr, count in frequent_transfers:
                if from_addr and to_addr and from_addr != to_addr:
                    # Weight by transfer frequency
                    if G.has_edge(from_addr, to_addr):
                        G[from_addr][to_addr]['weight'] += count
                    else:
                        G.add_edge(from_addr, to_addr, weight=count)

        print(f"\n✓ Co-spending graph constructed:")
        print(f"  Nodes: {G.number_of_nodes():,}")
        print(f"  Edges: {G.number_of_edges():,}")

        # Find connected components (clusters)
        clusters = list(nx.connected_components(G))

        # Filter by minimum size
        clusters = [c for c in clusters if len(c) >= min_cluster_size]

        # Sort by size
        clusters.sort(key=len, reverse=True)

        print(f"\n✓ Clusters found: {len(clusters)}")
        print(f"  Clusters with ≥{min_cluster_size} addresses: {len(clusters)}")

        # Display top clusters
        print(f"\n🏆 Top Clusters:")
        print("-"*80)
        for i, cluster in enumerate(clusters[:10], 1):
            print(f"  {i:3}. Cluster with {len(cluster):,} addresses")
            sample = list(cluster)[:3]
            print(f"       Sample: {', '.join([addr[:8]+'...' for addr in sample])}")

        print("="*80 + "\n")

        logger.log_metric("multi_input_clustering", len(clusters), "clusters", {
            "total_addresses": sum(len(c) for c in clusters),
            "min_cluster_size": min_cluster_size
        })

        return clusters

    async def cluster_by_temporal_correlation(
        self,
        time_window_seconds: int = 3600,
        min_correlation: float = 0.7,
        sample_size: int = 1000
    ) -> List[Set[str]]:
        """
        Cluster addresses by temporal transaction patterns

        Addresses that transact at similar times may be controlled by same entity

        Args:
            time_window_seconds: Time window for correlation
            min_correlation: Minimum correlation coefficient
            sample_size: Number of addresses to analyze

        Returns:
            List of address clusters
        """
        logger.info("🕐 Clustering by temporal correlation...")
        print(f"\n🕐 Temporal Correlation Clustering")
        print("="*80)
        print(f"Time window: {time_window_seconds/3600:.1f} hours")
        print(f"Min correlation: {min_correlation}")

        # Sample addresses
        async with self.db.get_session() as session:
            result = await session.execute(
                select(Transaction.sender.distinct())
                .where(Transaction.sender.isnot(None))
                .order_by(func.random())
                .limit(sample_size)
            )
            addresses = [row[0] for row in result.all()]

        print(f"\n📊 Analyzing {len(addresses)} addresses...")

        # Get transaction timestamps for each address
        address_timestamps = {}

        for i, address in enumerate(addresses):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(addresses)}")

            async with self.db.get_session() as session:
                result = await session.execute(
                    select(Transaction.timestamp)
                    .where(Transaction.sender == address)
                    .order_by(Transaction.timestamp)
                )
                timestamps = [row[0] for row in result.all()]
                address_timestamps[address] = timestamps

        # Build similarity graph based on temporal patterns
        G = nx.Graph()

        print(f"\n🔍 Calculating temporal correlations...")

        addresses_list = list(address_timestamps.keys())

        for i in range(len(addresses_list)):
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(addresses_list)}")

            addr1 = addresses_list[i]
            timestamps1 = address_timestamps[addr1]

            if len(timestamps1) < 5:  # Need minimum activity
                continue

            for j in range(i + 1, len(addresses_list)):
                addr2 = addresses_list[j]
                timestamps2 = address_timestamps[addr2]

                if len(timestamps2) < 5:
                    continue

                # Calculate temporal similarity
                # Check if transaction times overlap within window
                overlap_count = 0
                for ts1 in timestamps1:
                    for ts2 in timestamps2:
                        if abs((ts1 - ts2).total_seconds()) < time_window_seconds:
                            overlap_count += 1
                            break

                # Correlation score
                max_possible = min(len(timestamps1), len(timestamps2))
                if max_possible > 0:
                    correlation = overlap_count / max_possible

                    if correlation >= min_correlation:
                        G.add_edge(addr1, addr2, correlation=correlation)

        print(f"\n✓ Correlation graph constructed:")
        print(f"  Nodes: {G.number_of_nodes():,}")
        print(f"  Edges: {G.number_of_edges():,}")

        # Find clusters
        clusters = list(nx.connected_components(G))

        # Filter by size
        clusters = [c for c in clusters if len(c) >= 2]
        clusters.sort(key=len, reverse=True)

        print(f"\n✓ Temporal clusters found: {len(clusters)}")

        # Display top clusters
        print(f"\n🏆 Top Temporal Clusters:")
        print("-"*80)
        for i, cluster in enumerate(clusters[:5], 1):
            print(f"  {i}. Cluster with {len(cluster)} addresses")

        print("="*80 + "\n")

        logger.log_metric("temporal_clustering", len(clusters), "clusters", {
            "time_window_seconds": time_window_seconds,
            "min_correlation": min_correlation
        })

        return clusters

    async def cluster_by_behavioral_similarity(
        self,
        eps: float = 0.5,
        min_samples: int = 3,
        sample_size: int = 500
    ) -> List[Set[str]]:
        """
        Cluster addresses by behavioral similarity using DBSCAN

        Args:
            eps: DBSCAN epsilon (neighborhood size)
            min_samples: Minimum samples per cluster
            sample_size: Number of addresses to analyze

        Returns:
            List of address clusters
        """
        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn not available - cannot perform behavioral clustering")
            return []

        logger.info("🧠 Clustering by behavioral similarity...")
        print(f"\n🧠 Behavioral Similarity Clustering (DBSCAN)")
        print("="*80)
        print(f"Epsilon: {eps}")
        print(f"Min samples: {min_samples}")

        # Sample addresses
        async with self.db.get_session() as session:
            result = await session.execute(
                select(Transaction.sender.distinct())
                .where(Transaction.sender.isnot(None))
                .order_by(func.random())
                .limit(sample_size)
            )
            addresses = [row[0] for row in result.all()]

        print(f"\n🔬 Extracting features for {len(addresses)} addresses...")

        # Extract features
        features_list = []
        valid_addresses = []

        for i, address in enumerate(addresses):
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(addresses)}")

            features = await self.feature_extractor.extract(address)
            if features is not None:
                features_list.append(features)
                valid_addresses.append(address)

        if len(features_list) < min_samples * 2:
            print(f"❌ Insufficient data for clustering")
            return []

        print(f"\n✓ Extracted features for {len(features_list)} addresses")

        # Convert to numpy array
        X = np.array(features_list)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Apply DBSCAN
        print(f"\n🔍 Running DBSCAN clustering...")
        dbscan = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
        labels = dbscan.fit_predict(X_scaled)

        # Group addresses by cluster
        clusters_dict = defaultdict(set)
        for i, label in enumerate(labels):
            if label != -1:  # -1 is noise
                clusters_dict[label].add(valid_addresses[i])

        clusters = list(clusters_dict.values())

        noise_count = np.sum(labels == -1)

        print(f"\n✓ DBSCAN clustering complete:")
        print(f"  Clusters found: {len(clusters)}")
        print(f"  Addresses clustered: {sum(len(c) for c in clusters):,}")
        print(f"  Noise (unclustered): {noise_count:,}")

        # Display top clusters
        clusters.sort(key=len, reverse=True)

        print(f"\n🏆 Top Behavioral Clusters:")
        print("-"*80)
        for i, cluster in enumerate(clusters[:5], 1):
            print(f"  {i}. Cluster with {len(cluster)} addresses")
            sample = list(cluster)[:3]
            print(f"     Sample: {', '.join([addr[:8]+'...' for addr in sample])}")

        print("="*80 + "\n")

        logger.log_metric("behavioral_clustering", len(clusters), "clusters", {
            "eps": eps,
            "min_samples": min_samples,
            "noise_count": int(noise_count)
        })

        return clusters

    async def merge_clusters(
        self,
        cluster_sets: List[List[Set[str]]]
    ) -> List[Set[str]]:
        """
        Merge overlapping clusters from different methods

        Args:
            cluster_sets: List of cluster lists from different methods

        Returns:
            Merged clusters
        """
        logger.info("🔀 Merging clusters from different methods...")
        print(f"\n🔀 Merging Clusters")
        print("="*80)

        # Flatten all clusters
        all_clusters = []
        for cluster_set in cluster_sets:
            all_clusters.extend(cluster_set)

        print(f"Input clusters: {len(all_clusters)}")

        # Build union-find structure to merge overlapping clusters
        address_to_cluster = {}

        for cluster_id, cluster in enumerate(all_clusters):
            for address in cluster:
                if address not in address_to_cluster:
                    address_to_cluster[address] = set()
                address_to_cluster[address].add(cluster_id)

        # Merge clusters that share addresses
        merged = defaultdict(set)
        cluster_groups = {}  # Maps cluster_id to merged_id

        merged_id = 0
        for cluster_id, cluster in enumerate(all_clusters):
            # Find if any address in this cluster is already in a merged group
            existing_groups = set()
            for address in cluster:
                for other_cluster_id in address_to_cluster[address]:
                    if other_cluster_id in cluster_groups:
                        existing_groups.add(cluster_groups[other_cluster_id])

            if existing_groups:
                # Merge into existing group
                target_group = min(existing_groups)
                cluster_groups[cluster_id] = target_group
                merged[target_group].update(cluster)

                # Merge all existing groups
                for group_id in existing_groups:
                    if group_id != target_group:
                        merged[target_group].update(merged[group_id])
                        del merged[group_id]
            else:
                # Create new group
                cluster_groups[cluster_id] = merged_id
                merged[merged_id].update(cluster)
                merged_id += 1

        final_clusters = list(merged.values())

        # Sort by size
        final_clusters.sort(key=len, reverse=True)

        print(f"\n✓ Merged clusters: {len(final_clusters)}")
        print(f"  Total addresses: {sum(len(c) for c in final_clusters):,}")

        # Display top merged clusters
        print(f"\n🏆 Top Merged Clusters:")
        print("-"*80)
        for i, cluster in enumerate(final_clusters[:10], 1):
            print(f"  {i:3}. Cluster with {len(cluster):,} addresses")

        print("="*80 + "\n")

        logger.log_metric("clusters_merged", len(final_clusters), "clusters", {
            "input_clusters": len(all_clusters),
            "total_addresses": sum(len(c) for c in final_clusters)
        })

        return final_clusters

    async def cluster_all_methods(
        self,
        sample_size: int = 500
    ) -> List[Set[str]]:
        """
        Run all clustering methods and merge results

        Args:
            sample_size: Number of addresses to sample

        Returns:
            Final merged clusters
        """
        print(f"\n{'='*80}")
        print("🔗 COMPREHENSIVE ADDRESS CLUSTERING")
        print(f"{'='*80}")

        all_cluster_sets = []

        # Method 1: Multi-input
        print("\n1️⃣  Running multi-input clustering...")
        multi_input_clusters = await self.cluster_by_multi_input(min_cluster_size=2)
        all_cluster_sets.append(multi_input_clusters)

        # Method 2: Temporal
        print("\n2️⃣  Running temporal correlation clustering...")
        temporal_clusters = await self.cluster_by_temporal_correlation(
            time_window_seconds=3600,
            min_correlation=0.7,
            sample_size=sample_size
        )
        all_cluster_sets.append(temporal_clusters)

        # Method 3: Behavioral (if sklearn available)
        if SKLEARN_AVAILABLE:
            print("\n3️⃣  Running behavioral similarity clustering...")
            behavioral_clusters = await self.cluster_by_behavioral_similarity(
                eps=0.5,
                min_samples=3,
                sample_size=sample_size
            )
            all_cluster_sets.append(behavioral_clusters)

        # Merge all results
        print("\n4️⃣  Merging results...")
        final_clusters = await self.merge_clusters(all_cluster_sets)

        print(f"\n{'='*80}")
        print("✅ CLUSTERING COMPLETE")
        print(f"{'='*80}\n")

        return final_clusters


print("✓ Address clustering system loaded successfully!")
print("="*80)
