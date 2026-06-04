"""
性能优化工具
分析系统性能并提供优化建议
"""
import time
import psutil
import sys
import os
from functools import wraps

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.metrics = {}
    
    def profile_function(self, func):
        """函数性能分析装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            func_name = func.__name__
            self.metrics[func_name] = {
                'execution_time': end_time - start_time,
                'memory_used': end_memory - start_memory,
                'calls': self.metrics.get(func_name, {}).get('calls', 0) + 1
            }
            
            return result
        return wrapper
    
    def print_report(self):
        """打印性能报告"""
        print("\n" + "="*70)
        print("性能分析报告")
        print("="*70)
        print(f"{'函数名':<30} {'调用次数':<10} {'平均耗时(s)':<15} {'内存使用(MB)':<15}")
        print("-"*70)
        
        for func_name, metrics in sorted(self.metrics.items(), key=lambda x: x[1]['execution_time'], reverse=True):
            avg_time = metrics['execution_time'] / metrics['calls']
            print(f"{func_name:<30} {metrics['calls']:<10} {avg_time:<15.4f} {metrics['memory_used']:<15.2f}")
        
        print("="*70)

class DatabaseOptimizer:
    """数据库优化器"""
    
    @staticmethod
    def get_slow_queries():
        """获取慢查询（示例）"""
        recommendations = [
            {
                'query': 'SELECT * FROM metal_prices WHERE timestamp > ?',
                'issue': '全表扫描',
                'recommendation': '在 timestamp 字段添加索引',
                'sql': 'CREATE INDEX idx_metal_prices_timestamp ON metal_prices(timestamp)'
            },
            {
                'query': 'SELECT * FROM news WHERE content LIKE ?',
                'issue': 'LIKE 查询性能差',
                'recommendation': '使用全文索引或 Elasticsearch',
                'sql': 'ALTER TABLE news ADD FULLTEXT INDEX ft_content (content)'
            }
        ]
        return recommendations
    
    @staticmethod
    def suggest_indexes():
        """建议索引"""
        return [
            "CREATE INDEX idx_metal_prices_metal_timestamp ON metal_prices(metal_type, timestamp)",
            "CREATE INDEX idx_news_sentiment ON news(sentiment_label)",
            "CREATE INDEX idx_social_media_created ON social_media(created_at)"
        ]

class CacheOptimizer:
    """缓存优化器"""
    
    @staticmethod
    def analyze_cache_opportunities():
        """分析缓存机会"""
        return [
            {
                'endpoint': '/api/prices/latest',
                'current_cache': 'None',
                'recommendation': 'Redis缓存, TTL=60秒',
                'expected_improvement': '响应时间减少 80%'
            },
            {
                'endpoint': '/api/news/search',
                'current_cache': 'None',
                'recommendation': 'Redis缓存, TTL=300秒',
                'expected_improvement': '响应时间减少 70%'
            }
        ]
    
    @staticmethod
    def generate_redis_config():
        """生成Redis配置示例"""
        return """
# Redis 缓存配置示例
import redis
from flask_caching import Cache

# 初始化缓存
cache_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
    'CACHE_DEFAULT_TIMEOUT': 300
}

cache = Cache(app, config=cache_config)

# 使用缓存
@app.route('/api/prices/latest')
@cache.cached(timeout=60, query_string=True)
def get_prices():
    # ...
    pass
