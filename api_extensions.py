"""
Flask API扩展 - 股票和LLM端点
添加新的REST API端点
"""
from flask import Blueprint, jsonify, request
import logging

from DataCollector.StockDataCollector.yfinance_client import YFinanceStockClient
from AnalysisEngine.LLMService.llm_service import get_llm_service
from AnalysisEngine.LLMService.base import LLMRequest, TaskType

logger = logging.getLogger(__name__)

# 创建蓝图
stock_bp = Blueprint('stocks', __name__, url_prefix='/api/stocks')
llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')
correlation_bp = Blueprint('correlation', __name__, url_prefix='/api/correlation')

# 初始化服务
stock_client = YFinanceStockClient()
llm_service = get_llm_service()

# ============ 股票数据端点 ============

@stock_bp.route('/list', methods=['GET'])
def get_stock_list():
    """获取监控股票列表"""
    try:
        category = request.args.get('category', 'all').lower()
        
        if category == 'etf':
            symbols = stock_client.PRECIOUS_METAL_ETFS
        elif category == 'mining':
            symbols = stock_client.MINING_STOCKS
        elif category == 'index':
            symbols = stock_client.INDICES
        else:
            symbols = stock_client.all_symbols
        
        return jsonify({
            'success': True,
            'category': category,
            'count': len(symbols),
            'symbols': symbols
        })
    
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@stock_bp.route('/<symbol>/price', methods=['GET'])
def get_stock_price(symbol):
    """获取股票当前价格"""
    try:
        price_data = stock_client.get_current_price(symbol.upper())
        
        if not price_data:
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': price_data
        })
    
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@stock_bp.route('/<symbol>/history', methods=['GET'])
def get_stock_history(symbol):
    """获取历史价格数据"""
    try:
        period = request.args.get('period', '1mo')
        interval = request.args.get('interval', '1d')
        
        hist = stock_client.get_historical_data(
            symbol.upper(),
            period=period,
            interval=interval
        )
        
        if hist is None or hist.empty:
            return jsonify({'success': False, 'error': 'No data available'}), 404
        
        # 转换为JSON格式
        hist_dict = hist.to_dict('records')
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'period': period,
            'interval': interval,
            'count': len(hist_dict),
            'data': hist_dict
        })
    
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@stock_bp.route('/<symbol>/correlation', methods=['GET'])
def get_stock_correlation(symbol):
    """获取与金价的相关性"""
    try:
        period = request.args.get('period', '3mo')
        
        correlation = stock_client.calculate_correlation_with_gold(
            symbol.upper(),
            period=period
        )
        
        if correlation is None:
            return jsonify({'success': False, 'error': 'Unable to calculate correlation'}), 404
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'gold_correlation': correlation,
            'period': period
        })
    
    except Exception as e:
        logger.error(f"Error calculating correlation for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@stock_bp.route('/screener', methods=['GET'])
def stock_screener():
    """股票筛选器"""
    try:
        # 获取筛选条件
        min_corr = request.args.get('min_correlation', type=float)
        max_pe = request.args.get('max_pe', type=float)
        min_volume = request.args.get('min_volume', type=int)
        category = request.args.get('category')
        sort_by = request.args.get('sort_by', 'correlation')
        
        criteria = {}
        if min_corr is not None:
            criteria['min_correlation'] = min_corr
        if max_pe is not None:
            criteria['max_pe'] = max_pe
        if min_volume is not None:
            criteria['min_volume'] = min_volume
        if category:
            criteria['category'] = category
        criteria['sort_by'] = sort_by
        
        results = stock_client.screen_stocks(criteria)
        
        return jsonify({
            'success': True,
            'criteria': criteria,
            'count': len(results),
            'data': results
        })
    
    except Exception as e:
        logger.error(f"Error in stock screener: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ LLM分析端点 ============

@llm_bp.route('/analyze', methods=['POST'])
def llm_analyze():
    """LLM市场分析"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({'success': False, 'error': 'Missing prompt'}), 400
        
        prompt = data['prompt']
        task_type = TaskType.ANALYSIS
        
        llm_request = LLMRequest(
            task_type=task_type,
            prompt=prompt,
            system_prompt="你是资深贵金属市场分析师"
        )
        
        response = llm_service.complete(llm_request)
        
        if not response:
            return jsonify({'success': False, 'error': 'LLM request failed'}), 500
        
        return jsonify({
            'success': True,
            'analysis': response.content,
            'metadata': {
                'model': response.model,
                'provider': response.provider.value,
                'tokens': response.tokens_used,
                'cost': response.cost,
                'latency': response.latency,
                'cached': response.cached
            }
        })
    
    except Exception as e:
        logger.error(f"Error in LLM analyze: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@llm_bp.route('/summarize', methods=['POST'])
def llm_summarize():
    """LLM文本摘要"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Missing text'}), 400
        
        text = data['text']
        max_length = data.get('max_length', 200)
        
        summary = llm_service.summarize(text, max_length=max_length)
        
        if not summary:
            return jsonify({'success': False, 'error': 'Summarization failed'}), 500
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"Error in LLM summarize: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@llm_bp.route('/ask', methods=['POST'])
def llm_ask():
    """LLM问答"""
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'success': False, 'error': 'Missing question'}), 400
        
        question = data['question']
        context = data.get('context')
        
        answer = llm_service.ask(question, context=context)
        
        if not answer:
            return jsonify({'success': False, 'error': 'Question failed'}), 500
        
        return jsonify({
            'success': True,
            'answer': answer
        })
    
    except Exception as e:
        logger.error(f"Error in LLM ask: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@llm_bp.route('/stats', methods=['GET'])
def llm_stats():
    """LLM使用统计"""
    try:
        stats = llm_service.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"Error getting LLM stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ 相关性分析端点 ============

@correlation_bp.route('/gold-stocks', methods=['GET'])
def gold_stocks_correlation():
    """黄金与股票的相关性"""
    try:
        symbols = request.args.get('symbols', 'GLD,SLV,NEM,GOLD').split(',')
        period = request.args.get('period', '3mo')
        
        results = []
        for symbol in symbols:
            symbol = symbol.strip().upper()
            corr = stock_client.calculate_correlation_with_gold(symbol, period=period)
            
            if corr is not None:
                results.append({
                    'symbol': symbol,
                    'correlation': corr,
                    'category': stock_client.get_category(symbol)
                })
        
        # 按相关性排序
        results.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        return jsonify({
            'success': True,
            'period': period,
            'count': len(results),
            'data': results
        })
    
    except Exception as e:
        logger.error(f"Error in gold-stocks correlation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@correlation_bp.route('/matrix', methods=['GET'])
def correlation_matrix():
    """相关性矩阵"""
    try:
        symbols_param = request.args.get('symbols', 'GLD,SLV,NEM,GOLD,GDX')
        symbols = [s.strip().upper() for s in symbols_param.split(',')]
        period = request.args.get('period', '3mo')
        
        import pandas as pd
        
        # 获取所有股票的历史数据
        dfs = []
        for symbol in symbols:
            df = stock_client.get_historical_data(symbol, period=period)
            if df is not None and not df.empty:
                dfs.append(df[['Close']].rename(columns={'Close': symbol}))
        
        if len(dfs) < 2:
            return jsonify({'success': False, 'error': 'Insufficient data'}), 404
        
        # 合并数据
        merged = dfs[0]
        for df in dfs[1:]:
            merged = merged.join(df, how='inner')
        
        # 计算相关性矩阵
        corr_matrix = merged.corr()
        
        # 转换为JSON格式
        matrix_dict = corr_matrix.to_dict()
        
        return jsonify({
            'success': True,
            'period': period,
            'symbols': list(corr_matrix.columns),
            'matrix': matrix_dict
        })
    
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 注册蓝图的函数
def register_extended_apis(app):
    """注册扩展API蓝图"""
    app.register_blueprint(stock_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(correlation_bp)
    logger.info("Extended APIs registered successfully")
