"""
LSTM Price Predictor
LSTM价格预测模块
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

from ..utils.logger import setup_logging
from ..utils.config import get_settings, MODELS_DIR

logger = setup_logging("lstm_predictor")
settings = get_settings()


@dataclass
class PredictionResult:
    """Prediction result container"""
    symbol: str
    current_price: float
    predicted_price: float
    predicted_return: float
    direction: str  # 'up', 'down', 'neutral'
    confidence: float
    horizon: int
    generated_at: datetime


class LSTMModel(nn.Module):
    """
    LSTM model for price prediction
    
    Architecture:
    - Input layer
    - LSTM layers (with dropout)
    - Attention layer (optional)
    - Dense output layer
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 1,
        dropout: float = 0.2,
        bidirectional: bool = False
    ):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        # Attention layer
        lstm_output_dim = hidden_dim * 2 if bidirectional else hidden_dim
        self.attention = nn.Sequential(
            nn.Linear(lstm_output_dim, lstm_output_dim // 2),
            nn.Tanh(),
            nn.Linear(lstm_output_dim // 2, 1),
            nn.Softmax(dim=1)
        )
        
        # Output layers
        self.fc = nn.Sequential(
            nn.Linear(lstm_output_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_dim)
        
        Returns:
            output: Predictions of shape (batch, output_dim)
            attention_weights: Attention weights of shape (batch, seq_len, 1)
        """
        # LSTM forward
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Attention
        attention_weights = self.attention(lstm_out)
        context = torch.sum(attention_weights * lstm_out, dim=1)
        
        # Output
        output = self.fc(context)
        
        return output, attention_weights


class LSTMPredictor:
    """
    LSTM-based price predictor
    
    Features:
    - Multiple prediction horizons (T+1, T+5, T+30)
    - Attention mechanism for interpretability
    - Uncertainty estimation
    - Model persistence
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        sequence_length: int = 20,
        device: Optional[str] = None
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        
        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(f"Initializing LSTM predictor on {self.device}")
        
        # Initialize model
        self.model = LSTMModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers
        ).to(self.device)
        
        # Training state
        self.is_trained = False
        self.training_history = []
        self.feature_names = []
        
        # Normalization parameters
        self.feature_mean = None
        self.feature_std = None
        self.target_mean = None
        self.target_std = None
    
    def prepare_sequences(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Prepare sequential data for LSTM
        
        Args:
            X: Feature array of shape (n_samples, n_features)
            y: Target array of shape (n_samples,)
        
        Returns:
            X_seq: Sequential features of shape (n_samples - seq_len, seq_len, n_features)
            y_seq: Targets aligned with sequences
        """
        n_samples = len(X)
        seq_len = self.sequence_length
        
        if n_samples <= seq_len:
            raise ValueError(f"Not enough samples ({n_samples}) for sequence length ({seq_len})")
        
        # Create sequences
        X_seq = []
        for i in range(seq_len, n_samples):
            X_seq.append(X[i - seq_len:i])
        
        X_seq = np.array(X_seq)
        
        if y is not None:
            y_seq = y[seq_len:]
            return X_seq, y_seq
        
        return X_seq, None
    
    def normalize_features(
        self,
        X: np.ndarray,
        fit: bool = False
    ) -> np.ndarray:
        """Normalize features using z-score"""
        if fit:
            self.feature_mean = np.mean(X, axis=0)
            self.feature_std = np.std(X, axis=0) + 1e-8
        
        return (X - self.feature_mean) / self.feature_std
    
    def normalize_target(
        self,
        y: np.ndarray,
        fit: bool = False
    ) -> np.ndarray:
        """Normalize target"""
        if fit:
            self.target_mean = np.mean(y)
            self.target_std = np.std(y) + 1e-8
        
        return (y - self.target_mean) / self.target_std
    
    def denormalize_target(self, y: np.ndarray) -> np.ndarray:
        """Denormalize target"""
        return y * self.target_std + self.target_mean
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        early_stopping_patience: int = 10,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """
        Train the LSTM model
        
        Args:
            X: Feature array
            y: Target array
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            validation_split: Fraction for validation
            early_stopping_patience: Early stopping patience
            verbose: Print training progress
        
        Returns:
            Training history dictionary
        """
        logger.info(f"Training LSTM with {len(X)} samples...")
        
        # Normalize
        X_norm = self.normalize_features(X, fit=True)
        y_norm = self.normalize_target(y, fit=True)
        
        # Prepare sequences
        X_seq, y_seq = self.prepare_sequences(X_norm, y_norm)
        
        # Split train/validation
        n_samples = len(X_seq)
        n_val = int(n_samples * validation_split)
        n_train = n_samples - n_val
        
        X_train, X_val = X_seq[:n_train], X_seq[n_train:]
        y_train, y_val = y_seq[:n_train], y_seq[n_train:]
        
        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).unsqueeze(-1).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_val_t = torch.FloatTensor(y_val).unsqueeze(-1).to(self.device)
        
        # Create data loader
        train_dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t)
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True
        )
        
        # Optimizer and loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        history = {"train_loss": [], "val_loss": []}
        best_val_loss = float("inf")
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_losses = []
            
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                predictions, _ = self.model(X_batch)
                loss = criterion(predictions, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                train_losses.append(loss.item())
            
            avg_train_loss = np.mean(train_losses)
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_predictions, _ = self.model(X_val_t)
                val_loss = criterion(val_predictions, y_val_t).item()
            
            history["train_loss"].append(avg_train_loss)
            history["val_loss"].append(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                self.best_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
            
            if verbose and epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: train_loss={avg_train_loss:.6f}, val_loss={val_loss:.6f}")
            
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break
        
        # Restore best model
        if hasattr(self, "best_state"):
            self.model.load_state_dict(self.best_state)
        
        self.is_trained = True
        self.training_history = history
        
        logger.info(f"Training complete. Best val_loss: {best_val_loss:.6f}")
        
        return history
    
    def predict(
        self,
        X: np.ndarray,
        return_attention: bool = False
    ) -> np.ndarray:
        """
        Make predictions
        
        Args:
            X: Feature array
            return_attention: Whether to return attention weights
        
        Returns:
            Predictions (denormalized)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Normalize
        X_norm = self.normalize_features(X, fit=False)
        
        # Prepare sequences
        X_seq, _ = self.prepare_sequences(X_norm)
        
        # Convert to tensor
        X_t = torch.FloatTensor(X_seq).to(self.device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            predictions, attention = self.model(X_t)
        
        # Denormalize
        predictions = predictions.cpu().numpy().flatten()
        predictions = self.denormalize_target(predictions)
        
        if return_attention:
            return predictions, attention.cpu().numpy()
        
        return predictions
    
    def predict_with_uncertainty(
        self,
        X: np.ndarray,
        n_samples: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict with uncertainty estimation using MC Dropout
        
        Returns:
            mean_predictions, std_predictions
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Enable dropout for MC sampling
        def enable_dropout(model):
            for m in model.modules():
                if isinstance(m, nn.Dropout):
                    m.train()
        
        # Normalize and prepare sequences
        X_norm = self.normalize_features(X, fit=False)
        X_seq, _ = self.prepare_sequences(X_norm)
        X_t = torch.FloatTensor(X_seq).to(self.device)
        
        # MC sampling
        predictions = []
        enable_dropout(self.model)
        
        with torch.no_grad():
            for _ in range(n_samples):
                pred, _ = self.model(X_t)
                predictions.append(pred.cpu().numpy())
        
        predictions = np.array(predictions)
        
        # Calculate mean and std
        mean_pred = np.mean(predictions, axis=0).flatten()
        std_pred = np.std(predictions, axis=0).flatten()
        
        # Denormalize
        mean_pred = self.denormalize_target(mean_pred)
        std_pred = std_pred * self.target_std
        
        return mean_pred, std_pred
    
    def get_prediction_result(
        self,
        X: np.ndarray,
        current_price: float,
        symbol: str,
        horizon: int = 1
    ) -> PredictionResult:
        """
        Get structured prediction result
        """
        # Predict with uncertainty
        mean_pred, std_pred = self.predict_with_uncertainty(X)
        
        # Get last prediction
        predicted_return = mean_pred[-1]
        uncertainty = std_pred[-1]
        
        # Calculate predicted price
        predicted_price = current_price * (1 + predicted_return)
        
        # Determine direction
        if predicted_return > 0.005:
            direction = "up"
        elif predicted_return < -0.005:
            direction = "down"
        else:
            direction = "neutral"
        
        # Calculate confidence (inverse of uncertainty)
        confidence = max(0, min(1, 1 - uncertainty * 10))
        
        return PredictionResult(
            symbol=symbol,
            current_price=current_price,
            predicted_price=predicted_price,
            predicted_return=predicted_return,
            direction=direction,
            confidence=confidence,
            horizon=horizon,
            generated_at=datetime.now()
        )
    
    def save(self, filepath: Optional[str] = None):
        """Save model and parameters"""
        if filepath is None:
            filepath = MODELS_DIR / f"lstm_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        
        save_dict = {
            "model_state": self.model.state_dict(),
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "sequence_length": self.sequence_length,
            "feature_mean": self.feature_mean,
            "feature_std": self.feature_std,
            "target_mean": self.target_mean,
            "target_std": self.target_std,
            "training_history": self.training_history,
            "feature_names": self.feature_names
        }
        
        torch.save(save_dict, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model and parameters"""
        save_dict = torch.load(filepath, map_location=self.device)
        
        # Recreate model if dimensions differ
        if save_dict["input_dim"] != self.input_dim:
            self.input_dim = save_dict["input_dim"]
            self.model = LSTMModel(
                input_dim=self.input_dim,
                hidden_dim=save_dict["hidden_dim"],
                num_layers=save_dict["num_layers"]
            ).to(self.device)
        
        self.model.load_state_dict(save_dict["model_state"])
        self.sequence_length = save_dict["sequence_length"]
        self.feature_mean = save_dict["feature_mean"]
        self.feature_std = save_dict["feature_std"]
        self.target_mean = save_dict["target_mean"]
        self.target_std = save_dict["target_std"]
        self.training_history = save_dict.get("training_history", [])
        self.feature_names = save_dict.get("feature_names", [])
        self.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")


if __name__ == "__main__":
    # Test the predictor
    import yfinance as yf
    
    # Get sample data
    ticker = yf.Ticker("GLD")
    df = ticker.history(period="2y")
    
    # Simple features
    df["returns"] = df["Close"].pct_change()
    df["ma_5"] = df["Close"].rolling(5).mean()
    df["ma_20"] = df["Close"].rolling(20).mean()
    df["volatility"] = df["returns"].rolling(20).std()
    df = df.dropna()
    
    # Prepare data
    feature_cols = ["returns", "ma_5", "ma_20", "volatility"]
    X = df[feature_cols].values
    y = df["returns"].shift(-1).values[:-1]
    X = X[:-1]
    
    print(f"Data shape: X={X.shape}, y={y.shape}")
    
    # Train model
    predictor = LSTMPredictor(input_dim=len(feature_cols), sequence_length=20)
    history = predictor.train(X, y, epochs=50, verbose=True)
    
    # Predict
    predictions = predictor.predict(X[-50:])
    print(f"\nPredictions shape: {predictions.shape}")
    print(f"Last 5 predictions: {predictions[-5:]}")
    
    # Get prediction result
    result = predictor.get_prediction_result(
        X[-50:],
        current_price=df["Close"].iloc[-1],
        symbol="GLD"
    )
    print(f"\nPrediction result: {result}")
