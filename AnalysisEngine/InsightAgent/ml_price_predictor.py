"""
机器学习价格预测模型
使用 LSTM 神经网络预测贵金属价格
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class PricePredictionModel:
    """
    基于 LSTM 的价格预测模型
    
    注意: 需要安装 tensorflow/keras
    pip install tensorflow
    """
    
    def __init__(self, lookback_days=60):
        self.lookback_days = lookback_days
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.is_trained = False
        
        # 延迟导入 keras (如果未安装也能运行其他功能)
        try:
            from tensorflow import keras
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            self.keras = keras
            self.Sequential = Sequential
            self.LSTM = LSTM
            self.Dense = Dense
            self.Dropout = Dropout
        except ImportError:
            print("警告: TensorFlow 未安装，ML 预测功能不可用")
            print("安装: pip install tensorflow")
            self.keras = None
    
    def prepare_data(self, prices):
        """
        准备训练数据
        
        Args:
            prices: 价格序列 (pandas Series 或 numpy array)
        
        Returns:
            X, y: 训练特征和标签
        """
        if isinstance(prices, pd.Series):
            prices = prices.values
        
        # 归一化
        scaled_data = self.scaler.fit_transform(prices.reshape(-1, 1))
        
        X, y = [], []
        for i in range(self.lookback_days, len(scaled_data)):
            X.append(scaled_data[i-self.lookback_days:i, 0])
            y.append(scaled_data[i, 0])
        
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape):
        """构建 LSTM 模型"""
        if self.keras is None:
            raise ImportError("TensorFlow 未安装")
        
        model = self.Sequential([
            self.LSTM(50, return_sequences=True, input_shape=input_shape),
            self.Dropout(0.2),
            self.LSTM(50, return_sequences=False),
            self.Dropout(0.2),
            self.Dense(25),
            self.Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model
    
    def train(self, prices, epochs=50, batch_size=32, validation_split=0.2):
        """
        训练模型
        
        Args:
            prices: 历史价格数据
            epochs: 训练轮数
            batch_size: 批次大小
            validation_split: 验证集比例
        """
        if self.keras is None:
            print("错误: TensorFlow 未安装，无法训练模型")
            return
        
        X, y = self.prepare_data(prices)
        
        # Reshape for LSTM [samples, time steps, features]
        X = X.reshape(X.shape[0], X.shape[1], 1)
        
        # 构建模型
        self.model = self.build_model((X.shape[1], 1))
        
        # 训练
        print(f"开始训练模型... (样本数: {len(X)})")
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1
        )
        
        self.is_trained = True
        print("模型训练完成!")
        
        return history
    
    def predict(self, recent_prices, days_ahead=7):
        """
        预测未来价格
        
        Args:
            recent_prices: 最近的价格数据 (至少 lookback_days 个数据点)
            days_ahead: 预测未来多少天
        
        Returns:
            predictions: 预测价格数组
        """
        if not self.is_trained or self.model is None:
            print("错误: 模型未训练")
            return None
        
        if len(recent_prices) < self.lookback_days:
            print(f"错误: 需要至少 {self.lookback_days} 个历史数据点")
            return None
        
        # 准备输入数据
        if isinstance(recent_prices, pd.Series):
            recent_prices = recent_prices.values
        
        scaled_data = self.scaler.transform(recent_prices.reshape(-1, 1))
        
        predictions = []
        current_batch = scaled_data[-self.lookback_days:].reshape(1, self.lookback_days, 1)
        
        for _ in range(days_ahead):
            # 预测下一个值
            next_pred = self.model.predict(current_batch, verbose=0)
            predictions.append(next_pred[0, 0])
            
            # 更新批次（滚动窗口）
            current_batch = np.append(current_batch[:, 1:, :], [[next_pred]], axis=1)
        
        # 反归一化
        predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        
        return predictions.flatten()
    
    def save_model(self, filepath='models/price_prediction_model.h5'):
        """保存训练好的模型"""
        if self.model is None:
            print("错误: 没有可保存的模型")
            return
        
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.model.save(filepath)
        print(f"模型已保存到: {filepath}")
    
    def load_model(self, filepath='models/price_prediction_model.h5'):
        """加载已训练的模型"""
        if self.keras is None:
            print("错误: TensorFlow 未安装")
            return
        
        from tensorflow.keras.models import load_model
        self.model = load_model(filepath)
        self.is_trained = True
        print(f"模型已从 {filepath} 加载")

class SimpleMovingAveragePredictor:
    """
    简单移动平均预测器 (不需要 TensorFlow)
    作为 LSTM 的轻量级替代方案
    """
    
    def __init__(self, window=30):
        self.window = window
    
    def predict(self, prices, days_ahead=7):
        """
        基于移动平均的简单预测
        
        Args:
            prices: 历史价格
            days_ahead: 预测天数
        
        Returns:
            predictions: 预测价格
        """
        if len(prices) < self.window:
            return None
        
        # 计算最近的移动平均
        ma = prices[-self.window:].mean()
        
        # 计算趋势 (线性回归斜率)
        x = np.arange(self.window)
        y = prices[-self.window:].values if isinstance(prices, pd.Series) else prices[-self.window:]
        slope = np.polyfit(x, y, 1)[0]
        
        # 预测
        predictions = []
        for i in range(1, days_ahead + 1):
            pred = ma + (slope * i)
            predictions.append(pred)
        
        return np.array(predictions)

def demo_prediction():
    """演示价格预测功能"""
    print("="*60)
    print("价格预测模型演示")
    print("="*60)
    
    # 生成示例数据
    np.random.seed(42)
    days = 200
    trend = np.linspace(2000, 2100, days)
    noise = np.random.normal(0, 20, days)
    prices = pd.Series(trend + noise)
    
    print(f"\n生成了 {days} 天的示例价格数据")
    print(f"价格范围: ${prices.min():.2f} - ${prices.max():.2f}")
    
    # 尝试 LSTM 预测
    print("\n--- LSTM 预测 ---")
    lstm_model = PricePredictionModel(lookback_days=30)
    
    if lstm_model.keras is not None:
        print("训练 LSTM 模型...")
        lstm_model.train(prices, epochs=10, batch_size=16)
        
        predictions = lstm_model.predict(prices, days_ahead=7)
        print(f"\n未来 7 天价格预测:")
        for i, pred in enumerate(predictions, 1):
            print(f"  第 {i} 天: ${pred:.2f}")
    else:
        print("TensorFlow 未安装，跳过 LSTM 预测")
    
    # 简单移动平均预测
    print("\n--- 移动平均预测 ---")
    simple_model = SimpleMovingAveragePredictor(window=30)
    predictions = simple_model.predict(prices, days_ahead=7)
    
    print(f"\n未来 7 天价格预测 (移动平均):")
    for i, pred in enumerate(predictions, 1):
        print(f"  第 {i} 天: ${pred:.2f}")

if __name__ == '__main__':
    demo_prediction()
