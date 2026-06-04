# AnalysisEngine/InsightAgent/ml/__init__.py

"""
机器学习预测模块

包含:
- xgboost_predictor: XGBoost方向预测
- feature_engineering: 特征工程
"""

from .xgboost_predictor import XGBoostPredictor

__all__ = ['XGBoostPredictor']
