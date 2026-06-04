"""
风险管理框架

包含:
- var_calculator: VaR/CVaR计算
- stress_tester: 压力测试
"""

from .var_calculator import VaRCalculator, VaRResult
from .stress_tester import StressTester, StressScenario

__all__ = ['VaRCalculator', 'VaRResult', 'StressTester', 'StressScenario']
