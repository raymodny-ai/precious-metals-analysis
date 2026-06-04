"""
Advanced Deep Learning Models for Price Prediction
高级深度学习预测模型
Includes: CNN-LSTM-Attention, TabNet, XGBoost
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from ..utils.logger import setup_logging
from ..utils.config import get_settings, MODELS_DIR

logger = setup_logging("advanced_models")
settings = get_settings()


# ============================================================================
# CNN-LSTM-Attention Model
# ============================================================================

class TemporalConvBlock(nn.Module):
    """Temporal Convolutional Block for feature extraction"""
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        
        self.conv = nn.Conv1d(
            in_channels, out_channels, 
            kernel_size, padding=kernel_size // 2
        )
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(kernel_size=2, stride=1, padding=0)
    
    def forward(self, x):
        # x: (batch, seq_len, features) -> (batch, features, seq_len)
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        # Back to (batch, seq_len, features)
        x = x.transpose(1, 2)
        return x


class MultiHeadAttention(nn.Module):
    """Multi-Head Self-Attention Layer"""
    
    def __init__(self, hidden_dim: int, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"
        
        self.W_q = nn.Linear(hidden_dim, hidden_dim)
        self.W_k = nn.Linear(hidden_dim, hidden_dim)
        self.W_v = nn.Linear(hidden_dim, hidden_dim)
        self.W_o = nn.Linear(hidden_dim, hidden_dim)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5
    
    def forward(self, x, mask=None):
        batch_size, seq_len, hidden_dim = x.shape
        
        # Linear projections
        Q = self.W_q(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.W_k(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.W_v(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # Apply attention
        context = torch.matmul(attn_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, hidden_dim)
        
        output = self.W_o(context)
        
        return output, attn_weights


class CNNLSTMAttentionModel(nn.Module):
    """
    CNN-LSTM-Attention Model
    
    Architecture:
    1. CNN layers for local pattern extraction
    2. Bidirectional LSTM for sequential dependencies
    3. Multi-head attention for focusing on important timesteps
    4. Dense layers for prediction
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_heads: int = 4,
        cnn_channels: int = 64,
        dropout: float = 0.2,
        output_dim: int = 1
    ):
        super().__init__()
        
        # CNN Feature Extraction
        self.cnn1 = TemporalConvBlock(input_dim, cnn_channels, kernel_size=3)
        self.cnn2 = TemporalConvBlock(cnn_channels, cnn_channels, kernel_size=5)
        
        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=cnn_channels,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Attention
        self.attention = MultiHeadAttention(hidden_dim * 2, num_heads, dropout)
        
        # Output layers
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
        
        # Layer normalization
        self.layer_norm = nn.LayerNorm(hidden_dim * 2)
    
    def forward(self, x):
        # CNN feature extraction
        cnn_out = self.cnn1(x)
        cnn_out = self.cnn2(cnn_out)
        
        # LSTM
        lstm_out, _ = self.lstm(cnn_out)
        
        # Layer normalization
        lstm_out = self.layer_norm(lstm_out)
        
        # Attention
        attn_out, attn_weights = self.attention(lstm_out)
        
        # Residual connection
        attn_out = attn_out + lstm_out
        
        # Global average pooling over sequence
        pooled = torch.mean(attn_out, dim=1)
        
        # Output
        output = self.fc(pooled)
        
        return output, attn_weights


# ============================================================================
# TabNet Model (Interpretable Attention-based Network)
# ============================================================================

