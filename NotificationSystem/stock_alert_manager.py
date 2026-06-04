"""
股票预警管理器
监控股票价格、相关性、新闻等并触发预警
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from DataCollector.StockDataCollector.yfinance_client import YFinanceStockClient
from .notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class StockAlertRule:
    """股票预警规则基类"""
    
    def __init__(self, rule_id: str, symbol: str, enabled: bool = True):
        self.rule_id = rule_id
        self.symbol = symbol
        self.enabled = enabled
        self.last_triggered = None
        self.cooldown_minutes = 60  # 冷却时间，避免频繁预警
    
    def can_trigger(self) -> bool:
        """检查是否可以触发（考虑冷却时间）"""
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        elapsed = datetime.now() - self.last_triggered
        return elapsed.total_seconds() / 60 >= self.cooldown_minutes
    
    def check(self, data: Dict) -> Optional[Dict]:
        """检查规则，返回预警信息（如果需要预警）"""
        raise NotImplementedError

class PriceBreakoutRule(StockAlertRule):
    """价格突破预警规则"""
    
    def __init__(self, rule_id: str, symbol: str, 
                 breakout_price: float, direction: str = 'above',
                 enabled: bool = True):
        super().__init__(rule_id, symbol, enabled)
        self.breakout_price = breakout_price
        self.direction = direction  # 'above' or 'below'
    
    def check(self, data: Dict) -> Optional[Dict]:
        if not self.can_trigger():
            return None
        
        current_price = data.get('price')
        if current_price is None:
            return None
        
        triggered = False
        if self.direction == 'above' and current_price >= self.breakout_price:
            triggered = True
        elif self.direction == 'below' and current_price <= self.breakout_price:
            triggered = True
        
        if triggered:
            self.last_triggered = datetime.now()
            return {
                'rule_id': self.rule_id,
                'alert_type': 'PRICE_BREAKOUT',
                'symbol': self.symbol,
                'message': f"{self.symbol} 价格{'突破' if self.direction == 'above' else '跌破'} ${self.breakout_price:.2f}",
                'current_price': current_price,
                'trigger_price': self.breakout_price,
                'direction': self.direction,
                'severity': 'MEDIUM',
                'timestamp': datetime.now().isoformat()
            }
        
        return None

class PercentChangeRule(StockAlertRule):
    """涨跌幅预警规则"""
    
    def __init__(self, rule_id: str, symbol: str,
                 threshold_percent: float, direction: str = 'both',
                 enabled: bool = True):
        super().__init__(rule_id, symbol, enabled)
        self.threshold_percent = abs(threshold_percent)
        self.direction = direction  # 'up', 'down', 'both'
    
    def check(self, data: Dict) -> Optional[Dict]:
        if not self.can_trigger():
            return None
        
        change_percent = data.get('change_percent')
        if change_percent is None:
            return None
        
        triggered = False
        if self.direction == 'up' and change_percent >= self.threshold_percent:
            triggered = True
        elif self.direction == 'down' and change_percent <= -self.threshold_percent:
            triggered = True
        elif self.direction == 'both' and abs(change_percent) >= self.threshold_percent:
            triggered = True
        
        if triggered:
            self.last_triggered = datetime.now()
            severity = 'HIGH' if abs(change_percent) >= self.threshold_percent * 1.5 else 'MEDIUM'
            
            return {
                'rule_id': self.rule_id,
                'alert_type': 'PERCENT_CHANGE',
                'symbol': self.symbol,
                'message': f"{self.symbol} {'涨幅' if change_percent > 0 else '跌幅'} {abs(change_percent):.2f}%",
                'change_percent': change_percent,
                'threshold': self.threshold_percent,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
        
        return None

class CorrelationDivergenceRule(StockAlertRule):
    """相关性背离预警规则"""
    
    def __init__(self, rule_id: str, symbol: str,
                 min_correlation: float = 0.7,
                 divergence_threshold: float = 5.0,
                 enabled: bool = True):
        super().__init__(rule_id, symbol, enabled)
        self.min_correlation = min_correlation
        self.divergence_threshold = divergence_threshold
        self.cooldown_minutes = 180  # 背离预警冷却时间更长
    
    def check(self, data: Dict) -> Optional[Dict]:
        if not self.can_trigger():
            return None
        
        correlation = data.get('gold_correlation')
        stock_change = data.get('change_percent', 0)
        gold_change = data.get('gold_change_percent', 0)
        
        if correlation is None or correlation < self.min_correlation:
            return None
        
        # 检查是否背离（相关性高但走势相反）
        divergence = abs(stock_change - gold_change)
        
        if divergence >= self.divergence_threshold:
            # 相关性高但走势明显背离
            if (stock_change > 0 and gold_change < 0) or (stock_change < 0 and gold_change > 0):
                self.last_triggered = datetime.now()
                
                return {
                    'rule_id': self.rule_id,
                    'alert_type': 'CORRELATION_DIVERGENCE',
                    'symbol': self.symbol,
                    'message': f"{self.symbol} 与金价走势背离",
                    'stock_change': stock_change,
                    'gold_change': gold_change,
                    'correlation': correlation,
                    'divergence': divergence,
                    'severity': 'MEDIUM',
                    'timestamp': datetime.now().isoformat()
                }
        
        return None

class RSIAlertRule(StockAlertRule):
    """RSI超买超卖预警规则"""
    
    def __init__(self, rule_id: str, symbol: str,
                 oversold_threshold: float = 30,
                 overbought_threshold: float = 70,
                 enabled: bool = True):
        super().__init__(rule_id, symbol, enabled)
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
    
    def check(self, data: Dict) -> Optional[Dict]:
        if not self.can_trigger():
            return None
        
        rsi = data.get('rsi')
        if rsi is None:
            return None
        
        if rsi <= self.oversold_threshold:
            self.last_triggered = datetime.now()
            return {
                'rule_id': self.rule_id,
                'alert_type': 'RSI_OVERSOLD',
                'symbol': self.symbol,
                'message': f"{self.symbol} RSI={rsi:.1f} 进入超卖区",
                'rsi': rsi,
                'threshold': self.oversold_threshold,
                'severity': 'MEDIUM',
                'timestamp': datetime.now().isoformat()
            }
        
        elif rsi >= self.overbought_threshold:
            self.last_triggered = datetime.now()
            return {
                'rule_id': self.rule_id,
                'alert_type': 'RSI_OVERBOUGHT',
                'symbol': self.symbol,
                'message': f"{self.symbol} RSI={rsi:.1f} 进入超买区",
                'rsi': rsi,
                'threshold': self.overbought_threshold,
                'severity': 'MEDIUM',
                'timestamp': datetime.now().isoformat()
            }
        
        return None

class StockAlertManager:
    """股票预警管理器"""
    
    def __init__(self, notification_manager: Optional[NotificationManager] = None):
        self.stock_client = YFinanceStockClient()
        self.notification_manager = notification_manager or NotificationManager()
        self.rules: List[StockAlertRule] = []
        self.alert_history: List[Dict] = []
    
    def add_rule(self, rule: StockAlertRule):
        """添加预警规则"""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.rule_id} for {rule.symbol}")
    
    def remove_rule(self, rule_id: str):
        """移除预警规则"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Removed alert rule: {rule_id}")
    
    def check_all_rules(self) -> List[Dict]:
        """检查所有规则"""
        alerts = []
        
        # 获取所有监控股票的数据
        symbols = list(set(rule.symbol for rule in self.rules if rule.enabled))
        
        for symbol in symbols:
            try:
                # 获取当前数据
                quote = self.stock_client.get_current_price(symbol)
                
                if not quote:
                    continue
                
                # 获取金价变化（用于相关性分析）
                gold_quote = self.stock_client.get_current_price('GLD')
                if gold_quote:
                    quote['gold_change_percent'] = gold_quote['change_percent']
                
                # 获取相关性
                correlation = self.stock_client.calculate_correlation_with_gold(symbol)
                if correlation is not None:
                    quote['gold_correlation'] = correlation
                
                # 检查所有规则
                for rule in self.rules:
                    if rule.symbol == symbol and rule.enabled:
                        alert = rule.check(quote)
                        if alert:
                            alerts.append(alert)
                            self.alert_history.append(alert)
                            
                            # 发送通知
                            self._send_alert_notification(alert)
            
            except Exception as e:
                logger.error(f"Error checking alerts for {symbol}: {e}")
        
        return alerts
    
    def _send_alert_notification(self, alert: Dict):
        """发送预警通知"""
        try:
            subject = f"[股票预警] {alert['symbol']} - {alert['alert_type']}"
            
            message = f"""
股票预警通知

股票代码: {alert['symbol']}
预警类型: {alert['alert_type']}
严重程度: {alert['severity']}

{alert['message']}

触发时间: {alert['timestamp']}

详细信息:
{json.dumps(alert, indent=2, ensure_ascii=False)}
"""
            
            recipients = ['alert@example.com']  # 可以从配置读取
            
            self.notification_manager.send_notification(
                subject=subject,
                message=message,
                recipients=recipients,
                channels=['email']
            )
            
            logger.info(f"Sent alert notification for {alert['symbol']}")
        
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def get_alert_history(self, symbol: Optional[str] = None, 
                          hours: int = 24) -> List[Dict]:
        """获取预警历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered = []
        for alert in self.alert_history:
            alert_time = datetime.fromisoformat(alert['timestamp'])
            
            if alert_time >= cutoff_time:
                if symbol is None or alert['symbol'] == symbol:
                    filtered.append(alert)
        
        return filtered
    
    def get_active_alerts(self) -> List[Dict]:
        """获取最近1小时的活跃预警"""
        return self.get_alert_history(hours=1)
    
    def save_rules_to_file(self, filename: str = 'config/stock_alert_rules.json'):
        """保存规则到文件"""
        rules_data = []
        
        for rule in self.rules:
            rule_dict = {
                'rule_id': rule.rule_id,
                'symbol': rule.symbol,
                'enabled': rule.enabled,
                'type': rule.__class__.__name__
            }
            
            # 添加特定规则的参数
            if isinstance(rule, PriceBreakoutRule):
                rule_dict.update({
                    'breakout_price': rule.breakout_price,
                    'direction': rule.direction
                })
            elif isinstance(rule, PercentChangeRule):
                rule_dict.update({
                    'threshold_percent': rule.threshold_percent,
                    'direction': rule.direction
                })
            elif isinstance(rule, CorrelationDivergenceRule):
                rule_dict.update({
                    'min_correlation': rule.min_correlation,
                    'divergence_threshold': rule.divergence_threshold
                })
            elif isinstance(rule, RSIAlertRule):
                rule_dict.update({
                    'oversold_threshold': rule.oversold_threshold,
                    'overbought_threshold': rule.overbought_threshold
                })
            
            rules_data.append(rule_dict)
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(rules_data)} rules to {filename}")

# 使用示例
def demo():
    """演示预警系统"""
    manager = StockAlertManager()
    
    # 添加各种预警规则
    manager.add_rule(PriceBreakoutRule('gld_200', 'GLD', breakout_price=200, direction='above'))
    manager.add_rule(PercentChangeRule('nem_5pct', 'NEM', threshold_percent=5, direction='both'))
    manager.add_rule(CorrelationDivergenceRule('gold_diverge', 'GOLD', min_correlation=0.7))
    manager.add_rule(RSIAlertRule('slv_rsi', 'SLV'))
    
    # 检查所有规则
    alerts = manager.check_all_rules()
    
    print(f"\n触发了 {len(alerts)} 个预警:")
    for alert in alerts:
        print(f"  - {alert['symbol']}: {alert['message']}")
    
    # 保存规则
    manager.save_rules_to_file()

if __name__ == '__main__':
    demo()
