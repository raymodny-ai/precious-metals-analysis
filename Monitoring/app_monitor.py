"""
应用监控模块
实现健康检查、性能指标收集和告警
"""
import os
import time
import psutil
import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class ApplicationMonitor:
    """应用性能监控器"""
    
    def __init__(self, alert_threshold=None):
        self.start_time = time.time()
        self.metrics_history = {
            'cpu': deque(maxlen=100),
            'memory': deque(maxlen=100),
            'api_response_time': deque(maxlen=100),
            'error_count': 0
        }
        
        # 告警阈值
        self.alert_threshold = alert_threshold or {
            'cpu_percent': 80,
            'memory_percent': 80,
            'api_response_time': 5.0,  # 秒
            'error_rate': 0.05  # 5%
        }
    
    def collect_system_metrics(self):
        """收集系统指标"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict()
        }
        
        # 存储历史数据
        self.metrics_history['cpu'].append(metrics['cpu_percent'])
        self.metrics_history['memory'].append(metrics['memory_percent'])
        
        return metrics
    
    def check_health(self):
        """
        健康检查
        
        Returns:
            dict: 健康状态和详细信息
        """
        metrics = self.collect_system_metrics()
        
        health_status = {
            'status': 'healthy',
            'timestamp': metrics['timestamp'],
            'uptime': time.time() - self.start_time,
            'checks': {}
        }
        
        # CPU 检查
        if metrics['cpu_percent'] > self.alert_threshold['cpu_percent']:
            health_status['status'] = 'unhealthy'
            health_status['checks']['cpu'] = {
                'status': 'critical',
                'value': metrics['cpu_percent'],
                'threshold': self.alert_threshold['cpu_percent']
            }
        else:
            health_status['checks']['cpu'] = {
                'status': 'ok',
                'value': metrics['cpu_percent']
            }
        
        # 内存检查
        if metrics['memory_percent'] > self.alert_threshold['memory_percent']:
            health_status['status'] = 'unhealthy'
            health_status['checks']['memory'] = {
                'status': 'critical',
                'value': metrics['memory_percent'],
                'threshold': self.alert_threshold['memory_percent']
            }
        else:
            health_status['checks']['memory'] = {
                'status': 'ok',
                'value': metrics['memory_percent']
            }
        
        # 磁盘检查
        health_status['checks']['disk'] = {
            'status': 'ok' if metrics['disk_usage'] < 90 else 'warning',
            'value': metrics['disk_usage']
        }
        
        return health_status
    
    def record_api_call(self, endpoint, response_time, success=True):
        """
        记录 API 调用
        
        Args:
            endpoint: API 端点
            response_time: 响应时间（秒）
            success: 是否成功
        """
        self.metrics_history['api_response_time'].append(response_time)
        
        if not success:
            self.metrics_history['error_count'] += 1
        
        # 检查是否需要告警
        if response_time > self.alert_threshold['api_response_time']:
            logger.warning(f"API {endpoint} 响应时间过长: {response_time:.2f}s")
    
    def get_metrics_summary(self):
        """获取指标摘要"""
        summary = {
            'uptime_seconds': time.time() - self.start_time,
            'cpu': {
                'current': self.metrics_history['cpu'][-1] if self.metrics_history['cpu'] else 0,
                'average': sum(self.metrics_history['cpu']) / len(self.metrics_history['cpu']) if self.metrics_history['cpu'] else 0
            },
            'memory': {
                'current': self.metrics_history['memory'][-1] if self.metrics_history['memory'] else 0,
                'average': sum(self.metrics_history['memory']) / len(self.metrics_history['memory']) if self.metrics_history['memory'] else 0
            },
            'api': {
                'total_errors': self.metrics_history['error_count'],
                'avg_response_time': sum(self.metrics_history['api_response_time']) / len(self.metrics_history['api_response_time']) if self.metrics_history['api_response_time'] else 0
            }
        }
        
        return summary

class AlertManager:
    """告警管理器"""
    
    def __init__(self, notification_manager=None):
        self.notification_manager = notification_manager
        self.alert_history = deque(maxlen=100)
        self.alert_cooldown = {}  # 防止告警轰炸
        self.cooldown_period = 300  # 5分钟冷却期
    
    def send_alert(self, alert_type, message, severity='warning'):
        """
        发送告警
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            severity: 严重程度 (info, warning, critical)
        """
        now = time.time()
        
        # 检查冷却期
        if alert_type in self.alert_cooldown:
            if now - self.alert_cooldown[alert_type] < self.cooldown_period:
                logger.debug(f"告警 {alert_type} 在冷却期内，跳过")
                return
        
        # 记录告警
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        self.alert_history.append(alert)
        
        # 记录日志
        log_func = logger.info if severity == 'info' else logger.warning if severity == 'warning' else logger.error
        log_func(f"[{severity.upper()}] {alert_type}: {message}")
        
        # 发送通知（如果配置了）
        if self.notification_manager and severity in ['warning', 'critical']:
            try:
                self.notification_manager.send_custom_notification(
                    title=f"⚠️ 系统告警 [{severity.upper()}]",
                    message=f"{alert_type}\n{message}",
                    channels=['telegram']  # 使用 Telegram 快速通知
                )
            except Exception as e:
                logger.error(f"发送告警通知失败: {e}")
        
        # 更新冷却期
        self.alert_cooldown[alert_type] = now
    
    def check_and_alert(self, monitor):
        """
        检查监控指标并发送告警
        
        Args:
            monitor: ApplicationMonitor 实例
        """
        health = monitor.check_health()
        
        if health['status'] == 'unhealthy':
            for check_name, check_result in health['checks'].items():
                if check_result.get('status') == 'critical':
                    self.send_alert(
                        f'{check_name}_critical',
                        f"{check_name.upper()} 使用率过高: {check_result['value']:.1f}% (阈值: {check_result.get('threshold', 'N/A')})",
                        severity='critical'
                    )

# 全局监控实例
app_monitor = ApplicationMonitor()
alert_manager = AlertManager()

def get_monitor():
    """获取监控器实例"""
    return app_monitor

def get_alert_manager():
    """获取告警管理器实例"""
    return alert_manager
