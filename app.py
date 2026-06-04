def before_request():
    g.start_time = time.time()

# 请求后钩子
@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        response_time = time.time() - g.start_time
        
        # 记录 API 调用
        log_api_call(
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # 记录到监控器
        monitor.record_api_call(
            endpoint=request.path,
            response_time=response_time,
            success=(200 <= response.status_code < 400)
        )
        
        # 添加响应时间头
        response.headers['X-Response-Time'] = f"{response_time:.3f}s"
    
    return response

@app.route('/')
def index():
    return jsonify({"message": "PreciousInsight API", "version": "1.0"})

@app.route('/health')
def health_check():
    """健康检查端点"""
    health_status = monitor.check_health()
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/metrics')
def metrics():
    """指标端点"""
    summary = monitor.get_metrics_summary()
    return jsonify(summary)

@app.route('/api/prices/latest', methods=['GET'])
def get_latest_prices():
    """获取最新价格"""
    metal = request.args.get('metal', 'gold')
    # TODO: Fetch from database
    return jsonify({
        "metal": metal,
        "price": 2050.00,
        "change_24h": 1.2,
        "timestamp": "2024-11-27T17:30:00Z"
    })

@app.route('/api/news/search', methods=['POST'])
def search_news():
    """搜索新闻"""
    data = request.json
    keyword = data.get('keyword', '')
    # TODO: Query database
    return jsonify({
        "results": [
            {
                "title": "Sample news article",
                "sentiment": "positive",
                "url": "https://example.com"
            }
        ]
    })

@app.route('/api/analysis/sentiment', methods=['POST'])
def analyze_sentiment():
    """情感分析"""
    text = request.json.get('text', '')
    # TODO: Use sentiment analyzer
    return jsonify({
        "label": "positive",
        "score": 0.85
    })

def before_request():
    g.start_time = time.time()

# 请求后钩子
@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        response_time = time.time() - g.start_time
        
        # 记录 API 调用
        log_api_call(
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # 记录到监控器
        monitor.record_api_call(
            endpoint=request.path,
            response_time=response_time,
            success=(200 <= response.status_code < 400)
        )
        
        # 添加响应时间头
        response.headers['X-Response-Time'] = f"{response_time:.3f}s"
    
    return response

@app.route('/')
def index():
    return jsonify({"message": "PreciousInsight API", "version": "1.0"})

@app.route('/health')
def health_check():
    """健康检查端点"""
    health_status = monitor.check_health()
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/metrics')
def metrics():
    """指标端点"""
    summary = monitor.get_metrics_summary()
    return jsonify(summary)

@app.route('/api/prices/latest', methods=['GET'])
def get_latest_prices():
    """获取最新价格"""
    metal = request.args.get('metal', 'gold')
    # TODO: Fetch from database
    return jsonify({
        "metal": metal,
        "price": 2050.00,
        "change_24h": 1.2,
        "timestamp": "2024-11-27T17:30:00Z"
    })

@app.route('/api/news/search', methods=['POST'])
def search_news():
    """搜索新闻"""
    data = request.json
    keyword = data.get('keyword', '')
    # TODO: Query database
    return jsonify({
        "results": [
            {
                "title": "Sample news article",
                "sentiment": "positive",
                "url": "https://example.com"
            }
        ]
    })

@app.route('/api/analysis/sentiment', methods=['POST'])
def analyze_sentiment():
    """情感分析"""
    text = request.json.get('text', '')
    # TODO: Use sentiment analyzer
    return jsonify({
        "label": "positive",
        "score": 0.85
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # 注册扩展API
    from api_extensions import register_extended_apis
    register_extended_apis(app)
    
    # 启动应用
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