"""

class OptimizationRecommendations:
    """优化建议生成器"""
    
    @staticmethod
    def generate_report():
        """生成完整优化报告"""
        print("\n" + "="*70)
        print("PreciousInsight 性能优化建议")
        print("="*70)
        
        # 1. 数据库优化
        print("\n【1. 数据库优化】")
        print("-"*70)
        db_optimizer = DatabaseOptimizer()
        
        print("\n慢查询分析:")
        for i, query_info in enumerate(db_optimizer.get_slow_queries(), 1):
            print(f"\n{i}. {query_info['query']}")
            print(f"   问题: {query_info['issue']}")
            print(f"   建议: {query_info['recommendation']}")
            print(f"   SQL: {query_info['sql']}")
        
        print("\n建议添加的索引:")
        for idx_sql in db_optimizer.suggest_indexes():
            print(f"  - {idx_sql}")
        
        # 2. 缓存优化
        print("\n【2. 缓存优化】")
        print("-"*70)
        cache_optimizer = CacheOptimizer()
        
        for opportunity in cache_optimizer.analyze_cache_opportunities():
            print(f"\n端点: {opportunity['endpoint']}")
            print(f"  当前缓存: {opportunity['current_cache']}")
            print(f"  建议: {opportunity['recommendation']}")
            print(f"  预期改善: {opportunity['expected_improvement']}")
        
        # 3. 代码优化
        print("\n【3. 代码优化建议】")
        print("-"*70)
        print("""
  - 使用异步爬虫 (asyncio + aiohttp) 提升数据采集速度
  - 批量插入数据库，减少 I/O 操作
  - 使用连接池管理数据库连接
  - 启用 gzip 压缩 API 响应
  - 使用 CDN 加速静态资源
  - 实现 API 请求限流
        """)
        
        # 4. 系统优化
        print("\n【4. 系统资源优化】")
        print("-"*70)
        cpu_count = psutil.cpu_count()
        memory_total = psutil.virtual_memory().total / 1024 / 1024 / 1024
        
        print(f"""
  系统配置:
    - CPU 核心数: {cpu_count}
    - 总内存: {memory_total:.1f} GB
  
  优化建议:
    - 使用 Gunicorn 运行 Flask (workers={cpu_count * 2 + 1})
    - 配置 Nginx 反向代理
    - 启用进程管理器 (Supervisor)
    - 配置日志轮转 (logrotate)
        """)
        
        # 5. 监控优化
        print("\n【5. 监控与性能追踪】")
        print("-"*70)
        print("""
  - 集成 APM 工具 (New Relic / Datadog)
  - 使用 Prometheus + Grafana 可视化
  - 启用慢查询日志
  - 监控 API 响应时间分布
  - 设置性能告警阈值
        """)
        
        print("="*70)

def benchmark_api_endpoints():
    """API 端点性能基准测试"""
    import requests
    
    print("\n" + "="*70)
    print("API 端点性能基准测试")
    print("="*70)
    
    endpoints = [
        ('GET', 'http://localhost:5000/'),
        ('GET', 'http://localhost:5000/health'),
        ('GET', 'http://localhost:5000/metrics'),
        ('GET', 'http://localhost:5000/api/prices/latest?metal=gold'),
    ]
    
    results = []
    
    for method, url in endpoints:
        times = []
        for _ in range(10):
            try:
                start = time.time()
                if method == 'GET':
                    response = requests.get(url, timeout=5)
                else:
                    response = requests.post(url, timeout=5)
                end = time.time()
                
                if response.status_code == 200:
                    times.append(end - start)
            except Exception as e:
                print(f"错误: {url} - {e}")
                break
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results.append({
                'url': url,
                'avg': avg_time,
                'min': min_time,
                'max': max_time
            })
    
    print(f"\n{'端点':<50} {'平均(ms)':<12} {'最小(ms)':<12} {'最大(ms)':<12}")
    print("-"*70)
    for result in results:
        print(f"{result['url']:<50} {result['avg']*1000:<12.2f} {result['min']*1000:<12.2f} {result['max']*1000:<12.2f}")
    
    print("="*70)

def main():
    """主函数"""
    print("PreciousInsight 性能优化工具")
    print("\n选项:")
    print("1. 生成优化建议")
    print("2. API 性能基准测试")
    print("3. 显示缓存配置示例")
    print("4. 全部执行")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == '1' or choice == '4':
        OptimizationRecommendations.generate_report()
    
    if choice == '2' or choice == '4':
        print("\n提示: 请确保 Flask API 正在运行 (python app.py)")
        input("按 Enter 继续...")
        benchmark_api_endpoints()
    
    if choice == '3' or choice == '4':
        print("\n" + "="*70)
        print("Redis 缓存配置示例")
        print("="*70)
        print(CacheOptimizer.generate_redis_config())

if __name__ == '__main__':
    main()
