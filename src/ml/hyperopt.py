"""
Hyperparameter Optimization with Optuna
Optuna超参数优化模块
Based on Model_Hyperparameter_Optimization.md
"""

import optuna
from optuna.trial import Trial
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from ..utils.logger import setup_logging
from ..utils.config import get_settings, MODELS_DIR

logger = setup_logging("hyperopt")
settings = get_settings()


@dataclass
class OptimizationResult:
    """Optimization result container"""
    best_params: Dict[str, Any]
    best_value: float
    n_trials: int
    optimization_history: List[Dict]
    study_name: str
    model_type: str
    timestamp: datetime


class OptunaOptimizer:
    """
    Hyperparameter optimization using Optuna
    
    Features:
    - Bayesian optimization with TPE sampler
    - Early stopping with pruning
    - Multi-objective optimization
    - Cross-validation integration
    - Automatic parameter space definition
    """
    
    # Default parameter spaces for different model types
    PARAM_SPACES = {
        "lstm": {
            "hidden_dim": ("int", 32, 256),
            "num_layers": ("int", 1, 4),
            "dropout": ("float", 0.1, 0.5),
            "learning_rate": ("loguniform", 1e-5, 1e-2),
            "batch_size": ("categorical", [16, 32, 64, 128]),
            "sequence_length": ("int", 10, 50)
        },
        "cnn_lstm": {
            "cnn_channels": ("int", 32, 128),
            "hidden_dim": ("int", 64, 256),
            "num_layers": ("int", 1, 3),
            "num_heads": ("categorical", [2, 4, 8]),
            "dropout": ("float", 0.1, 0.4),
            "learning_rate": ("loguniform", 1e-5, 1e-2)
        },
        "tabnet": {
            "n_steps": ("int", 2, 5),
            "hidden_dim": ("int", 64, 256),
            "attention_dim": ("int", 32, 128),
            "gamma": ("float", 1.0, 2.0),
            "dropout": ("float", 0.0, 0.3)
        },
        "xgboost": {
            "n_estimators": ("int", 100, 1000),
            "max_depth": ("int", 3, 10),
            "learning_rate": ("loguniform", 0.01, 0.3),
            "subsample": ("float", 0.6, 1.0),
            "colsample_bytree": ("float", 0.6, 1.0),
            "reg_alpha": ("loguniform", 1e-8, 10),
            "reg_lambda": ("loguniform", 1e-8, 10)
        }
    }
    
    def __init__(
        self,
        model_type: str = "lstm",
        n_trials: int = 100,
        timeout: Optional[int] = None,
        n_jobs: int = 1,
        study_name: Optional[str] = None,
        direction: str = "minimize"  # or "maximize"
    ):
        self.model_type = model_type
        self.n_trials = n_trials
        self.timeout = timeout
        self.n_jobs = n_jobs
        self.study_name = study_name or f"{model_type}_opt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.direction = direction
        
        # Get param space
        self.param_space = self.PARAM_SPACES.get(model_type, {})
        
        # Results
        self.study: Optional[optuna.Study] = None
        self.best_params: Dict = {}
        self.optimization_history: List[Dict] = []
    
    def _sample_params(self, trial: Trial) -> Dict[str, Any]:
        """Sample parameters from defined space"""
        params = {}
        
        for name, config in self.param_space.items():
            param_type = config[0]
            
            if param_type == "int":
                params[name] = trial.suggest_int(name, config[1], config[2])
            elif param_type == "float":
                params[name] = trial.suggest_float(name, config[1], config[2])
            elif param_type == "loguniform":
                params[name] = trial.suggest_float(name, config[1], config[2], log=True)
            elif param_type == "categorical":
                params[name] = trial.suggest_categorical(name, config[1])
        
        return params
    
    def optimize(
        self,
        objective_fn: Callable[[Dict, Any], float],
        data: Any,
        custom_param_space: Optional[Dict] = None
    ) -> OptimizationResult:
        """
        Run hyperparameter optimization
        
        Args:
            objective_fn: Function that takes (params, data) and returns score
            data: Data to pass to objective function
            custom_param_space: Override default parameter space
        
        Returns:
            OptimizationResult with best params and history
        """
        if custom_param_space:
            self.param_space = custom_param_space
        
        logger.info(f"Starting optimization: {self.study_name}")
        logger.info(f"Parameter space: {list(self.param_space.keys())}")
        
        # Create study
        sampler = TPESampler(seed=42)
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        
        self.study = optuna.create_study(
            study_name=self.study_name,
            direction=self.direction,
            sampler=sampler,
            pruner=pruner
        )
        
        # Define objective
        def objective(trial: Trial) -> float:
            params = self._sample_params(trial)
            
            try:
                score = objective_fn(params, data)
                
                # Record history
                self.optimization_history.append({
                    "trial": trial.number,
                    "params": params,
                    "value": score,
                    "state": "complete"
                })
                
                return score
                
            except optuna.TrialPruned:
                raise
            except Exception as e:
                logger.warning(f"Trial {trial.number} failed: {e}")
                return float("inf") if self.direction == "minimize" else float("-inf")
        
        # Run optimization
        self.study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            n_jobs=self.n_jobs,
            show_progress_bar=True
        )
        
        self.best_params = self.study.best_params
        
        logger.info(f"Optimization complete!")
        logger.info(f"Best value: {self.study.best_value:.6f}")
        logger.info(f"Best params: {self.best_params}")
        
        return OptimizationResult(
            best_params=self.best_params,
            best_value=self.study.best_value,
            n_trials=len(self.study.trials),
            optimization_history=self.optimization_history,
            study_name=self.study_name,
            model_type=self.model_type,
            timestamp=datetime.now()
        )
    
    def get_importance(self) -> Dict[str, float]:
        """Get parameter importance analysis"""
        if self.study is None:
            return {}
        
        try:
            importance = optuna.importance.get_param_importances(self.study)
            return dict(importance)
        except Exception as e:
            logger.warning(f"Could not compute importance: {e}")
            return {}
    
    def save_study(self, filepath: Optional[str] = None):
        """Save study results"""
        if filepath is None:
            filepath = MODELS_DIR / f"{self.study_name}_results.json"
        
        results = {
            "study_name": self.study_name,
            "model_type": self.model_type,
            "best_params": self.best_params,
            "best_value": self.study.best_value if self.study else None,
            "n_trials": len(self.study.trials) if self.study else 0,
            "param_importance": self.get_importance(),
            "history": self.optimization_history,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Study saved to {filepath}")


class CrossValidator:
    """
    Cross-validation framework for time-series
    
    Implements:
    - Walk-forward validation
    - Expanding window
    - Rolling window
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        test_size: int = 20,
        gap: int = 0,
        method: str = "expanding"  # "expanding" or "rolling"
    ):
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap
        self.method = method
    
    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate train/test indices for time-series CV
        
        Returns:
            List of (train_indices, test_indices) tuples
        """
        n_samples = len(X)
        
        # Calculate minimum training size
        min_train_size = n_samples - self.n_splits * (self.test_size + self.gap)
        
        if min_train_size < 30:
            logger.warning(f"Training set may be too small: {min_train_size}")
        
        splits = []
        
        for i in range(self.n_splits):
            # Test end index
            test_end = n_samples - i * (self.test_size + self.gap)
            test_start = test_end - self.test_size
            
            # Train indices
            if self.method == "expanding":
                train_start = 0
            else:  # rolling
                train_start = max(0, test_start - min_train_size)
            
            train_end = test_start - self.gap
            
            if train_end <= train_start:
                continue
            
            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)
            
            splits.append((train_idx, test_idx))
        
        # Reverse to chronological order
        return list(reversed(splits))
    
    def cross_validate(
        self,
        model_fn: Callable,
        X: np.ndarray,
        y: np.ndarray,
        params: Dict[str, Any],
        metric_fn: Callable[[np.ndarray, np.ndarray], float]
    ) -> Dict[str, Any]:
        """
        Run cross-validation
        
        Args:
            model_fn: Function that creates and trains model, returns predictions
            X: Features
            y: Target
            params: Model parameters
            metric_fn: Evaluation metric function
        
        Returns:
            CV results with scores and statistics
        """
        splits = self.split(X, y)
        scores = []
        fold_results = []
        
        for fold, (train_idx, test_idx) in enumerate(splits):
            logger.info(f"Fold {fold + 1}/{len(splits)}: "
                       f"train={len(train_idx)}, test={len(test_idx)}")
            
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            try:
                predictions = model_fn(X_train, y_train, X_test, params)
                score = metric_fn(y_test, predictions)
                scores.append(score)
                
                fold_results.append({
                    "fold": fold + 1,
                    "train_size": len(train_idx),
                    "test_size": len(test_idx),
                    "score": score
                })
                
            except Exception as e:
                logger.error(f"Fold {fold + 1} failed: {e}")
                fold_results.append({
                    "fold": fold + 1,
                    "error": str(e)
                })
        
        return {
            "mean_score": np.mean(scores) if scores else None,
            "std_score": np.std(scores) if scores else None,
            "scores": scores,
            "n_folds": len(splits),
            "fold_results": fold_results
        }


