"""
邮件推送模块
支持 SMTP 发送邮件通知和报告
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self):
        # 从环境变量加载配置
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'PreciousInsight')
    
    def send_email(self, to_email, subject, body_html, body_text=None, attachments=None):
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱 (str or list)
            subject: 邮件主题
            body_html: HTML 正文
            body_text: 纯文本正文 (可选)
            attachments: 附件列表 [{filename, content}]
        
        Returns:
            bool: 发送是否成功
        """
        if not self.smtp_user or not self.smtp_password:
            print("错误: 邮件配置未完成")
            print("请设置环境变量: SMTP_USER, SMTP_PASSWORD")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email if isinstance(to_email, str) else ', '.join(to_email)
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # 添加纯文本版本
            if body_text:
                part1 = MIMEText(body_text, 'plain', 'utf-8')
                msg.attach(part1)
            
            # 添加 HTML 版本
            part2 = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part2)
            
            # 添加附件
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(attachment['content'])
                    part.add_header('Content-Disposition', 'attachment', 
                                  filename=attachment['filename'])
                    msg.attach(part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✓ 邮件已发送到: {to_email}")
            return True
            
        except Exception as e:
            print(f"✗ 邮件发送失败: {e}")
            return False
    
    def send_price_alert(self, to_email, metal, current_price, threshold, direction):
        """
        发送价格预警
        
        Args:
            to_email: 收件人
            metal: 金属名称 (gold, silver, etc.)
            current_price: 当前价格
            threshold: 阈值
            direction: 'above' or 'below'
        """
        metal_names = {
            'gold': '黄金',
            'silver': '白银',
            'platinum': '铂金',
            'palladium': '钯金'
        }
        
        metal_cn = metal_names.get(metal, metal)
        direction_text = '突破' if direction == 'above' else '跌破'
        
        subject = f"⚠️ {metal_cn}价格预警: {direction_text} ${threshold}"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f8d7da; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .price {{ font-size: 24px; font-weight: bold; color: #721c24; }}
                .footer {{ padding: 10px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 价格预警通知</h2>
            </div>
            <div class="content">
                <p><strong>{metal_cn}</strong> 价格已{direction_text}预警阈值</p>
                <p class="price">当前价格: ${current_price:.2f}</p>
                <p>预警阈值: ${threshold:.2f}</p>
                <p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p>请及时关注市场动态并采取相应措施。</p>
            </div>
            <div class="footer">
                <p>PreciousInsight - 贵金属市场智能分析系统</p>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        价格预警通知
        
        {metal_cn} 价格已{direction_text}预警阈值
        当前价格: ${current_price:.2f}
        预警阈值: ${threshold:.2f}
        时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        请及时关注市场动态并采取相应措施。
        
        PreciousInsight - 贵金属市场智能分析系统
        """
        
        return self.send_email(to_email, subject, html, text)
    
    def send_daily_report(self, to_email, report_path):
        """
        发送每日报告
        
        Args:
            to_email: 收件人
            report_path: 报告文件路径 (.md or .pdf)
        """
        subject = f"📊 贵金属市场日报 - {datetime.now().strftime('%Y-%m-%d')}"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #d4edda; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ padding: 10px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 每日市场报告</h2>
            </div>
            <div class="content">
                <p>尊敬的用户，</p>
                <p>请查收今日的贵金属市场分析报告。</p>
                <p>报告日期: {datetime.now().strftime('%Y年%m月%d日')}</p>
                <p>报告已作为附件发送，请下载查看。</p>
                <hr>
                <p><strong>主要内容包括：</strong></p>
                <ul>
                    <li>价格走势分析</li>
                    <li>市场情绪评估</li>
                    <li>技术指标解读</li>
                    <li>趋势预测与建议</li>
                </ul>
            </div>
            <div class="footer">
                <p>PreciousInsight - 贵金属市场智能分析系统</p>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        每日市场报告
        
        尊敬的用户，
        
        请查收今日的贵金属市场分析报告。
        报告日期: {datetime.now().strftime('%Y年%m月%d日')}
        
        报告已作为附件发送，请下载查看。
        
        主要内容包括：
        - 价格走势分析
        - 市场情绪评估
        - 技术指标解读
        - 趋势预测与建议
        
        PreciousInsight - 贵金属市场智能分析系统
        """
        
        # 读取报告文件
        attachments = []
        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                attachments.append({
                    'filename': os.path.basename(report_path),
                    'content': f.read()
                })
        
        return self.send_email(to_email, subject, html, text, attachments)

def test_email_notifier():
    """测试邮件通知功能"""
    print("="*60)
    print("邮件通知模块测试")
    print("="*60)
    
    notifier = EmailNotifier()
    
    if not notifier.smtp_user or not notifier.smtp_password:
        print("\n⚠️  邮件配置未完成")
        print("请在 .env 文件中设置:")
        print("  SMTP_USER=your_email@gmail.com")
        print("  SMTP_PASSWORD=your_app_password")
        print("  FROM_EMAIL=your_email@gmail.com")
        print("\n提示: 使用 Gmail 需要生成应用专用密码")
        return
    
    # 测试邮件
    test_recipient = input("请输入测试邮件地址: ").strip()
    
    if not test_recipient:
        print("未输入邮件地址，跳过测试")
        return
    
    print("\n发送测试邮件...")
    success = notifier.send_price_alert(
        test_recipient,
        'gold',
        2050.00,
        2040.00,
        'above'
    )
    
    if success:
        print("✓ 测试成功！请检查您的邮箱")
    else:
        print("✗ 测试失败，请检查配置")

if __name__ == '__main__':
    test_email_notifier()
