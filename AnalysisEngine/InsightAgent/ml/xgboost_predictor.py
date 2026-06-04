# AnalysisEngine/InsightAgent/ml/xgboost_predictor.py

"""
XGBoost方向预测模型

预测价格涨跌方向(分类问题)
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import pickle

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not installed. Install with: pip install xgboost")

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


class XGBoostPredictor:
    """XGBoost方向预测器"""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        random_state: int = 42
    ):
        """
        Args:
            n_estimators: 树的数量
            max_depth: 树的最大深度
            learning_rate: 学习率
            random_state: 随机种子
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not available. Install with: pip install xgboost")
        
        self.model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        self.feature_names = None
        self.is_trained = False
    
    def create_features(self, data: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        创建特征
        
        Args:
            data: OHLCV数据
            lookback: 回望期
        
        Returns:
            特征DataFrame
        """
        features = pd.DataFrame(index=data.index)
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume'] if 'volume' in data.columns else None
        
        # 1. 价格特征
        features['returns_1d'] = close.pct_change(1)
        features['returns_5d'] = close.pct_change(5)
        features['returns_20d'] = close.pct_change(20)
        
        # 2. 移动平均
        features['sma_5'] = close.rolling(5).mean() / close - 1
        features['sma_20'] = close.rolling(20).mean() / close - 1
        features['sma_60'] = close.rolling(60).mean() / close - 1
        
        # 3. 波动率
        features['volatility_5d'] = close.pct_change().rolling(5).std()
        features['volatility_20d'] = close.pct_change().rolling(20).std()
        
        # 4. RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # 5. MACD
        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        features['macd'] = (ema_fast - ema_slow) / close
        
        # 6. 布林带位置
        bb_middle = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        features['bb_position'] = (close - (bb_middle - 2*bb_std)) / (4*bb_std)
        
        # 7. 成交量特征
        if volume is not None:
            features['volume_ratio'] = volume / volume.rolling(20).mean()
            features['volume_change'] = volume.pct_change(1)
        
        # 8. 高低价差
        features['hl_ratio'] = (high - low) / close
        
        # 9. 动量
        features['momentum_10'] = close / close.shift(10) - 1
        features['momentum_20'] = close / close.shift(20) - 1
        
        return features.dropna()
    
    def create_labels(
        self,
        data: pd.DataFrame,
        forecast_horizon: int = 1,
        threshold: float = 0.0
    ) -> pd.Series:
        """
        创建标签 (1=上涨, 0=下跌)
        
        Args:
            data: 价格数据
            forecast_horizon: 预测期限 (天数)
            threshold: 涨跌阈值 (默认0,即任何上涨都算)
        
        Returns:
            标签序列
        """
        close = data['close']
        future_returns = close.shift(-forecast_horizon) / close - 1
        labels = (future_returns > threshold).astype(int)
        return labels
    
    def train(
        self,
        data: pd.DataFrame,
        test_size: float = 0.2,
        forecast_horizon: int = 1
    ) -> Dict:
        """
        训练模型
        
        Args:
            data: OHLCV数据
            test_size: 测试集比例
            forecast_horizon: 预测期限
        
        Returns:
            训练结果
        """
        # 创建特征和标签
        features = self.create_features(data)
        labels = self.create_labels(data, forecast_horizon)
        
        # 对齐
        common_index = features.index.intersection(labels.index)
        X = features.loc[common_index]
        y = labels.loc[common_index]
        
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )
        
        # 训练
        self.model.fit(X_train, y_train)
        self.feature_names = X.columns.tolist()
        self.is_trained = True
        
        # 预测
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        # 评估
        train_accuracy = accuracy_score(y_train, y_pred_train)
        test_accuracy = accuracy_score(y_test, y_pred_test)
        
        return {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'feature_importance': self.get_feature_importance(),
            'classification_report': classification_report(y_test, y_pred_test),
            'confusion_matrix': confusion_matrix(y_test, y_pred_test).tolist(),
            'n_train_samples': len(X_train),
            'n_test_samples': len(X_test)
        }
    
    def predict(self, data: pd.DataFrame) -> int:
        """
        预测方向
        
        Returns:
            1=上涨, 0=下跌
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        features = self.create_features(data)
        X = features[self.feature_names].iloc[[-1]]  # 最新数据
        prediction = self.model.predict(X)[0]
        return int(prediction)
    
    def predict_proba(self, data: pd.DataFrame) -> float:
        """
        预测上涨概率
        
        Returns:
            上涨概率 (0-1)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        features = self.create_features(data)
        X = features[self.feature_names].iloc[[-1]]
        proba = self.model.predict_proba(X)[0][1]  # 类别1的概率
        return float(proba)
    
    def get_feature_importance(self) -> pd.Series:
        """
        获取特征重要性
        
        Returns:
            特征重要性排序
        """
        if not self.is_trained:
            return pd.Series()
        
        importance = pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)
        
        return importance
    
    def cross_validate(
        self,
        data: pd.DataFrame,
        cv: int = 5,
        forecast_horizon: int = 1
    ) -> Dict:
        """
        交叉验证
        
        Args:
            cv: 折数
        
        Returns:
            交叉验证结果
        """
        features = self.create_features(data)
        labels = self.create_labels(data, forecast_horizon)
        
        common_index = features.index.intersection(labels.index)
        X = features.loc[common_index]
        y = labels.loc[common_index]
        
        scores = cross_val_score(self.model, X, y, cv=cv, scoring='accuracy')
        
        return {
            'cv_scores': scores.tolist(),
            'cv_mean': scores.mean(),
            'cv_std': scores.std()
        }
    
    def save(self, filepath: str):
        """保存模型"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
    
    def load(self, filepath: str):
        """加载模型"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.is_trained = True