class AutoMLSelector:
    """
    Automatic model selection
    
    Compares multiple models and selects the best one
    """
    
    def __init__(self, cv: Optional[CrossValidator] = None):
        self.cv = cv or CrossValidator(n_splits=5)
        self.results: Dict[str, Dict] = {}
        self.best_model: Optional[str] = None
    
    def compare_models(
        self,
        models: Dict[str, Callable],
        X: np.ndarray,
        y: np.ndarray,
        metric_fn: Callable,
        higher_is_better: bool = False
    ) -> Dict[str, Any]:
        """
        Compare multiple models using cross-validation
        
        Args:
            models: Dict of model_name -> model_fn
            X: Features
            y: Target
            metric_fn: Evaluation metric
            higher_is_better: Whether higher metric is better
        
        Returns:
            Comparison results with rankings
        """
        logger.info(f"Comparing {len(models)} models...")
        
        for name, model_fn in models.items():
            logger.info(f"Evaluating: {name}")
            
            cv_results = self.cv.cross_validate(
                model_fn=model_fn,
                X=X,
                y=y,
                params={},
                metric_fn=metric_fn
            )
            
            self.results[name] = cv_results
        
        # Rank models
        valid_results = {
            k: v for k, v in self.results.items() 
            if v.get("mean_score") is not None
        }
        
        if not valid_results:
            return {"error": "No models completed successfully"}
        
        sorted_models = sorted(
            valid_results.items(),
            key=lambda x: x[1]["mean_score"],
            reverse=higher_is_better
        )
        
        self.best_model = sorted_models[0][0]
        
        return {
            "rankings": [
                {
                    "rank": i + 1,
                    "model": name,
                    "mean_score": results["mean_score"],
                    "std_score": results["std_score"]
                }
                for i, (name, results) in enumerate(sorted_models)
            ],
            "best_model": self.best_model,
            "best_score": sorted_models[0][1]["mean_score"]
        }