class GhostBatchNorm(nn.Module):
    """Ghost Batch Normalization for TabNet"""
    
    def __init__(self, num_features: int, virtual_batch_size: int = 128, momentum: float = 0.1):
        super().__init__()
        
        self.bn = nn.BatchNorm1d(num_features, momentum=momentum)
        self.virtual_batch_size = virtual_batch_size
    
    def forward(self, x):
        if self.training:
            chunks = x.chunk(max(1, x.size(0) // self.virtual_batch_size), dim=0)
            return torch.cat([self.bn(chunk) for chunk in chunks], dim=0)
        return self.bn(x)


class TabNetBlock(nn.Module):
    """Single TabNet Decision Step Block"""
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_dim: int,
        dropout: float = 0.1
    ):
        super().__init__()
        
        # Feature transformer
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = GhostBatchNorm(hidden_dim)
        
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = GhostBatchNorm(hidden_dim)
        
        # Attention transformer
        self.attn_fc = nn.Linear(hidden_dim, input_dim)
        self.attn_bn = GhostBatchNorm(input_dim)
        
        # Output
        self.output_fc = nn.Linear(hidden_dim, output_dim)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, prior_scales):
        # Feature transformation
        h = F.gelu(self.bn1(self.fc1(x)))
        h = self.dropout(h)
        h = F.gelu(self.bn2(self.fc2(h)))
        
        # Attention mask
        mask = F.softmax(self.attn_bn(self.attn_fc(h)) * prior_scales, dim=-1)
        
        # Apply mask
        masked_x = mask * x
        
        # Decision contribution
        decision = self.output_fc(h)
        
        return decision, mask, masked_x


class TabNetModel(nn.Module):
    """
    TabNet: Attentive Interpretable Tabular Learning
    
    Features:
    - Sequential attention for feature selection
    - Interpretable feature importance
    - Sparse attention for efficiency
    """
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int = 1,
        n_steps: int = 3,
        hidden_dim: int = 128,
        attention_dim: int = 64,
        gamma: float = 1.3,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.n_steps = n_steps
        self.gamma = gamma
        
        # Initial BN
        self.initial_bn = nn.BatchNorm1d(input_dim)
        
        # TabNet blocks
        self.blocks = nn.ModuleList([
            TabNetBlock(input_dim, hidden_dim, attention_dim, dropout)
            for _ in range(n_steps)
        ])
        
        # Final output
        self.final_fc = nn.Linear(hidden_dim * n_steps, output_dim)
    
    def forward(self, x):
        # Initial normalization
        x = self.initial_bn(x)
        
        # Prior scales (start uniform)
        prior_scales = torch.ones(x.shape).to(x.device)
        
        # Collect decisions and masks
        decisions = []
        masks = []
        
        for block in self.blocks:
            decision, mask, masked_x = block(x, prior_scales)
            decisions.append(decision)
            masks.append(mask)
            
            # Update prior scales
            prior_scales = prior_scales * (self.gamma - mask)
        
        # Aggregate decisions
        aggregated = torch.cat(decisions, dim=-1)
        output = self.final_fc(aggregated)
        
        # Feature importance (average attention across steps)
        feature_importance = torch.stack(masks, dim=0).mean(dim=0)
        
        return output, feature_importance


# ============================================================================
# XGBoost Wrapper
# ============================================================================

class XGBoostPredictor:
    """
    XGBoost Wrapper for price prediction
    
    Features:
    - Native feature importance
    - Handles missing values
    - Fast training and inference
    """
    
    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42
    ):
        try:
            import xgboost as xgb
            self.xgb = xgb
        except ImportError:
            logger.error("XGBoost not installed. Run: pip install xgboost")
            self.xgb = None
        
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "random_state": random_state,
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "n_jobs": -1
        }
        
        self.model = None
        self.feature_names = []
        self.is_trained = False
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        validation_split: float = 0.2,
        early_stopping_rounds: int = 50,
        verbose: bool = True
    ) -> Dict:
        """Train XGBoost model"""
        
        if self.xgb is None:
            raise ImportError("XGBoost not installed")
        
        self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
        
        # Split data
        n_val = int(len(X) * validation_split)
        X_train, X_val = X[:-n_val], X[-n_val:]
        y_train, y_val = y[:-n_val], y[-n_val:]
        
        # Create model
        self.model = self.xgb.XGBRegressor(**self.params)
        
        # Train
        eval_set = [(X_train, y_train), (X_val, y_val)]
        
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            early_stopping_rounds=early_stopping_rounds,
            verbose=verbose
        )
        
        self.is_trained = True
        
        # Get feature importance
        importance = self.model.feature_importances_
        
        return {
            "best_iteration": self.model.best_iteration,
            "best_score": self.model.best_score,
            "feature_importance": dict(zip(self.feature_names, importance))
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        return self.model.predict(X)
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """Get top N important features"""
        if not self.is_trained:
            return {}
        
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_importance[:top_n])


