"""
ML Model Manager
模型版本管理和监控
"""

import os
import json
import pickle
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("model_manager")
settings = get_settings()


@dataclass
class ModelMetadata:
    """Model metadata"""
    name: str
    version: str
    model_type: str  # lstm, xgboost, ensemble
    
    # Training info
    trained_at: str = ""
    training_duration: float = 0.0
    training_samples: int = 0
    
    # Metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Status
    stage: str = "development"  # development, staging, production
    is_active: bool = False
    
    # Artifact
    artifact_path: str = ""
    artifact_size: int = 0
    checksum: str = ""


class ModelRegistry:
    """
    Local ML model registry
    
    For production, consider MLflow, Weights & Biases, or similar
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir or "models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_file = self.model_dir / "registry.json"
        self._registry: Dict[str, Dict[str, ModelMetadata]] = {}
        
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                
                for name, versions in data.items():
                    self._registry[name] = {}
                    for version, meta in versions.items():
                        self._registry[name][version] = ModelMetadata(**meta)
                
                logger.info(f"Loaded model registry: {len(self._registry)} models")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self._registry = {}
    
    def _save_registry(self):
        """Save registry to file"""
        try:
            data = {}
            for name, versions in self._registry.items():
                data[name] = {}
                for version, meta in versions.items():
                    data[name][version] = asdict(meta)
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _compute_checksum(self, file_path: Path) -> str:
        """Compute file checksum"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def register_model(
        self,
        name: str,
        version: str,
        model: Any,
        model_type: str,
        metrics: Dict[str, float] = None,
        stage: str = "development"
    ) -> ModelMetadata:
        """
        Register and save a model
        """
        # Create artifact path
        artifact_name = f"{name}_{version}.pkl"
        artifact_path = self.model_dir / artifact_name
        
        # Save model
        with open(artifact_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Create metadata
        metadata = ModelMetadata(
            name=name,
            version=version,
            model_type=model_type,
            trained_at=datetime.utcnow().isoformat(),
            metrics=metrics or {},
            stage=stage,
            artifact_path=str(artifact_path),
            artifact_size=artifact_path.stat().st_size,
            checksum=self._compute_checksum(artifact_path)
        )
        
        # Add to registry
        if name not in self._registry:
            self._registry[name] = {}
        self._registry[name][version] = metadata
        
        self._save_registry()
        logger.info(f"Registered model: {name} v{version}")
        
        return metadata
    
    def load_model(self, name: str, version: Optional[str] = None) -> Any:
        """
        Load a model
        
        Args:
            name: Model name
            version: Specific version, or None for production/latest
        """
        if name not in self._registry:
            raise ValueError(f"Model '{name}' not found")
        
        versions = self._registry[name]
        
        if version:
            if version not in versions:
                raise ValueError(f"Version '{version}' not found for model '{name}'")
            metadata = versions[version]
        else:
            # Get production model, or latest
            production = [v for v in versions.values() if v.stage == "production"]
            if production:
                metadata = production[0]
            else:
                # Get latest by version
                latest_version = max(versions.keys())
                metadata = versions[latest_version]
        
        # Load model file
        with open(metadata.artifact_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"Loaded model: {name} v{metadata.version}")
        return model
    
    def promote_model(self, name: str, version: str, stage: str):
        """Promote model to new stage"""
        if name not in self._registry or version not in self._registry[name]:
            raise ValueError(f"Model {name} v{version} not found")
        
        self._registry[name][version].stage = stage
        
        # If promoting to production, demote others
        if stage == "production":
            for v, meta in self._registry[name].items():
                if v != version and meta.stage == "production":
                    meta.stage = "archived"
        
        self._save_registry()
        logger.info(f"Promoted {name} v{version} to {stage}")
    
    def list_models(self, name: Optional[str] = None) -> List[ModelMetadata]:
        """List all models or versions of specific model"""
        if name:
            if name not in self._registry:
                return []
            return list(self._registry[name].values())
        
        return [
            meta
            for versions in self._registry.values()
            for meta in versions.values()
        ]
    
    def get_production_model(self, name: str) -> Optional[ModelMetadata]:
        """Get production model metadata"""
        if name not in self._registry:
            return None
        
        for meta in self._registry[name].values():
            if meta.stage == "production":
                return meta
        return None
    
    def delete_model(self, name: str, version: str):
        """Delete a model version"""
        if name not in self._registry or version not in self._registry[name]:
            raise ValueError(f"Model {name} v{version} not found")
        
        metadata = self._registry[name][version]
        
        # Delete file
        if os.path.exists(metadata.artifact_path):
            os.remove(metadata.artifact_path)
        
        # Remove from registry
        del self._registry[name][version]
        if not self._registry[name]:
            del self._registry[name]
        
        self._save_registry()
        logger.info(f"Deleted model: {name} v{version}")


# ============================================================================
# Model Monitor
# ============================================================================

@dataclass
class PredictionLog:
    """Prediction log entry"""
    model_name: str
    model_version: str
    symbol: str
    prediction: float
    confidence: float
    timestamp: str
    actual: Optional[float] = None
    error: Optional[float] = None


class ModelMonitor:
    """
    Monitor model predictions and performance
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir or "logs/predictions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._predictions: List[PredictionLog] = []
        self._performance: Dict[str, List[float]] = {}
    
    def log_prediction(
        self,
        model_name: str,
        model_version: str,
        symbol: str,
        prediction: float,
        confidence: float,
        actual: Optional[float] = None
    ):
        """Log a prediction"""
        error = abs(actual - prediction) if actual is not None else None
        
        log = PredictionLog(
            model_name=model_name,
            model_version=model_version,
            symbol=symbol,
            prediction=prediction,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat(),
            actual=actual,
            error=error
        )
        
        self._predictions.append(log)
        
        # Track performance
        if error is not None:
            key = f"{model_name}:{symbol}"
            if key not in self._performance:
                self._performance[key] = []
            self._performance[key].append(error)
        
        # Alert on high error
        if error is not None and error > 0.05:  # 5% threshold
            logger.warning(
                f"High prediction error: {model_name} on {symbol}, "
                f"error={error:.4f}"
            )
    
    def get_metrics(self, model_name: str, symbol: Optional[str] = None) -> Dict:
        """Get model performance metrics"""
        import numpy as np
        
        key_pattern = f"{model_name}:{symbol}" if symbol else f"{model_name}:"
        
        errors = []
        for key, vals in self._performance.items():
            if key.startswith(key_pattern):
                errors.extend(vals)
        
        if not errors:
            return {}
        
        errors = np.array(errors)
        
        return {
            "mae": float(np.mean(errors)),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "max_error": float(np.max(errors)),
            "prediction_count": len(errors)
        }
    
    def save_logs(self, date: Optional[str] = None):
        """Save prediction logs to file"""
        if not self._predictions:
            return
        
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"predictions_{date}.jsonl"
        
        with open(log_file, 'a') as f:
            for log in self._predictions:
                f.write(json.dumps(asdict(log)) + '\n')
        
        self._predictions.clear()


# Global instances
model_registry = ModelRegistry()
model_monitor = ModelMonitor()


if __name__ == "__main__":
    print("Testing Model Manager...")
    
    # Test registry
    class DummyModel:
        def predict(self, x):
            return x * 2
    
    model = DummyModel()
    
    # Register
    meta = model_registry.register_model(
        name="test_model",
        version="1.0.0",
        model=model,
        model_type="dummy",
        metrics={"mae": 0.01, "rmse": 0.02}
    )
    print(f"Registered: {meta.name} v{meta.version}")
    
    # Load
    loaded = model_registry.load_model("test_model")
    print(f"Loaded model prediction: {loaded.predict(5)}")
    
    # List
    models = model_registry.list_models()
    print(f"Models: {len(models)}")
    
    # Monitor
    model_monitor.log_prediction(
        model_name="test_model",
        model_version="1.0.0",
        symbol="GLD",
        prediction=200.0,
        confidence=0.8,
        actual=202.0
    )
    metrics = model_monitor.get_metrics("test_model")
    print(f"Metrics: {metrics}")
    
    print("\nModel manager test complete!")
