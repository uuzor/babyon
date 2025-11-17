"""
ML-Based Address Classifier
Uses XGBoost to classify addresses based on extracted features
"""
import asyncio
import pickle
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import numpy as np
from datetime import datetime

try:
    from xgboost import XGBClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not available - ML classifier will use placeholder")

from ..utils.logger import DebugLogger
from ..database.connection import Database
from ..database.models import AddressMetadata
from .feature_extractor import FeatureExtractor

logger = DebugLogger("ml_classifier")

print("="*80)
print("🤖 Loading ML-Based Address Classifier")
print("="*80)


class MLAddressClassifier:
    """
    Machine learning-based address classifier using XGBoost

    Labels:
    - exchange
    - validator
    - whale
    - bot
    - relayer
    - regular (default)
    """

    def __init__(self, db: Database, model_path: Optional[str] = None):
        """
        Initialize ML classifier

        Args:
            db: Database connection
            model_path: Path to load pre-trained model (None = create new)
        """
        print("\n" + "="*80)
        print("🤖 Initializing ML Classifier")
        print("="*80)

        self.db = db
        self.feature_extractor = FeatureExtractor(db)

        if not XGBOOST_AVAILABLE:
            print("❌ XGBoost not installed!")
            print("   Install with: pip install xgboost scikit-learn")
            print("   ML classifier will not work until installed.")
            self.model = None
            self.scaler = None
            self.label_encoder = None
            return

        # Initialize model components
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )

        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False

        # Load pre-trained model if path provided
        if model_path and Path(model_path).exists():
            self.load_model(model_path)

        logger.log_startup("MLAddressClassifier", {
            "xgboost_available": XGBOOST_AVAILABLE,
            "model_loaded": self.is_trained
        })

        print("✓ ML classifier initialized")
        if self.is_trained:
            print("✓ Pre-trained model loaded")
        else:
            print("  ℹ️  Model not trained yet")
        print("="*80 + "\n")

    async def train(self, min_samples_per_class: int = 10):
        """
        Train the ML model using labeled addresses from database

        Args:
            min_samples_per_class: Minimum number of samples required per class
        """
        if not XGBOOST_AVAILABLE:
            print("❌ Cannot train - XGBoost not installed")
            return

        print("\n" + "="*80)
        print("🎓 Training ML Classifier")
        print("="*80)

        logger.info("Starting ML model training")

        # Get labeled addresses from database
        print("📊 Fetching labeled addresses from database...")

        async with self.db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(AddressMetadata)
                .where(AddressMetadata.label_type.isnot(None))
            )
            labeled_metadata = result.scalars().all()

        if not labeled_metadata:
            print("❌ No labeled addresses found in database!")
            print("   Run heuristic labeler first to generate training data:")
            print("   python -m src.enrichment.address_labeler")
            logger.warning("No labeled addresses found for training")
            return

        print(f"✓ Found {len(labeled_metadata)} labeled addresses")

        # Count samples per class
        label_counts = {}
        for meta in labeled_metadata:
            label_counts[meta.label_type] = label_counts.get(meta.label_type, 0) + 1

        print(f"\n📊 Label distribution:")
        for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {label.upper()}: {count:,}")

        # Filter classes with insufficient samples
        valid_labels = {label for label, count in label_counts.items() if count >= min_samples_per_class}

        if len(valid_labels) < 2:
            print(f"\n❌ Insufficient data for training!")
            print(f"   Need at least {min_samples_per_class} samples per class for 2+ classes")
            print(f"   Currently have {len(valid_labels)} valid classes")
            return

        # Extract features for all labeled addresses
        print(f"\n🔬 Extracting features for {len(labeled_metadata)} addresses...")

        features_list = []
        labels_list = []
        addresses_processed = 0

        for i, meta in enumerate(labeled_metadata):
            if meta.label_type not in valid_labels:
                continue

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(labeled_metadata)} ({(i+1)/len(labeled_metadata)*100:.1f}%)")

            features = await self.feature_extractor.extract(meta.address)

            if features is not None:
                features_list.append(features)
                labels_list.append(meta.label_type)
                addresses_processed += 1

        if addresses_processed < min_samples_per_class * len(valid_labels):
            print(f"\n❌ Failed to extract enough features!")
            print(f"   Extracted features for only {addresses_processed} addresses")
            return

        print(f"\n✓ Successfully extracted features for {addresses_processed} addresses")

        # Convert to numpy arrays
        X = np.array(features_list)
        y = np.array(labels_list)

        print(f"\n📊 Training data shape: {X.shape}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Samples: {X.shape[0]}")
        print(f"   Classes: {len(set(y))}")

        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded,
            test_size=0.2,
            random_state=42,
            stratify=y_encoded
        )

        print(f"\n📊 Train/test split:")
        print(f"   Training samples: {len(X_train)}")
        print(f"   Test samples: {len(X_test)}")

        # Train model
        print(f"\n🎓 Training XGBoost classifier...")

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        self.is_trained = True

        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        print(f"\n✅ Training complete!")
        print(f"   Training accuracy: {train_score:.2%}")
        print(f"   Test accuracy: {test_score:.2%}")

        # Detailed classification report
        y_pred = self.model.predict(X_test)
        class_names = self.label_encoder.classes_

        print(f"\n📊 Classification Report:")
        print("-"*80)

        report = classification_report(
            y_test, y_pred,
            target_names=class_names,
            output_dict=True
        )

        for label in class_names:
            metrics = report[label]
            print(f"  {label.upper():12} - Precision: {metrics['precision']:.2%} | Recall: {metrics['recall']:.2%} | F1: {metrics['f1-score']:.2%}")

        print(f"\n  Overall accuracy: {report['accuracy']:.2%}")
        print("-"*80)

        # Feature importance
        print(f"\n🔍 Top 10 Most Important Features:")
        feature_names = self.feature_extractor.get_feature_names()
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:10]

        for i, idx in enumerate(indices, 1):
            print(f"  {i:2}. {feature_names[idx]:30} - {importances[idx]:.4f}")

        print("="*80 + "\n")

        logger.log_metric("ml_model_trained", 1, "count", {
            "train_accuracy": round(train_score, 4),
            "test_accuracy": round(test_score, 4),
            "num_samples": int(X.shape[0]),
            "num_classes": len(class_names),
        })

    async def predict(self, address: str) -> Tuple[Optional[str], float]:
        """
        Predict label for an address

        Args:
            address: Babylon address

        Returns:
            (predicted_label, confidence) or (None, 0.0) if prediction fails
        """
        if not XGBOOST_AVAILABLE or not self.is_trained:
            logger.warning("ML model not available or not trained")
            return None, 0.0

        logger.debug(f"🔮 Predicting label for {address[:16]}...")

        # Extract features
        features = await self.feature_extractor.extract(address)

        if features is None:
            logger.warning(f"Could not extract features for {address[:16]}")
            return None, 0.0

        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # Predict
        prediction_encoded = self.model.predict(features_scaled)[0]
        prediction_proba = self.model.predict_proba(features_scaled)[0]

        # Decode label
        predicted_label = self.label_encoder.inverse_transform([prediction_encoded])[0]
        confidence = float(prediction_proba.max())

        logger.log_ml_prediction("XGBoostClassifier", 1, predicted_label, confidence)
        print(f"  🤖 ML Prediction: {predicted_label.upper()} (confidence: {confidence:.2%})")

        return predicted_label, confidence

    async def predict_batch(self, addresses: List[str]) -> Dict[str, Tuple[Optional[str], float]]:
        """
        Predict labels for multiple addresses

        Args:
            addresses: List of addresses

        Returns:
            Dictionary mapping address -> (label, confidence)
        """
        if not XGBOOST_AVAILABLE or not self.is_trained:
            logger.warning("ML model not available or not trained")
            return {addr: (None, 0.0) for addr in addresses}

        print(f"\n🤖 ML predictions for {len(addresses)} addresses...")

        results = {}

        for i, address in enumerate(addresses):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(addresses)} ({(i+1)/len(addresses)*100:.1f}%)")

            label, confidence = await self.predict(address)
            results[address] = (label, confidence)

        successful = sum(1 for label, _ in results.values() if label is not None)
        print(f"  ✓ Successfully predicted {successful}/{len(addresses)} addresses")

        return results

    def save_model(self, model_path: str):
        """
        Save trained model to disk

        Args:
            model_path: Path to save model file
        """
        if not self.is_trained:
            logger.warning("Cannot save - model not trained")
            return

        print(f"\n💾 Saving ML model to: {model_path}")

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "label_encoder": self.label_encoder,
            "feature_names": self.feature_extractor.get_feature_names(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"✓ Model saved successfully")
        logger.info(f"Model saved to {model_path}")

    def load_model(self, model_path: str):
        """
        Load trained model from disk

        Args:
            model_path: Path to model file
        """
        print(f"\n📂 Loading ML model from: {model_path}")

        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.label_encoder = model_data["label_encoder"]
            self.is_trained = True

            print(f"✓ Model loaded successfully")
            print(f"  Trained on: {model_data['timestamp']}")
            print(f"  Classes: {', '.join(self.label_encoder.classes_)}")

            logger.info(f"Model loaded from {model_path}")

        except Exception as e:
            logger.error(f"Failed to load model from {model_path}", exc=e)
            print(f"❌ Failed to load model: {e}")


# Utility function for training from command line
async def train_model_from_database():
    """Train ML model using labeled addresses from database"""
    from ..database.connection import Database

    print("\n" + "="*80)
    print("🎓 ML Model Training Utility")
    print("="*80)

    db = Database()
    classifier = MLAddressClassifier(db)

    await classifier.train(min_samples_per_class=10)

    # Save model
    model_dir = Path(__file__).parent.parent.parent / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / f"address_classifier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

    if classifier.is_trained:
        classifier.save_model(str(model_path))

    await db.close()

    print("\n✅ Training complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(train_model_from_database())


print("✓ ML-based address classifier loaded successfully!")
print("="*80)
