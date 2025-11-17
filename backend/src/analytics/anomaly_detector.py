"""
Anomaly Detection System
Detects unusual address behavior patterns using machine learning
"""
import asyncio
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️  scikit-learn not available - anomaly detection will use placeholder")

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..enrichment.feature_extractor import FeatureExtractor

logger = DebugLogger("anomaly_detector")

print("="*80)
print("🚨 Loading Anomaly Detection System")
print("="*80)


class AnomalyDetector:
    """
    Detect anomalous address behavior using Isolation Forest

    Features:
    - Statistical anomaly detection
    - Behavior pattern analysis
    - Risk scoring
    - Batch processing
    """

    def __init__(self, db: Database, contamination: float = 0.1):
        """
        Initialize anomaly detector

        Args:
            db: Database connection
            contamination: Expected proportion of anomalies (default: 10%)
        """
        print("\n" + "="*80)
        print("🚨 Initializing Anomaly Detector")
        print("="*80)

        self.db = db
        self.contamination = contamination
        self.feature_extractor = FeatureExtractor(db)

        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn not installed!")
            print("   Install with: pip install scikit-learn")
            print("   Anomaly detector will not work until installed.")
            self.model = None
            self.scaler = None
            self.is_fitted = False
            return

        # Initialize Isolation Forest
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1  # Use all CPU cores
        )

        self.scaler = StandardScaler()
        self.is_fitted = False

        logger.log_startup("AnomalyDetector", {
            "sklearn_available": SKLEARN_AVAILABLE,
            "contamination": contamination,
            "model": "IsolationForest"
        })

        print(f"✓ Anomaly detector initialized")
        print(f"✓ Expected anomaly rate: {contamination*100:.1f}%")
        print(f"✓ Model: Isolation Forest (100 trees)")
        print("="*80 + "\n")

    async def fit(self, addresses: Optional[List[str]] = None, sample_size: int = 1000):
        """
        Fit anomaly detection model on address features

        Args:
            addresses: List of addresses to train on (None = sample from DB)
            sample_size: Number of addresses to sample if addresses not provided
        """
        if not SKLEARN_AVAILABLE or self.model is None:
            print("❌ Cannot fit - scikit-learn not installed")
            return

        print("\n" + "="*80)
        print("🎓 Training Anomaly Detection Model")
        print("="*80)

        logger.info("Fitting anomaly detection model")

        # Get addresses to train on
        if addresses is None:
            print(f"📊 Sampling {sample_size} addresses from database...")

            async with self.db.get_session() as session:
                from sqlalchemy import select, func
                from ..database.models import Transaction

                # Sample random addresses
                result = await session.execute(
                    select(Transaction.sender.distinct())
                    .where(Transaction.sender.isnot(None))
                    .order_by(func.random())
                    .limit(sample_size)
                )
                addresses = [row[0] for row in result.all()]

            print(f"✓ Sampled {len(addresses)} addresses")
        else:
            print(f"📊 Training on {len(addresses)} provided addresses")

        # Extract features for all addresses
        print(f"\n🔬 Extracting features...")

        features_list = []
        valid_addresses = []

        for i, address in enumerate(addresses):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(addresses)} ({(i+1)/len(addresses)*100:.1f}%)")

            features = await self.feature_extractor.extract(address)

            if features is not None:
                features_list.append(features)
                valid_addresses.append(address)

        if len(features_list) < 10:
            print(f"\n❌ Insufficient data for training!")
            print(f"   Extracted features for only {len(features_list)} addresses")
            return

        print(f"\n✓ Extracted features for {len(features_list)} addresses")

        # Convert to numpy array
        X = np.array(features_list)

        print(f"\n📊 Training data shape: {X.shape}")
        print(f"   Samples: {X.shape[0]}")
        print(f"   Features: {X.shape[1]}")

        # Scale features
        print(f"\n⚖️  Scaling features...")
        X_scaled = self.scaler.fit_transform(X)

        # Fit Isolation Forest
        print(f"\n🌲 Training Isolation Forest...")
        self.model.fit(X_scaled)

        self.is_fitted = True

        print(f"\n✅ Model training complete!")
        print(f"   Trained on {X.shape[0]} addresses")
        print(f"   Feature dimensions: {X.shape[1]}")

        # Test on training data to get anomaly distribution
        predictions = self.model.predict(X_scaled)
        anomalies_found = np.sum(predictions == -1)
        anomaly_rate = anomalies_found / len(predictions) * 100

        print(f"\n📊 Training set analysis:")
        print(f"   Normal addresses: {np.sum(predictions == 1):,} ({100-anomaly_rate:.1f}%)")
        print(f"   Anomalous addresses: {anomalies_found:,} ({anomaly_rate:.1f}%)")

        print("="*80 + "\n")

        logger.log_metric("anomaly_model_fitted", X.shape[0], "addresses", {
            "features": X.shape[1],
            "anomaly_rate": round(anomaly_rate, 2)
        })

    async def detect_anomaly(self, address: str) -> Tuple[bool, float, Dict]:
        """
        Detect if an address exhibits anomalous behavior

        Args:
            address: Babylon address

        Returns:
            (is_anomaly, anomaly_score, details)
        """
        if not SKLEARN_AVAILABLE or not self.is_fitted:
            logger.warning("Model not fitted or sklearn not available")
            return False, 0.0, {"error": "model_not_fitted"}

        logger.debug(f"🔍 Detecting anomaly for {address[:16]}...")
        print(f"🔍 Anomaly detection for {address[:16]}...")

        # Extract features
        features = await self.feature_extractor.extract(address)

        if features is None:
            logger.warning(f"Could not extract features for {address[:16]}")
            return False, 0.0, {"error": "no_features"}

        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # Predict
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.score_samples(features_scaled)[0]

        is_anomaly = (prediction == -1)

        # Normalize anomaly score to 0-100 (lower score = more anomalous)
        # Typical score range is around -0.5 to 0.5
        normalized_score = max(0, min(100, (anomaly_score + 0.5) * 100))

        details = {
            "address": address,
            "is_anomaly": is_anomaly,
            "anomaly_score": float(normalized_score),
            "raw_score": float(anomaly_score),
            "prediction": int(prediction),
            "detected_at": datetime.utcnow().isoformat()
        }

        if is_anomaly:
            print(f"  ⚠️  ANOMALY DETECTED")
            print(f"  Anomaly score: {normalized_score:.1f}/100 (lower = more anomalous)")
        else:
            print(f"  ✅ Normal behavior")
            print(f"  Normality score: {normalized_score:.1f}/100")

        logger.log_metric("anomaly_detected", 1 if is_anomaly else 0, "address", details)

        return is_anomaly, normalized_score, details

    async def detect_anomalies_batch(
        self,
        addresses: List[str]
    ) -> Dict[str, Tuple[bool, float, Dict]]:
        """
        Detect anomalies for multiple addresses

        Args:
            addresses: List of addresses

        Returns:
            Dictionary mapping address -> (is_anomaly, score, details)
        """
        if not SKLEARN_AVAILABLE or not self.is_fitted:
            logger.warning("Model not fitted or sklearn not available")
            return {addr: (False, 0.0, {"error": "model_not_fitted"}) for addr in addresses}

        print(f"\n🚨 Batch Anomaly Detection")
        print("="*80)
        print(f"Addresses: {len(addresses)}")

        results = {}

        for i, address in enumerate(addresses):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(addresses)} ({(i+1)/len(addresses)*100:.1f}%)")

            is_anomaly, score, details = await self.detect_anomaly(address)
            results[address] = (is_anomaly, score, details)

        anomalies_found = sum(1 for is_anom, _, _ in results.values() if is_anom)

        print(f"\n✓ Analysis complete:")
        print(f"  Normal addresses: {len(addresses) - anomalies_found:,}")
        print(f"  Anomalous addresses: {anomalies_found:,} ({anomalies_found/len(addresses)*100:.1f}%)")
        print("="*80 + "\n")

        logger.log_metric("batch_anomaly_detection", len(addresses), "addresses", {
            "anomalies_found": anomalies_found
        })

        return results

    async def get_anomalous_addresses(
        self,
        limit: int = 100,
        min_score_threshold: float = 30.0
    ) -> List[Dict]:
        """
        Get most anomalous addresses from database

        Args:
            limit: Maximum number of addresses to analyze
            min_score_threshold: Minimum anomaly threshold (lower = more anomalous)

        Returns:
            List of anomalous addresses with scores
        """
        if not SKLEARN_AVAILABLE or not self.is_fitted:
            print("❌ Model not fitted")
            return []

        print(f"\n🚨 Finding Most Anomalous Addresses")
        print("="*80)
        print(f"Analyzing up to {limit} addresses")
        print(f"Threshold: score < {min_score_threshold}")

        # Get sample of addresses
        async with self.db.get_session() as session:
            from sqlalchemy import select, func
            from ..database.models import Transaction

            result = await session.execute(
                select(Transaction.sender.distinct())
                .where(Transaction.sender.isnot(None))
                .order_by(func.random())
                .limit(limit * 2)  # Get more than we need
            )
            addresses = [row[0] for row in result.all()]

        print(f"\n🔬 Analyzing {len(addresses)} addresses...")

        # Detect anomalies
        results = await self.detect_anomalies_batch(addresses)

        # Filter anomalous addresses
        anomalous = []
        for address, (is_anomaly, score, details) in results.items():
            if is_anomaly and score < min_score_threshold:
                # Get label if available
                async with self.db.get_session() as session:
                    from sqlalchemy import select
                    from ..database.models import AddressMetadata

                    label_result = await session.execute(
                        select(AddressMetadata.label_type)
                        .where(AddressMetadata.address == address)
                    )
                    label_row = label_result.first()
                    label = label_row[0] if label_row else None

                anomalous.append({
                    "address": address,
                    "anomaly_score": score,
                    "label": label,
                    "detected_at": details["detected_at"]
                })

        # Sort by anomaly score (lowest = most anomalous)
        anomalous.sort(key=lambda x: x['anomaly_score'])

        # Take top N
        top_anomalous = anomalous[:limit]

        print(f"\n⚠️  Top Anomalous Addresses:")
        print("-"*80)

        for i, addr_data in enumerate(top_anomalous[:20], 1):
            label_str = f"({addr_data['label'].upper()})" if addr_data['label'] else ""
            print(f"  {i:3}. {addr_data['address'][:16]}... Score: {addr_data['anomaly_score']:.1f}/100 {label_str}")

        print("="*80 + "\n")

        logger.log_metric("anomalous_addresses_found", len(top_anomalous), "addresses", {
            "threshold": min_score_threshold,
            "limit": limit
        })

        return top_anomalous

    async def analyze_anomaly_patterns(self, anomalous_addresses: List[str]) -> Dict:
        """
        Analyze common patterns among anomalous addresses

        Args:
            anomalous_addresses: List of anomalous addresses

        Returns:
            Pattern analysis
        """
        print(f"\n📊 Analyzing Anomaly Patterns")
        print("="*80)
        print(f"Addresses: {len(anomalous_addresses)}")

        # Get features for all anomalous addresses
        features_list = []

        for address in anomalous_addresses:
            features = await self.feature_extractor.extract(address)
            if features is not None:
                features_list.append(features)

        if not features_list:
            print("❌ No features extracted")
            return {}

        X = np.array(features_list)

        # Calculate statistics
        feature_names = self.feature_extractor.get_feature_names()

        pattern_analysis = {
            "num_addresses": len(anomalous_addresses),
            "feature_statistics": {}
        }

        print(f"\n📈 Feature Statistics (compared to normal):")
        print("-"*80)

        for i, feature_name in enumerate(feature_names):
            feature_values = X[:, i]

            stats = {
                "mean": float(np.mean(feature_values)),
                "std": float(np.std(feature_values)),
                "min": float(np.min(feature_values)),
                "max": float(np.max(feature_values)),
                "median": float(np.median(feature_values))
            }

            pattern_analysis["feature_statistics"][feature_name] = stats

            # Show interesting features (high variance)
            if stats['std'] > 0 and i < 10:  # Show top 10
                print(f"  {feature_name:30} Mean: {stats['mean']:10.2f} ± {stats['std']:.2f}")

        print("="*80 + "\n")

        logger.log_metric("anomaly_patterns_analyzed", len(anomalous_addresses), "addresses", {
            "features_analyzed": len(feature_names)
        })

        return pattern_analysis


print("✓ Anomaly detection system loaded successfully!")
print("="*80)
