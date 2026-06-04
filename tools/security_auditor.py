"""
安全审计与加固工具
检查安全漏洞并提供加固建议
"""
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SecurityAuditor:
    """安全审计器"""
    
    def __init__(self, project_root):
        self.project_root = project_root
        self.issues = []
    
    def check_env_file_security(self):
        """检查环境变量文件安全"""
        print("\n【检查 1】环境变量安全")
        print("-"*70)
        
        env_file = os.path.join(self.project_root, '.env')
        gitignore_file = os.path.join(self.project_root, '.gitignore')
        
        # 检查 .env 是否被git忽略
        if os.path.exists(gitignore_file):
            with open(gitignore_file, 'r') as f:
                gitignore_content = f.read()
                if '.env' in gitignore_content:
                    print("✓ .env 文件已添加到 .gitignore")
                else:
                    print("✗ 警告: .env 文件未添加到 .gitignore")
                    self.issues.append({
                        'severity': 'HIGH',
                        'issue': '.env file not in .gitignore',
                        'recommendation': '在 .gitignore 中添加 .env'
                    })
        
        # 检查是否有硬编码的密钥
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if 'your_' in line.lower() or 'example' in line.lower():
                        print("⚠ 发现示例密钥，请替换为实际值")
    
    def check_sql_injection(self):
        """检查SQL注入风险"""
        print("\n【检查 2】SQL 注入防护")
        print("-"*70)
        
        sql_patterns = [
            r'execute\s*\(',
            r'cursor\.execute\s*\(\s*["\'].*%s',
            r'cursor\.execute\s*\(\s*["\'].*\+',
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        found_issues = False
        for filepath in python_files:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for pattern in sql_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        print(f"⚠ 潜在SQL注入风险: {filepath}")
                        found_issues = True
                        self.issues.append({
                            'severity': 'CRITICAL',
                            'file': filepath,
                            'issue': 'Potential SQL injection',
                            'recommendation': '使用参数化查询'
                        })
                        break
        
        if not found_issues:
            print("✓ 未发现明显的SQL注入风险")
    
    def check_api_security(self):
        """检查API安全配置"""
        print("\n【检查 3】API 安全配置")
        print("-"*70)
        
        recommendations = []
        
        # 检查是否有认证
        app_file = os.path.join(self.project_root, 'app.py')
        if os.path.exists(app_file):
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if 'login_required' not in content and 'auth' not in content.lower():
                    print("⚠ API 未配置认证")
                    recommendations.append('添加 API 认证 (JWT, OAuth2)')
                
                if 'limiter' not in content.lower():
                    print("⚠ API 未配置限流")
                    recommendations.append('添加请求限流 (Flask-Limiter)')
                
                if 'CORS' in content:
                    print("✓ 已配置 CORS")
                    if "CORS(app)" in content or "origins='*'" in content:
                        print("⚠ CORS 配置过于宽松")
                        recommendations.append('限制 CORS 允许的域名')
        
        if recommendations:
            print("\n建议:")
            for rec in recommendations:
                print(f"  - {rec}")
    
    def check_sensitive_data_exposure(self):
        """检查敏感数据暴露"""
        print("\n【检查 4】敏感数据暴露")
        print("-"*70)
        
        # 检查是否有明文密码
        sensitive_patterns = [
            (r'password\s*=\s*["\'](?!your_|<)[^"\']+["\']', 'Hardcoded password'),
            (r'api_key\s*=\s*["\'](?!your_|<)[A-Za-z0-9]{20,}["\']', 'Hardcoded API key'),
            (r'secret\s*=\s*["\'](?!your_|<)[^"\']+["\']', 'Hardcoded secret'),
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 跳过虚拟环境和缓存目录
            if 'venv' in root or '__pycache__' in root or '.git' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        found = False
        for filepath in python_files:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for pattern, issue_type in sensitive_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        rel_path = os.path.relpath(filepath, self.project_root)
                        print(f"⚠ {issue_type} 在 {rel_path}")
                        found = True
        
        if not found:
            print("✓ 未发现硬编码的敏感信息")
    
    def check_dependency_security(self):
        """检查依赖安全"""
        print("\n【检查 5】依赖包安全")
        print("-"*70)
        
        requirements_file = os.path.join(self.project_root, 'requirements.txt')
        if os.path.exists(requirements_file):
            print("建议定期运行安全检查:")
            print("  pip install safety")
            print("  safety check -r requirements.txt")
            print("\n或使用:")
            print("  pip-audit")
    
    def generate_security_recommendations(self):
        """生成安全加固建议"""
        print("\n" + "="*70)
        print("安全加固建议")
        print("="*70)
        
        print("""
【1. 认证与授权】
  ✓ 实现 JWT 令牌认证
  ✓ 添加 API 密钥验证
  ✓ 实现基于角色的访问控制 (RBAC)
  
示例代码:
  from flask_jwt_extended import JWTManager, jwt_required
  
  jwt = JWTManager(app)
  
  @app.route('/api/protected')
  @jwt_required()
  def protected():
      return jsonify({'message': 'Protected resource'})

【2. 请求限流】
  ✓ 防止暴力破解和 DDoS 攻击
  
示例代码:
  from flask_limiter import Limiter
  from flask_limiter.util import get_remote_address
  
  limiter = Limiter(
      app,
      key_func=get_remote_address,
      default_limits=["200 per day", "50 per hour"]
  )
  
  @app.route('/api/prices')
  @limiter.limit("10 per minute")
  def get_prices():
      return jsonify({...})

【3. 输入验证】
  ✓ 验证所有用户输入
  ✓ 使用白名单而非黑名单
  
示例代码:
  from flask import request, abort
  from marshmallow import Schema, fields, ValidationError
  
  class PriceQuerySchema(Schema):
      metal = fields.Str(required=True, 
                        validate=lambda x: x in ['gold', 'silver', 'platinum'])
  
  @app.route('/api/prices')
  def get_prices():
      try:
          data = PriceQuerySchema().load(request.args)
      except ValidationError as e:
          abort(400, str(e))

【4. HTTPS 配置】
  ✓ 强制使用 HTTPS
  ✓ 配置 SSL/TLS 证书
  
Nginx 配置:
  server {
      listen 443 ssl;
      ssl_certificate /path/to/cert.pem;
      ssl_certificate_key /path/to/key.pem;
      ssl_protocols TLSv1.2 TLSv1.3;
  }

【5. 安全响应头】
  ✓ 添加安全相关的 HTTP 头
  
示例代码:
  from flask_talisman import Talisman
  
  Talisman(app, 
           force_https=True,
           strict_transport_security=True,
           content_security_policy={
               'default-src': "'self'"
           })

【6. 日志审计】
  ✓ 记录所有安全相关事件
  ✓ 定期审查日志
  ✓ 实现入侵检测
  
  - 记录失败的登录尝试
  - 记录敏感操作
  - 监控异常访问模式

【7. 数据加密】
  ✓ 敏感数据加密存储
  ✓ 传输层加密 (HTTPS)
  
示例代码:
  from cryptography.fernet import Fernet
  
  key = Fernet.generate_key()
  cipher = Fernet(key)
  
  encrypted = cipher.encrypt(b"sensitive_data")
  decrypted = cipher.decrypt(encrypted)

【8. 定期安全审计】
  ✓ 定期更新依赖包
  ✓ 运行安全扫描工具
  ✓ 代码审查
  
  工具推荐:
    - Bandit (Python 安全扫描)
    - Safety (依赖漏洞检查)
    - OWASP ZAP (Web 应用安全测试)
        """)
    
    def print_report(self):
        """打印安全审计报告"""
        print("\n" + "="*70)
        print("安全问题汇总")
        print("="*70)
        
        if not self.issues:
            print("✓ 未发现严重安全问题")
        else:
            critical = [i for i in self.issues if i['severity'] == 'CRITICAL']
            high = [i for i in self.issues if i['severity'] == 'HIGH']
            medium = [i for i in self.issues if i['severity'] == 'MEDIUM']
            
            print(f"严重: {len(critical)}")
            print(f"高危: {len(high)}")
            print(f"中危: {len(medium)}")
            
            print("\n详细:")
            for issue in self.issues:
                print(f"\n[{issue['severity']}] {issue['issue']}")
                print(f"  建议: {issue['recommendation']}")
                if 'file' in issue:
                    print(f"  文件: {issue['file']}")

def main():
    """主函数"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("="*70)
    print("PreciousInsight 安全审计工具")
    print("="*70)
    
    auditor = SecurityAuditor(project_root)
    
    # 运行所有检查
    auditor.check_env_file_security()
    auditor.check_sql_injection()
    auditor.check_api_security()
    auditor.check_sensitive_data_exposure()
    auditor.check_dependency_security()
    
    # 打印报告
    auditor.print_report()
    
    # 生成加固建议
    auditor.generate_security_recommendations()
    
    print("\n" + "="*70)
    print("审计完成")
    print("="*70)

if __name__ == '__main__':
    main()
