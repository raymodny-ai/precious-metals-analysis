"""
LLM成本追踪系统
详细记录每次LLM调用的成本和使用情况
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path
import logging

from .base import LLMProvider

logger = logging.getLogger(__name__)

class CostTracker:
    """LLM调用成本追踪器"""
    
    def __init__(self, db_path: str = "logs/llm_costs.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                task_type TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost REAL,
                latency REAL,
                cached BOOLEAN DEFAULT 0,
                user_id TEXT,
                session_id TEXT,
                metadata TEXT
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON llm_calls(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider_model 
            ON llm_calls(provider, model)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_type 
            ON llm_calls(task_type)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cost tracker database initialized: {self.db_path}")
    
    def log_call(self, provider: LLMProvider, model: str, task_type: str,
                 prompt_tokens: int, completion_tokens: int, total_tokens: int,
                 cost: float, latency: float, cached: bool = False,
                 user_id: Optional[str] = None, session_id: Optional[str] = None,
                 metadata: Optional[str] = None):
        """
        记录一次LLM调用
        
        Args:
            provider: LLM提供商
            model: 模型名称
            task_type: 任务类型
            prompt_tokens: 输入token数
            completion_tokens: 输出token数
            total_tokens: 总token数
            cost: 成本（美元）
            latency: 延迟（秒）
            cached: 是否来自缓存
            user_id: 用户ID（可选）
            session_id: 会话ID（可选）
            metadata: 额外元数据（可选）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO llm_calls 
            (provider, model, task_type, prompt_tokens, completion_tokens, 
             total_tokens, cost, latency, cached, user_id, session_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            provider.value if isinstance(provider, LLMProvider) else provider,
            model, task_type, prompt_tokens, completion_tokens,
            total_tokens, cost, latency, cached, user_id, session_id, metadata
        ))
        
        conn.commit()
        conn.close()
    
    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """获取指定日期的总成本"""
        if date is None:
            date = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) FROM llm_calls
            WHERE DATE(timestamp) = DATE(?)
            AND cached = 0
        """, (date.strftime("%Y-%m-%d"),))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return float(result)
    
    def get_monthly_cost(self, year: Optional[int] = None, month: Optional[int] = None) -> float:
        """获取指定月份的总成本"""
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) FROM llm_calls
            WHERE strftime('%Y', timestamp) = ?
            AND strftime('%m', timestamp) = ?
            AND cached = 0
        """, (str(year), f"{month:02d}"))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return float(result)
    
    def get_cost_by_provider(self, days: int = 30) -> Dict[str, float]:
        """获取各提供商的成本分布"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT provider, SUM(cost) as total_cost
            FROM llm_calls
            WHERE timestamp >= datetime('now', ? || ' days')
            AND cached = 0
            GROUP BY provider
            ORDER BY total_cost DESC
        """, (f"-{days}",))
        
        results = {row[0]: float(row[1]) for row in cursor.fetchall()}
        conn.close()
        
        return results
    
    def get_cost_by_task_type(self, days: int = 30) -> Dict[str, float]:
        """获取各任务类型的成本分布"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_type, SUM(cost) as total_cost
            FROM llm_calls
            WHERE timestamp >= datetime('now', ? || ' days')
            AND cached = 0
            GROUP BY task_type
            ORDER BY total_cost DESC
        """, (f"-{days}",))
        
        results = {row[0]: float(row[1]) for row in cursor.fetchall()}
        conn.close()
        
        return results
    
    def get_usage_stats(self, days: int = 7) -> Dict:
        """获取详细使用统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总体统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN cached = 1 THEN 1 ELSE 0 END) as cached_calls,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                AVG(latency) as avg_latency
            FROM llm_calls
            WHERE timestamp >= datetime('now', ? || ' days')
        """, (f"-{days}",))
        
        row = cursor.fetchone()
        stats = {
            'total_calls': row[0] or 0,
            'cached_calls': row[1] or 0,
            'cache_hit_rate': (row[1] / row[0]) if row[0] > 0 else 0,
            'total_tokens': row[2] or 0,
            'total_cost': float(row[3] or 0),
            'avg_latency': float(row[4] or 0)
        }
        
        # 按提供商统计
        stats['by_provider'] = self.get_cost_by_provider(days)
        
        # 按任务类型统计
        stats['by_task_type'] = self.get_cost_by_task_type(days)
        
        conn.close()
        
        return stats
    
    def get_daily_trend(self, days: int = 30) -> pd.DataFrame:
        """获取每日成本趋势"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as calls,
                SUM(total_tokens) as tokens,
                SUM(cost) as cost
            FROM llm_calls
            WHERE timestamp >= datetime('now', ? || ' days')
            AND cached = 0
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, conn, params=(f"-{days}",))
        
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def get_top_expensive_calls(self, limit: int = 10, days: int = 7) -> List[Dict]:
        """获取最昂贵的调用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                timestamp, provider, model, task_type,
                total_tokens, cost, latency
            FROM llm_calls
            WHERE timestamp >= datetime('now', ? || ' days')
            AND cached = 0
            ORDER BY cost DESC
            LIMIT ?
        """, (f"-{days}", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'timestamp': row[0],
                'provider': row[1],
                'model': row[2],
                'task_type': row[3],
                'tokens': row[4],
                'cost': float(row[5]),
                'latency': float(row[6])
            })
        
        conn.close()
        
        return results
    
    def generate_report(self, days: int = 30) -> str:
        """生成成本报告"""
        stats = self.get_usage_stats(days)
        trend = self.get_daily_trend(days)
        
        report = f"""
# LLM成本报告 (最近{days}天)

## 总体统计
- 总调用次数: {stats['total_calls']:,}
- 缓存命中: {stats['cached_calls']:,} ({stats['cache_hit_rate']:.1%})
- 总Token数: {stats['total_tokens']:,}
- 总成本: ${stats['total_cost']:.2f}
- 平均延迟: {stats['avg_latency']:.2f}s

## 成本分解

### 按提供商
"""
        for provider, cost in stats['by_provider'].items():
            percentage = (cost / stats['total_cost'] * 100) if stats['total_cost'] > 0 else 0
            report += f"- {provider}: ${cost:.2f} ({percentage:.1f}%)\n"
        
        report += "\n### 按任务类型\n"
        for task, cost in stats['by_task_type'].items():
            percentage = (cost / stats['total_cost'] * 100) if stats['total_cost'] > 0 else 0
            report += f"- {task}: ${cost:.2f} ({percentage:.1f}%)\n"
        
        if not trend.empty:
            report += f"\n## 每日趋势\n"
            report += f"- 日均成本: ${trend['cost'].mean():.2f}\n"
            report += f"- 最高单日: ${trend['cost'].max():.2f}\n"
            report += f"- 最低单日: ${trend['cost'].min():.2f}\n"
        
        return report
    
    def set_budget_alert(self, daily_limit: float = 10.0, monthly_limit: float = 200.0):
        """设置预算告警（返回是否超出）"""
        daily_cost = self.get_daily_cost()
        monthly_cost = self.get_monthly_cost()
        
        alerts = []
        
        if daily_cost > daily_limit:
            alerts.append(f"⚠️ 今日成本 ${daily_cost:.2f} 已超出每日限额 ${daily_limit:.2f}")
        
        if monthly_cost > monthly_limit:
            alerts.append(f"⚠️ 本月成本 ${monthly_cost:.2f} 已超出月度限额 ${monthly_limit:.2f}")
        
        return alerts

# 全局追踪器实例
_cost_tracker = None

def get_cost_tracker() -> CostTracker:
    """获取成本追踪器单例"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
