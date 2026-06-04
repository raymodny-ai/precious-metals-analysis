# AnalysisEngine/InsightAgent/indicators/precious_metals_indicators.py

import pandas as pd
import numpy as np
from typing import Dict

class PreciousMetalsIndicators:
    """贵金属特定指标"""
    
    @staticmethod
    def gold_silver_ratio(
        gold_price: pd.Series,
        silver_price: pd.Series
    ) -> pd.Series:
        """
        金银比 (Gold/Silver Ratio)
        
        历史均值约65-75
        >80: 白银相对低估
        <50: 黄金相对低估
        """
        return gold_price / silver_price
    
    @staticmethod
    def gold_correlation_with_dxy(
        gold_returns: pd.Series,
        dxy_returns: pd.Series,
        window: int = 60
    ) -> pd.Series:
        """
        黄金与美元指数的滚动相关性
        
        通常为负相关
        """
        correlation = gold_returns.rolling(window=window).corr(dxy_returns)
        return correlation
    
    @staticmethod
    def real_interest_rate_spread(
        nominal_rate: pd.Series,
        inflation_rate: pd.Series
    ) -> pd.Series:
        """
        实际利率利差
        
        实际利率下降利好黄金
        """
        real_rate = nominal_rate - inflation_rate
        return real_rate
    
    @staticmethod
    def gold_etf_holdings(holdings: pd.Series) -> Dict:
        """
        黄金ETF持仓分析
        
        Args:
            holdings: 黄金ETF持仓量 (吨)
        
        Returns:
            持仓变化统计
        """
        holdings_change = holdings.diff()
        
        return {
            'current_holdings': holdings.iloc[-1],
            'change_1d': holdings_change.iloc[-1],
            'change_5d': holdings_change.tail(5).sum(),
            'change_20d': holdings_change.tail(20).sum(),
            'trend': 'increasing' if holdings_change.tail(5).mean() > 0 else 'decreasing'
        }
    
    @staticmethod
    def cot_report_analysis(
        commercial_long: pd.Series,
        commercial_short: pd.Series,
        non_commercial_long: pd.Series,
        non_commercial_short: pd.Series
    ) -> Dict:
        """
        CFTC持仓报告分析 (Commitments of Traders)
        
        Args:
            commercial_*: 商业持仓 (对冲者)
            non_commercial_*: 投机持仓
        
        Returns:
            持仓情绪分析
        """
        # 净持仓
        commercial_net = commercial_long - commercial_short
        speculative_net = non_commercial_long - non_commercial_short
        
        # 持仓变化
        commercial_net_change = commercial_net.diff()
        speculative_net_change = speculative_net.diff()
        
        # 情绪判断
        if speculative_net.iloc[-1] > speculative_net.quantile(0.8):
            sentiment = 'extremely_bullish'
        elif speculative_net.iloc[-1] > speculative_net.quantile(0.6):
            sentiment = 'bullish'
        elif speculative_net.iloc[-1] < speculative_net.quantile(0.2):
            sentiment = 'extremely_bearish'
        elif speculative_net.iloc[-1] < speculative_net.quantile(0.4):
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        return {
            'commercial_net': commercial_net.iloc[-1],
            'speculative_net': speculative_net.iloc[-1],
            'commercial_net_change_5w': commercial_net_change.tail(5).sum(),
            'speculative_net_change_5w': speculative_net_change.tail(5).sum(),
            'sentiment': sentiment,
            'contrarian_signal': commercial_net_change.iloc[-1] > 0 and speculative_net_change.iloc[-1] < 0
        }
    
    @staticmethod
    def mining_stocks_performance(
        mining_etf_price: pd.Series,
        gold_price: pd.Series,
        window: int = 60
    ) ->pd.Series:
        """
        矿业股相对黄金表现
        
        矿业股/黄金比率上升 → 矿业股跑赢
        """
        ratio = mining_etf_price / gold_price
        
        # 标准化 (Z-score)
        mean = ratio.rolling(window=window).mean()
        std = ratio.rolling(window=window).std()
        z_score = (ratio - mean) / std
        
        return z_score
