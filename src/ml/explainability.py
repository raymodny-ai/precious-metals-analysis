"""
Model Explainability Module
模型可解释性模块
SHAP and LIME for model interpretation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import warnings

from ..utils.logger import setup_logging
from ..utils.config import get_settings

logger = setup_logging("explainability")
settings = get_settings()

warnings.filterwarnings("ignore")


@dataclass
class ExplanationResult:
    """Explanation result container"""
    feature_names: List[str]
    feature_importance: Dict[str, float]
    local_explanations: Optional[np.ndarray] = None
    global_explanations: Optional[np.ndarray] = None
    base_value: Optional[float] = None
    method: str = "shap"


class SHAPExplainer:
    """
    SHAP (SHapley Additive exPlanations) Explainer
    
    Features:
    - Global feature importance
    - Local explanations for individual predictions
    - Interaction effects
    - Multiple explainer types (Tree, Kernel, Deep)
    """
    
    def __init__(self, model, model_type: str = "tree"):
        """
        Initialize SHAP explainer
        
        Args:
            model: Trained model
            model_type: 'tree', 'kernel', 'deep', or 'linear'
        """
        self.model = model
        self.model_type = model_type
        self.explainer = None
        self.shap_values = None
        self.feature_names = []
        
        try:
            import shap
            self.shap = shap
            self._initialized = True
        except ImportError:
            logger.warning("SHAP not installed. Run: pip install shap")
            self._initialized = False
    
    def fit(
        self,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
        background_samples: int = 100
    ):
        """
        Fit SHAP explainer with background data
        
        Args:
            X: Background data for explainer
            feature_names: Names of features
            background_samples: Number of background samples to use
        """
        if not self._initialized:
            return
        
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        
        # Sample background data
        if len(X) > background_samples:
            indices = np.random.choice(len(X), background_samples, replace=False)
            background = X[indices]
        else:
            background = X
        
        # Create explainer based on model type
        if self.model_type == "tree":
            try:
                self.explainer = self.shap.TreeExplainer(self.model)
            except Exception:
                logger.info("Falling back to KernelExplainer")
                self.explainer = self.shap.KernelExplainer(
                    self.model.predict, 
                    background
                )
        elif self.model_type == "deep":
            self.explainer = self.shap.DeepExplainer(self.model, background)
        elif self.model_type == "linear":
            self.explainer = self.shap.LinearExplainer(self.model, background)
        else:  # kernel
            self.explainer = self.shap.KernelExplainer(
                self.model.predict if hasattr(self.model, 'predict') else self.model,
                background
            )
        
        logger.info(f"SHAP explainer fitted with {len(background)} background samples")
    
    def explain(
        self,
        X: np.ndarray,
        max_samples: int = 100
    ) -> ExplanationResult:
        """
        Generate SHAP explanations
        
        Args:
            X: Data to explain
            max_samples: Maximum samples to explain
        
        Returns:
            ExplanationResult with SHAP values
        """
        if not self._initialized or self.explainer is None:
            return self._get_mock_result(X)
        
        # Limit samples
        if len(X) > max_samples:
            indices = np.random.choice(len(X), max_samples, replace=False)
            X = X[indices]
        
        # Compute SHAP values
        try:
            self.shap_values = self.explainer.shap_values(X)
            
            # Handle multi-output
            if isinstance(self.shap_values, list):
                self.shap_values = self.shap_values[0]
            
            # Global importance
            global_importance = np.abs(self.shap_values).mean(axis=0)
            
            # Feature importance dict
            importance_dict = {
                name: float(imp) 
                for name, imp in zip(self.feature_names, global_importance)
            }
            
            # Sort by importance
            importance_dict = dict(
                sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            )
            
            # Base value
            base_value = None
            if hasattr(self.explainer, 'expected_value'):
                base_value = self.explainer.expected_value
                if isinstance(base_value, np.ndarray):
                    base_value = float(base_value[0])
            
            return ExplanationResult(
                feature_names=self.feature_names,
                feature_importance=importance_dict,
                local_explanations=self.shap_values,
                global_explanations=global_importance,
                base_value=base_value,
                method="shap"
            )
            
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return self._get_mock_result(X)
    
    def explain_single(
        self,
        x: np.ndarray
    ) -> Dict[str, float]:
        """
        Explain a single prediction
        
        Returns dict of feature -> contribution
        """
        if not self._initialized or self.explainer is None:
            return {}
        
        if x.ndim == 1:
            x = x.reshape(1, -1)
        
        try:
            shap_values = self.explainer.shap_values(x)
            
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            return {
                name: float(val)
                for name, val in zip(self.feature_names, shap_values[0])
            }
        except Exception as e:
            logger.error(f"Single explanation failed: {e}")
            return {}
    
    def get_top_features(self, n: int = 10) -> List[str]:
        """Get top N important features"""
        if self.shap_values is None:
            return []
        
        importance = np.abs(self.shap_values).mean(axis=0)
        top_indices = np.argsort(importance)[-n:][::-1]
        
        return [self.feature_names[i] for i in top_indices]
    
    def _get_mock_result(self, X: np.ndarray) -> ExplanationResult:
        """Generate mock result when SHAP unavailable"""
        n_features = X.shape[1] if X.ndim > 1 else len(X)
        
        mock_importance = {
            f"feature_{i}": np.random.uniform(0, 1)
            for i in range(min(n_features, 20))
        }
        
        return ExplanationResult(
            feature_names=list(mock_importance.keys()),
            feature_importance=mock_importance,
            method="mock"
        )


class LIMEExplainer:
    """
    LIME (Local Interpretable Model-agnostic Explanations) Explainer
    
    Features:
    - Local explanations
    - Model-agnostic
    - Works with any black-box model
    """
    
    def __init__(self, model, mode: str = "regression"):
        """
        Initialize LIME explainer
        
        Args:
            model: Trained model with predict method
            mode: 'regression' or 'classification'
        """
        self.model = model
        self.mode = mode
        self.explainer = None
        self.feature_names = []
        
        try:
            import lime
            import lime.lime_tabular
            self.lime = lime
            self.lime_tabular = lime.lime_tabular
            self._initialized = True
        except ImportError:
            logger.warning("LIME not installed. Run: pip install lime")
            self._initialized = False
    
    def fit(
        self,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
        categorical_features: Optional[List[int]] = None
    ):
        """
        Fit LIME explainer
        
        Args:
            X: Training data for statistics
            feature_names: Names of features
            categorical_features: Indices of categorical features
        """
        if not self._initialized:
            return
        
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        
        self.explainer = self.lime_tabular.LimeTabularExplainer(
            X,
            feature_names=self.feature_names,
            categorical_features=categorical_features,
            mode=self.mode,
            verbose=False
        )
        
        logger.info(f"LIME explainer fitted with {len(X)} samples")
    
    def explain_instance(
        self,
        x: np.ndarray,
        num_features: int = 10
    ) -> Dict[str, float]:
        """
        Explain a single instance
        
        Args:
            x: Single instance to explain
            num_features: Number of features to include
        
        Returns:
            Dict of feature -> contribution
        """
        if not self._initialized or self.explainer is None:
            return {}
        
        if x.ndim > 1:
            x = x.flatten()
        
        try:
            # Get prediction function
            if hasattr(self.model, 'predict_proba'):
                pred_fn = self.model.predict_proba
            else:
                pred_fn = lambda x: self.model.predict(x).reshape(-1, 1)
            
            # Generate explanation
            explanation = self.explainer.explain_instance(
                x,
                pred_fn,
                num_features=num_features
            )
            
            # Extract feature contributions
            return dict(explanation.as_list())
            
        except Exception as e:
            logger.error(f"LIME explanation failed: {e}")
            return {}
    
    def explain_batch(
        self,
        X: np.ndarray,
        num_features: int = 10,
        max_samples: int = 50
    ) -> List[Dict[str, float]]:
        """
        Explain multiple instances
        """
        if len(X) > max_samples:
            indices = np.random.choice(len(X), max_samples, replace=False)
            X = X[indices]
        
        explanations = []
        for x in X:
            exp = self.explain_instance(x, num_features)
            explanations.append(exp)
        
        return explanations


class FeatureImportanceVisualizer:
    """
    Visualize feature importance from various sources
    """
    
    def __init__(self):
        pass
    
    def plot_importance(
        self,
        importance: Dict[str, float],
        title: str = "Feature Importance",
        top_n: int = 20,
        save_path: Optional[str] = None
    ) -> Optional[Any]:
        """
        Plot feature importance bar chart
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not installed")
            return None
        
        # Sort and limit
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
        features, values = zip(*sorted_importance)
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, max(6, len(features) * 0.3)))
        
        y_pos = np.arange(len(features))
        ax.barh(y_pos, values, color='steelblue')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        ax.set_xlabel('Importance')
        ax.set_title(title)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        
        return fig
    
    def generate_report(
        self,
        shap_result: Optional[ExplanationResult] = None,
        model_importance: Optional[Dict[str, float]] = None,
        top_n: int = 15
    ) -> Dict[str, Any]:
        """
        Generate comprehensive importance report
        """
        report = {
            "top_features": [],
            "importance_sources": []
        }
        
        if shap_result:
            report["importance_sources"].append("shap")
            sorted_shap = sorted(
                shap_result.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            for feature, importance in sorted_shap:
                report["top_features"].append({
                    "feature": feature,
                    "shap_importance": importance,
                    "model_importance": model_importance.get(feature, 0) if model_importance else 0
                })
        elif model_importance:
            report["importance_sources"].append("model")
            sorted_model = sorted(
                model_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            for feature, importance in sorted_model:
                report["top_features"].append({
                    "feature": feature,
                    "model_importance": importance
                })
        
        return report


# Convenience functions
def explain_model(
    model,
    X: np.ndarray,
    feature_names: Optional[List[str]] = None,
    method: str = "shap"
) -> ExplanationResult:
    """
    Convenience function to explain model
    """
    if method == "shap":
        explainer = SHAPExplainer(model, model_type="kernel")
        explainer.fit(X, feature_names)
        return explainer.explain(X)
    else:
        raise ValueError(f"Unknown method: {method}")


if __name__ == "__main__":
    # Test explainability
    print("Testing Explainability Module...")
    
    # Create simple test model
    from sklearn.ensemble import RandomForestRegressor
    
    X = np.random.randn(200, 10)
    y = X[:, 0] * 2 + X[:, 1] * 1.5 + np.random.randn(200) * 0.1
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    feature_names = [f"feature_{i}" for i in range(10)]
    
    # Test SHAP
    print("\nTesting SHAP Explainer...")
    shap_exp = SHAPExplainer(model, model_type="tree")
    shap_exp.fit(X, feature_names)
    result = shap_exp.explain(X[:50])
    
    print(f"Top 5 features: {list(result.feature_importance.keys())[:5]}")
    print(f"Top feature importance: {list(result.feature_importance.values())[:5]}")
    
    # Test single explanation
    single_exp = shap_exp.explain_single(X[0])
    print(f"\nSingle explanation (first 3): {list(single_exp.items())[:3]}")
    
    # Test LIME
    print("\nTesting LIME Explainer...")
    lime_exp = LIMEExplainer(model)
    lime_exp.fit(X, feature_names)
    lime_result = lime_exp.explain_instance(X[0])
    print(f"LIME result: {list(lime_result.items())[:3]}")
    
    print("\nExplainability tests complete!")
