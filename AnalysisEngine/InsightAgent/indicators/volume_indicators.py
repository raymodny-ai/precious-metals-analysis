# AnalysisEngine/InsightAgent/indicators/volume_indicators.py

import pandas as pd
import numpy as np

class VolumeIndicators:
    """成交量类技术指标"""
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标 (On-Balance Volume)
        
        累积成交量,反映资金流向
        """
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def mfi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        资金流量指标 (Money Flow Index)
        
        结合价格和成交量的动量指标
        范围: 0-100, >80超买, <20超卖
        """
        # 典型价格
        typical_price = (high + low + close) / 3
        
        # 资金流量
        money_flow = typical_price * volume
        
        # 正负资金流量
        positive_flow = pd.Series(0.0, index=close.index)
        negative_flow = pd.Series(0.0, index=close.index)
        
        for i in range(1, len(close)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                negative_flow.iloc[i] = money_flow.iloc[i]
        
        # 资金流量比率
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        mfr = positive_mf / negative_mf
        
        # MFI
        mfi = 100 - (100 / (1 + mfr))
        
        return mfi
    
    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        成交量加权平均价 (Volume Weighted Average Price)
        
        日内交易重要参考线
        """
        typical_price = (high + low + close) / 3
        
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        
        return vwap
    
    @staticmethod
    def cmf(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        蔡金资金流量 (Chaikin Money Flow)
        
        范围: -1到+1
        >0资金流入, <0资金流出
        """
        # 资金流量乘数
        mf_multiplier = ((close - low) - (high - close)) / (high - low)
        mf_multiplier = mf_multiplier.fillna(0)
        
        # 资金流量成交量
        mf_volume = mf_multiplier * volume
        
        # CMF
        cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
        
        return cmf
    
    @staticmethod
    def accumulation_distribution(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        累积/派发线 (Accumulation/Distribution Line)
        
        资金流向的累积指标
        """
        # 资金流量乘数
        mf_multiplier = ((close - low) - (high - close)) / (high - low)
        mf_multiplier = mf_multiplier.fillna(0)
        
        # 资金流量成交量
        mf_volume = mf_multiplier * volume
        
        # 累积
        ad_line = mf_volume.cumsum()
        
        return ad_line
