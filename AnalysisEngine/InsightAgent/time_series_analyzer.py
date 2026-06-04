import pandas as pd
import numpy as np

class TimeSeriesAnalyzer:
    def __init__(self):
        pass
    
    def calculate_rsi(self, prices, period=14):
        """计算相对强弱指标 (RSI)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, prices, slow=26, fast=12, signal=9):
        """计算指数平滑异同移动平均线 (MACD)"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """
        计算布林带 (Bollinger Bands)
        
        Args:
            prices: 价格序列
            period: 移动平均周期 (默认20)
            std_dev: 标准差倍数 (默认2)
        
        Returns:
            upper_band, middle_band, lower_band
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    def calculate_fibonacci_levels(self, prices):
        """
        计算斐波那契回撤位
        
        基于最高点和最低点计算关键斐波那契水平:
        0%, 23.6%, 38.2%, 50%, 61.8%, 100%
        
        Returns:
            dict: 斐波那契水平字典
        """
        max_price = prices.max()
        min_price = prices.min()
        diff = max_price - min_price
        
        levels = {
            'level_0': max_price,  # 100% (顶部)
            'level_236': max_price - (diff * 0.236),
            'level_382': max_price - (diff * 0.382),
            'level_500': max_price - (diff * 0.500),
            'level_618': max_price - (diff * 0.618),
            'level_100': min_price  # 0% (底部)
        }
        
        return levels
    
    def calculate_fibonacci_extensions(self, prices):
        """
        计算斐波那契延伸位 (用于目标价位)
        
        Returns:
            dict: 斐波那契延伸水平
        """
        max_price = prices.max()
        min_price = prices.min()
        diff = max_price - min_price
        
        extensions = {
            'ext_1272': max_price + (diff * 0.272),
            'ext_1618': max_price + (diff * 0.618),
            'ext_2618': max_price + (diff * 1.618)
        }
        
        return extensions

    def analyze(self, df):
        """
        执行完整的技术分析
        
        Args:
            df: DataFrame with 'price' column
        
        Returns:
            df: DataFrame with all technical indicators
        """
        if 'price' not in df.columns:
            return df
        
        # 移动平均
        df['SMA_20'] = df['price'].rolling(window=20).mean()
        df['SMA_50'] = df['price'].rolling(window=50).mean()
        df['EMA_12'] = df['price'].ewm(span=12, adjust=False).mean()
        
        # RSI
        df['RSI'] = self.calculate_rsi(df['price'])
        
        # MACD
        df['MACD'], df['Signal'] = self.calculate_macd(df['price'])
        df['MACD_Histogram'] = df['MACD'] - df['Signal']
        
        # 布林带
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self.calculate_bollinger_bands(df['price'])
        df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
        df['BB_Position'] = (df['price'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # 斐波那契水平 (存储为元数据，不是每行数据)
        fib_levels = self.calculate_fibonacci_levels(df['price'])
        df.attrs['fibonacci_levels'] = fib_levels
        
        fib_extensions = self.calculate_fibonacci_extensions(df['price'])
        df.attrs['fibonacci_extensions'] = fib_extensions
        
        return df
    
    def get_trading_signals(self, df):
        """
        生成交易信号
        
        Returns:
            dict: 包含各种交易信号
        """
        if df.empty or 'price' not in df.columns:
            return {}
        
        latest = df.iloc[-1]
        signals = {}
        
        # RSI 信号
        if 'RSI' in df.columns and not pd.isna(latest['RSI']):
            if latest['RSI'] > 70:
                signals['rsi_signal'] = 'OVERBOUGHT'
            elif latest['RSI'] < 30:
                signals['rsi_signal'] = 'OVERSOLD'
            else:
                signals['rsi_signal'] = 'NEUTRAL'
        
        # MACD 信号
        if 'MACD' in df.columns and 'Signal' in df.columns:
            if latest['MACD'] > latest['Signal']:
                signals['macd_signal'] = 'BULLISH'
            else:
                signals['macd_signal'] = 'BEARISH'
        
        # 布林带信号
        if 'BB_Position' in df.columns and not pd.isna(latest['BB_Position']):
            if latest['BB_Position'] > 1:
                signals['bollinger_signal'] = 'ABOVE_UPPER_BAND'
            elif latest['BB_Position'] < 0:
                signals['bollinger_signal'] = 'BELOW_LOWER_BAND'
            elif latest['BB_Position'] > 0.8:
                signals['bollinger_signal'] = 'NEAR_UPPER_BAND'
            elif latest['BB_Position'] < 0.2:
                signals['bollinger_signal'] = 'NEAR_LOWER_BAND'
            else:
                signals['bollinger_signal'] = 'MIDDLE_RANGE'
        
        # 斐波那契水平
        if hasattr(df, 'attrs') and 'fibonacci_levels' in df.attrs:
            fib = df.attrs['fibonacci_levels']
            current_price = latest['price']
            
            # 找到最近的斐波那契水平
            closest_level = min(fib.items(), key=lambda x: abs(x[1] - current_price))
            signals['nearest_fibonacci'] = {
                'level': closest_level[0],
                'price': closest_level[1],
                'distance': abs(closest_level[1] - current_price)
            }
        
        return signals