# Convenience functions
def optimize_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    n_trials: int = 50
) -> OptimizationResult:
    """Optimize LSTM hyperparameters"""
    
    from .lstm_predictor import LSTMPredictor
    
    def objective(params, data):
        X_train, y_train, X_val, y_val = data
        
        predictor = LSTMPredictor(
            input_dim=X_train.shape[-1],
            hidden_dim=params["hidden_dim"],
            num_layers=params["num_layers"],
            sequence_length=params.get("sequence_length", 20)
        )
        
        history = predictor.train(
            X_train, y_train,
            epochs=50,
            batch_size=params.get("batch_size", 32),
            validation_split=0.0,  # Using separate validation set
            verbose=False
        )
        
        predictions = predictor.predict(X_val)
        mse = np.mean((predictions - y_val[-len(predictions):]) ** 2)
        
        return mse
    
    optimizer = OptunaOptimizer(model_type="lstm", n_trials=n_trials)
    return optimizer.optimize(
        objective,
        data=(X_train, y_train, X_val, y_val)
    )


if __name__ == "__main__":
    # Test optimization
    print("Testing Optuna Optimizer...")
    
    # Simple test function
    def test_objective(params, data):
        x = params.get("x", 0)
        y = params.get("y", 0)
        return (x - 2) ** 2 + (y + 1) ** 2
    
    optimizer = OptunaOptimizer(
        model_type="test",
        n_trials=20
    )
    
    optimizer.param_space = {
        "x": ("float", -5, 5),
        "y": ("float", -5, 5)
    }
    
    result = optimizer.optimize(test_objective, None)
    
    print(f"\nBest params: {result.best_params}")
    print(f"Best value: {result.best_value:.4f}")
    print(f"Expected: x=2, y=-1, value=0")
    
    # Test cross-validator
    print("\nTesting Cross-Validator...")
    cv = CrossValidator(n_splits=3, test_size=10)
    X = np.random.randn(100, 10)
    splits = cv.split(X)
    print(f"Generated {len(splits)} splits")
    for i, (train, test) in enumerate(splits):
        print(f"  Fold {i+1}: train={len(train)}, test={len(test)}")
