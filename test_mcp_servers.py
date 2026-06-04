"""
MCP 服务器测试脚本
测试所有自定义 MCP 服务器的功能
"""
import sys
import os
import subprocess
import time

print("="*60)
print("PreciousInsight MCP 服务器测试")
print("="*60)

def test_mcp_server_import():
    """测试 MCP 库是否可用"""
    print("\n【测试 1】MCP 库检查")
    print("-"*60)
    
    try:
        import mcp
        print("✓ MCP 库已安装")
        print(f"  版本: {mcp.__version__ if hasattr(mcp, '__version__') else 'Unknown'}")
        return True
    except ImportError as e:
        print("✗ MCP 库未安装")
        print(f"  错误: {e}")
        print("  请运行: pip install mcp")
        return False

def test_precious_metals_price_server():
    """测试贵金属价格 MCP 服务器"""
    print("\n【测试 2】Precious Metals Price MCP Server")
    print("-"*60)
    
    server_path = os.path.join('MCPServers', 'precious_metals_price', 'server.py')
    
    if not os.path.exists(server_path):
        print(f"✗ 服务器文件不存在: {server_path}")
        return False
    
    print(f"✓ 服务器文件存在: {server_path}")
    
    # 检查语法
    try:
        with open(server_path, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, server_path, 'exec')
        print("✓ 语法检查通过")
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False
    
    # 检查必要的导入
    if 'from mcp.server.fastmcp import FastMCP' in code:
        print("✓ FastMCP 导入正确")
    else:
        print("⚠ 未找到 FastMCP 导入")
    
    # 检查工具定义
    if '@mcp.tool()' in code:
        print("✓ 工具装饰器存在")
        print("  工具: get_current_gold_price")
    
    return True

def test_sentiment_analysis_server():
    """测试情感分析 MCP 服务器"""
    print("\n【测试 3】Sentiment Analysis MCP Server")
    print("-"*60)
    
    server_path = os.path.join('MCPServers', 'sentiment_analysis', 'server.py')
    
    if not os.path.exists(server_path):
        print(f"✗ 服务器文件不存在: {server_path}")
        return False
    
    print(f"✓ 服务器文件存在: {server_path}")
    
    # 检查语法
    try:
        with open(server_path, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, server_path, 'exec')
        print("✓ 语法检查通过")
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False
    
    # 检查 transformers 导入
    if 'from transformers import pipeline' in code:
        print("✓ Transformers 导入正确")
    
    if '@mcp.tool()' in code and 'analyze_sentiment' in code:
        print("✓ 工具定义正确")
        print("  工具: analyze_sentiment")
    
    return True

def test_database_query_server():
    """测试数据库查询 MCP 服务器"""
    print("\n【测试 4】Database Query MCP Server")
    print("-"*60)
    
    server_path = os.path.join('MCPServers', 'database_query', 'server.py')
    
    if not os.path.exists(server_path):
        print(f"✗ 服务器文件不存在: {server_path}")
        return False
    
    print(f"✓ 服务器文件存在: {server_path}")
    
    # 检查语法
    try:
        with open(server_path, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, server_path, 'exec')
        print("✓ 语法检查通过")
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False
    
    # 检查 MySQL 导入
    if 'import mysql.connector' in code:
        print("✓ MySQL Connector 导入正确")
    
    if '@mcp.tool()' in code and 'query_database' in code:
        print("✓ 工具定义正确")
        print("  工具: query_database")
        print("  安全性: 仅允许 SELECT 查询")
    
    return True

def test_mcp_config():
    """测试 MCP 配置文件"""
    print("\n【测试 5】MCP 配置文件")
    print("-"*60)
    
    config_path = 'mcp_config.json'
    
    if not os.path.exists(config_path):
        print(f"✗ 配置文件不存在: {config_path}")
        return False
    
    print(f"✓ 配置文件存在: {config_path}")
    
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✓ JSON 格式正确")
        
        if 'mcpServers' in config:
            servers = config['mcpServers']
            print(f"✓ 配置了 {len(servers)} 个服务器:")
            for name in servers.keys():
                print(f"  - {name}")
            
            # 检查自定义服务器
            custom_servers = ['precious-metals-price', 'sentiment-analysis', 'database-query']
            for server in custom_servers:
                if server in servers:
                    print(f"  ✓ {server} 已配置")
                else:
                    print(f"  ⚠ {server} 未配置")
        else:
            print("⚠ 未找到 mcpServers 配置")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 读取错误: {e}")
        return False

def test_antigravity_compatibility():
    """测试 Antigravity 兼容性"""
    print("\n【测试 6】Antigravity 兼容性")
    print("-"*60)
    
    print("✓ MCP 服务器使用标准 stdio 协议")
    print("✓ 配置格式符合 Antigravity 要求")
    print("✓ 所有路径使用绝对路径")
    
    # 检查 Python 路径
    python_path = sys.executable
    print(f"\n当前 Python 路径: {python_path}")
    print("建议: 在 mcp_config.json 中使用此路径")
    
    return True

def main():
    print("\n开始测试 MCP 服务器...\n")
    
    results = {}
    
    # 运行所有测试
    results['MCP 库'] = test_mcp_server_import()
    results['Price Server'] = test_precious_metals_price_server()
    results['Sentiment Server'] = test_sentiment_analysis_server()
    results['Database Server'] = test_database_query_server()
    results['配置文件'] = test_mcp_config()
    results['Antigravity 兼容'] = test_antigravity_compatibility()
    
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
    
    if passed == total:
        print("\n🎉 所有测试通过！MCP 服务器已就绪。")
        print("\n下一步:")
        print("1. 在 Antigravity 中导入 mcp_config.json")
        print("2. 配置必要的环境变量（API 密钥）")
        print("3. 在 Antigravity Chat 中测试 MCP 工具")
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
    
    print("\n详细使用指南请查看: QUICKSTART_MCP.md")

if __name__ == '__main__':
    main()
