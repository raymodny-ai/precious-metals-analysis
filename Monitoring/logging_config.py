"""
日志聚合配置
结构化日志输出，支持多种格式和目标
"""
import os
import sys
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)

class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, app_name='PreciousInsight', log_dir='logs'):
        self.app_name = app_name
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """配置日志系统"""
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器（JSON 格式，按大小轮转）
        json_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'app.json.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
        
        # 错误日志文件（仅记录错误和严重错误）
        error_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'errors.log'),
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(console_formatter)
        root_logger.addHandler(error_handler)
        
        # 性能日志（按天轮转）
        performance_handler = TimedRotatingFileHandler(
            os.path.join(self.log_dir, 'performance.log'),
            when='midnight',
            interval=1,
            backupCount=30
        )
        performance_handler.setLevel(logging.INFO)
        performance_handler.setFormatter(console_formatter)
        
        # 只让性能日志器使用这个处理器
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(performance_handler)
        perf_logger.propagate = False
    
    def log_api_call(self, endpoint, method, status_code, response_time, user=None):
        """记录 API 调用"""
        logger = logging.getLogger('api')
        extra = {
            'extra_fields': {
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time': response_time,
                'user': user
            }
        }
        logger.info(f"API Call: {method} {endpoint} - {status_code} ({response_time:.3f}s)", extra=extra)
    
    def log_data_collection(self, source, records_count, success=True, error=None):
        """记录数据采集"""
        logger = logging.getLogger('data_collector')
        extra = {
            'extra_fields': {
                'source': source,
                'records_count': records_count,
                'success': success,
                'error': str(error) if error else None
            }
        }
        
        if success:
            logger.info(f"Data collected from {source}: {records_count} records", extra=extra)
        else:
            logger.error(f"Data collection failed from {source}: {error}", extra=extra)
    
    def log_performance_metric(self, metric_name, value, unit='ms'):
        """记录性能指标"""
        perf_logger = logging.getLogger('performance')
        perf_logger.info(f"{metric_name}: {value}{unit}")

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_file='logs/app.json.log'):
        self.log_file = log_file
    
    def analyze_errors(self, hours=24):
        """分析最近的错误"""
        if not os.path.exists(self.log_file):
            return {'error': 'Log file not found'}
        
        errors = []
        error_count = 0
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        if log_entry.get('level') in ['ERROR', 'CRITICAL']:
                            errors.append(log_entry)
                            error_count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            return {'error': str(e)}
        
        return {
            'total_errors': error_count,
            'recent_errors': errors[-10:] if errors else [],
            'error_types': self._categorize_errors(errors)
        }
    
    def _categorize_errors(self, errors):
        """按类型分类错误"""
        categories = {}
        for error in errors:
            module = error.get('module', 'unknown')
            categories[module] = categories.get(module, 0) + 1
        return categories
    
    def get_stats(self):
        """获取日志统计"""
        if not os.path.exists(self.log_file):
            return {}
        
        stats = {
            'total_lines': 0,
            'levels': {},
            'modules': {}
        }
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    stats['total_lines'] += 1
                    try:
                        log_entry = json.loads(line)
                        level = log_entry.get('level', 'UNKNOWN')
                        module = log_entry.get('module', 'unknown')
                        
                        stats['levels'][level] = stats['levels'].get(level, 0) + 1
                        stats['modules'][module] = stats['modules'].get(module, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            stats['error'] = str(e)
        
        return stats

# 全局日志器实例
structured_logger = StructuredLogger()

def get_logger(name=None):
    """获取日志器"""
    return logging.getLogger(name) if name else logging.getLogger()

def log_api_call(endpoint, method, status_code, response_time, user=None):
    """快捷函数：记录 API 调用"""
    structured_logger.log_api_call(endpoint, method, status_code, response_time, user)

def log_data_collection(source, records_count, success=True, error=None):
    """快捷函数：记录数据采集"""
    structured_logger.log_data_collection(source, records_count, success, error)
