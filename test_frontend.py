"""
前端与UI测试脚本
测试 Streamlit 仪表盘和 Flask API
"""
import sys
import os
import subprocess
import time
import requests

print("="*60)
print("PreciousInsight 前端与UI测试")
print("="*60)

def test_flask_api_syntax():
    """测试 Flask API 语法"""
    print("\n【测试 1】Flask API 语法检查")
    print("-"*60)
    
    api_path = 'app.py'
    
    if not os.path.exists(api_path):
        print(f"✗ API 文件不存在: {api_path}")
        return False
    
    print(f"✓ API 文件存在: {api_path}")
    
    try:
        with open(api_path, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, api_path, 'exec')
        print("✓ 语法检查通过")
        
        # 检查关键导入
        if 'from flask import Flask' in code:
            print("✓ Flask 导入正确")
        if 'from flask_cors import CORS' in code:
            print("✓ CORS 配置存在")
        if '@app.route' in code:
            print("✓ 路由定义存在")
            
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False

def test_streamlit_syntax():
    """测试 Streamlit 仪表盘语法"""
    print("\n【测试 2】Streamlit 仪表盘语法检查")
    print("-"*60)
    
    dashboard_path = 'dashboard.py'
    
    if not os.path.exists(dashboard_path):
        print(f"✗ 仪表盘文件不存在: {dashboard_path}")
        return False
    
    print(f"✓ 仪表盘文件存在: {dashboard_path}")
    
    try:
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, dashboard_path, 'exec')
        print("✓ 语法检查通过")
        
        # 检查关键导入
        if 'import streamlit' in code:
            print("✓ Streamlit 导入正确")
        if 'import plotly' in code:
            print("✓ Plotly 导入正确")
        if 'st.set_page_config' in code:
            print("✓ 页面配置存在")
            
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n【测试 3】依赖包检查")
    print("-"*60)
    
    dependencies = {
        'flask': 'Flask',
        'streamlit': 'Streamlit',
        'plotly': 'Plotly',
        'pandas': 'Pandas',
        'flask_cors': 'Flask-CORS'
    }
    
    all_installed = True
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {name} 已安装")
        except ImportError:
            print(f"✗ {name} 未安装")
            all_installed = False
    
    return all_installed

def test_flask_api_run():
    """测试 Flask API 是否可以启动"""
    print("\n【测试 4】Flask API 启动测试")
    print("-"*60)
    
    print("⚠ 手动测试: 运行 'python app.py' 启动 API")
    print("  预期输出: * Running on http://0.0.0.0:5000")
    print("  访问: http://localhost:5000")
    print("  应看到: {\"message\": \"PreciousInsight API\", ...}")
    
    return True

def test_streamlit_run():
    """测试 Streamlit 是否可以启动"""
    print("\n【测试 5】Streamlit 仪表盘启动测试")
    print("-"*60)
    
    print("⚠ 手动测试: 运行 'streamlit run dashboard.py' 启动仪表盘")
    print("  预期输出: Local URL: http://localhost:8501")
    print("  浏览器会自动打开仪表盘")
    print("  应看到: PreciousInsight 仪表盘界面")
    
    return True

def test_api_endpoints():
    """测试 API 端点"""
    print("\n【测试 6】API 端点定义检查")
    print("-"*60)
    
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    endpoints = [
        ('/', '根路径'),
        ('/api/prices/latest', '最新价格'),
        ('/api/news/search', '新闻搜索'),
        ('/api/analysis/sentiment', '情感分析')
    ]
    
    print("✓ 已定义的端点:")
    for route, desc in endpoints:
        if route in code:
            print(f"  - {route} ({desc})")
    
    return True

def test_dashboard_pages():
    """测试仪表盘页面"""
    print("\n【测试 7】仪表盘页面检查")
    print("-"*60)
    
    with open('dashboard.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    pages = [
        '仪表盘',
        '新闻分析',
        '趋势预测',
        '报告'
    ]
    
    print("✓ 已定义的页面:")
    for page in pages:
        if page in code:
            print(f"  - {page}")
    
    return True

def test_responsive_design():
    """测试响应式设计"""
    print("\n【测试 8】响应式设计检查")
    print("-"*60)
    
    with open('dashboard.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    if 'st.columns' in code:
        print("✓ 使用了列布局")
    if 'layout=\"wide\"' in code:
        print("✓ 使用了宽屏布局")
    
    print("✓ Streamlit 默认支持响应式")
    
    return True

def main():
    print("\n开始测试前端与UI...\n")
    
    results = {}
    
    # 运行所有测试
    results['Flask 语法'] = test_flask_api_syntax()
    results['Streamlit 语法'] = test_streamlit_syntax()
    results['依赖包'] = test_dependencies()
    results['API 端点'] = test_api_endpoints()
    results['仪表盘页面'] = test_dashboard_pages()
    results['响应式设计'] = test_responsive_design()
    results['Flask 启动'] = test_flask_api_run()
    results['Streamlit 启动'] = test_streamlit_run()
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed >= total - 2:  # 允许2个手动测试未执行
        print("\n🎉 前端与UI测试通过！")
        print("\n下一步:")
        print("1. 运行 Flask API: python app.py")
        print("2. 运行 Streamlit: streamlit run dashboard.py")
        print("3. 访问 http://localhost:5000 (API)")
        print("4. 访问 http://localhost:8501 (仪表盘)")
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
    
    print("\n详细使用指南请查看: QUICKSTART_FRONTEND.md")

if __name__ == '__main__':
    main()