# ============================================================================
# Ensemble Model
# ============================================================================

@dataclass
class EnsemblePrediction:
    """Ensemble prediction result"""
    combined_prediction: float
    model_predictions: Dict[str, float]
    model_weights: Dict[str, float]
    confidence: float
    feature_importance: Dict[str, float]


class EnsemblePredictor:
    """
    Ensemble of multiple models for robust predictions
    
    Models:
    - CNN-LSTM-Attention (deep patterns)
    - TabNet (interpretable attention)
    - XGBoost (feature importance)
    
    Combination methods:
    - Simple average
    - Weighted average (based on validation performance)
    - Stacking
    """
    
    def __init__(
        self,
        input_dim: int,
        sequence_length: int = 20,
        device: Optional[str] = None
    ):
        self.input_dim = input_dim
        self.sequence_length = sequence_length
        
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Initialize models
        self.cnn_lstm = None
        self.tabnet = None
        self.xgboost = None
        
        # Model weights (learned from validation)
        self.weights = {
            "cnn_lstm": 0.4,
            "tabnet": 0.3,
            "xgboost": 0.3
        }
        
        self.is_trained = False
    
    def _init_models(self):
        """Initialize all models"""
        self.cnn_lstm = CNNLSTMAttentionModel(
            input_dim=self.input_dim,
            hidden_dim=128
        ).to(self.device)
        
        self.tabnet = TabNetModel(
            input_dim=self.input_dim,
            hidden_dim=128
        ).to(self.device)
        
        self.xgboost = XGBoostPredictor()
    
    def train(
        self,
        X_seq: np.ndarray,  # Sequential data for CNN-LSTM
        X_flat: np.ndarray,  # Flat features for TabNet/XGBoost
        y: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        validation_split: float = 0.2
    ) -> Dict:
        """Train all models in ensemble"""
        
        logger.info("Training ensemble models...")
        
        self._init_models()
        
        results = {}
        
        # Train CNN-LSTM-Attention
        logger.info("Training CNN-LSTM-Attention...")
        cnn_result = self._train_pytorch_model(
            self.cnn_lstm, X_seq, y, epochs, batch_size, validation_split
        )
        results["cnn_lstm"] = cnn_result
        
        # Train TabNet
        logger.info("Training TabNet...")
        tabnet_result = self._train_pytorch_model(
            self.tabnet, X_flat, y, epochs, batch_size, validation_split,
            is_sequential=False
        )
        results["tabnet"] = tabnet_result
        
        # Train XGBoost
        logger.info("Training XGBoost...")
        xgb_result = self.xgboost.train(X_flat, y, validation_split=validation_split)
        results["xgboost"] = xgb_result
        
        # Update weights based on validation performance
        self._update_weights(results)
        
        self.is_trained = True
        
        logger.info(f"Ensemble training complete. Weights: {self.weights}")
        
        return results
    
    def _train_pytorch_model(
        self,
        model,
        X,
        y,
        epochs,
        batch_size,
        validation_split,
        is_sequential=True
    ):
        """Train a PyTorch model"""
        
        # Split data
        n_val = int(len(X) * validation_split)
        X_train, X_val = X[:-n_val], X[-n_val:]
        y_train, y_val = y[:-n_val], y[-n_val:]
        
        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).unsqueeze(-1).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_val_t = torch.FloatTensor(y_val).unsqueeze(-1).to(self.device)
        
        # DataLoader
        dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Optimizer
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10)
        criterion = nn.MSELoss()
        
        best_val_loss = float("inf")
        
        for epoch in range(epochs):
            model.train()
            train_losses = []
            
            for X_batch, y_batch in loader:
                optimizer.zero_grad()
                pred, _ = model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_losses.append(loss.item())
            
            # Validation
            model.eval()
            with torch.no_grad():
                val_pred, _ = model(X_val_t)
                val_loss = criterion(val_pred, y_val_t).item()
            
            scheduler.step(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: train_loss={np.mean(train_losses):.6f}, val_loss={val_loss:.6f}")
        
        return {"best_val_loss": best_val_loss}
    
    def _update_weights(self, results: Dict):
        """Update model weights based on validation performance"""
        
        # Get inverse of validation losses (lower = better = higher weight)
        losses = {
            "cnn_lstm": results["cnn_lstm"]["best_val_loss"],
            "tabnet": results["tabnet"]["best_val_loss"],
            "xgboost": 1 / (results["xgboost"]["best_score"] + 1e-6)  # Convert score to loss-like
        }
        
        # Inverse weights
        inv_losses = {k: 1 / (v + 1e-6) for k, v in losses.items()}
        total = sum(inv_losses.values())
        
        self.weights = {k: v / total for k, v in inv_losses.items()}
    
    def predict(self, X_seq: np.ndarray, X_flat: np.ndarray) -> EnsemblePrediction:
        """Make ensemble prediction"""
        
        if not self.is_trained:
            raise ValueError("Ensemble not trained")
        
        predictions = {}
        
        # CNN-LSTM prediction
        self.cnn_lstm.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X_seq).to(self.device)
            pred, _ = self.cnn_lstm(X_t)
            predictions["cnn_lstm"] = pred.cpu().numpy().flatten()[-1]
        
        # TabNet prediction
        self.tabnet.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X_flat[-1:]).to(self.device)
            pred, feature_imp = self.tabnet(X_t)
            predictions["tabnet"] = pred.cpu().numpy().flatten()[0]
        
        # XGBoost prediction
        predictions["xgboost"] = self.xgboost.predict(X_flat[-1:])[0]
        
        # Weighted combination
        combined = sum(predictions[k] * self.weights[k] for k in predictions)
        
        # Confidence (based on agreement)
        pred_std = np.std(list(predictions.values()))
        confidence = max(0, 1 - pred_std * 10)
        
        # Combined feature importance
        xgb_importance = self.xgboost.get_feature_importance(20)
        
        return EnsemblePrediction(
            combined_prediction=combined,
            model_predictions=predictions,
            model_weights=self.weights,
            confidence=confidence,
            feature_importance=xgb_importance
        )


if __name__ == "__main__":
    # Test models
    batch_size = 32
    seq_len = 20
    input_dim = 50
    
    # Test CNN-LSTM-Attention
    print("Testing CNN-LSTM-Attention...")
    model = CNNLSTMAttentionModel(input_dim=input_dim)
    x = torch.randn(batch_size, seq_len, input_dim)
    output, attn = model(x)
    print(f"  Input: {x.shape}, Output: {output.shape}, Attention: {attn.shape}")
    
    # Test TabNet
    print("Testing TabNet...")
    model = TabNetModel(input_dim=input_dim)
    x = torch.randn(batch_size, input_dim)
    output, importance = model(x)
    print(f"  Input: {x.shape}, Output: {output.shape}, Importance: {importance.shape}")
    
    # Test XGBoost
    print("Testing XGBoost...")
    xgb = XGBoostPredictor()
    X = np.random.randn(100, input_dim)
    y = np.random.randn(100)
    result = xgb.train(X, y, verbose=False)
    print(f"  Best score: {result['best_score']:.6f}")
    
    print("\nAll models tested successfully!")
