"""
统一通知管理器
整合所有通知渠道（邮件、Telegram、Discord、Webhook）
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NotificationSystem.email_notifier import EmailNotifier
from NotificationSystem.telegram_notifier import TelegramNotifier

class NotificationManager:
    """统一通知管理器"""
    
    def __init__(self):
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        
        # 从环境变量加载通知配置
        self.enabled_channels = os.getenv('NOTIFICATION_CHANNELS', 'email,telegram').split(',')
        self.alert_recipients = os.getenv('ALERT_RECIPIENTS', '').split(',')
    
    def send_price_alert(self, metal, current_price, threshold, direction):
        """
        发送价格预警（所有启用的渠道）
        
        Args:
            metal: 金属类型
            current_price: 当前价格
            threshold: 阈值
            direction: 'above' or 'below'
        """
        results = {}
        
        # 邮件通知
        if 'email' in self.enabled_channels:
            for recipient in self.alert_recipients:
                if recipient and '@' in recipient:
                    success = self.email_notifier.send_price_alert(
                        recipient, metal, current_price, threshold, direction
                    )
                    results['email'] = success
        
        # Telegram 通知
        if 'telegram' in self.enabled_channels:
            success = self.telegram_notifier.send_price_alert(
                metal, current_price, threshold, direction
            )
            results['telegram'] = success
        
        return results
    
    def send_daily_report(self, report_path=None, summary_data=None):
        """
        发送每日报告
        
        Args:
            report_path: 报告文件路径 (用于邮件附件)
            summary_data: 摘要数据 (用于 Telegram)
        """
        results = {}
        
        # 邮件报告
        if 'email' in self.enabled_channels and report_path:
            for recipient in self.alert_recipients:
                if recipient and '@' in recipient:
                    success = self.email_notifier.send_daily_report(
                        recipient, report_path
                    )
                    results['email'] = success
        
        # Telegram 摘要
        if 'telegram' in self.enabled_channels and summary_data:
            success = self.telegram_notifier.send_daily_summary(summary_data)
            results['telegram'] = success
        
        return results
    
    def send_custom_notification(self, title, message, channels=None):
        """
        发送自定义通知
        
        Args:
            title: 通知标题
            message: 通知内容
            channels: 指定渠道列表，None 则使用所有启用的渠道
        """
        if channels is None:
            channels = self.enabled_channels
        
        results = {}
        
        if 'telegram' in channels:
            formatted_message = f"<b>{title}</b>\n\n{message}"
            results['telegram'] = self.telegram_notifier.send_message(formatted_message)
        
        # 可以添加更多渠道
        
        return results
    
    def get_enabled_channels(self):
        """获取已启用的通知渠道"""
        return self.enabled_channels
    
    def test_all_channels(self):
        """测试所有通知渠道"""
        print("="*60)
        print("通知系统测试")
        print("="*60)
        
        print(f"\n已启用的渠道: {', '.join(self.enabled_channels)}")
        
        # 测试价格预警
        print("\n【测试 1】价格预警通知")
        results = self.send_price_alert('gold', 2050.00, 2040.00, 'above')
        
        for channel, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"  {channel}: {status}")
        
        # 测试摘要
        print("\n【测试 2】每日摘要")
        summary_data = {
            'gold': {'price': 2050.00, 'change': 1.2},
            'silver': {'price': 24.50, 'change': -0.8},
            'sentiment': '正面',
            'forecast': '短期看涨'
        }
        results = self.send_daily_report(summary_data=summary_data)
        
        for channel, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"  {channel}: {status}")

def main():
    """主函数"""
    manager = NotificationManager()
    
    print("PreciousInsight 通知系统")
    print("="*60)
    print("\n选项:")
    print("1. 测试所有通知渠道")
    print("2. 发送测试价格预警")
    print("3. 发送测试每日报告")
    print("4. 退出")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == '1':
        manager.test_all_channels()
    elif choice == '2':
        manager.send_price_alert('gold', 2050.00, 2040.00, 'above')
        print("✓ 价格预警已发送")
    elif choice == '3':
        summary = {
            'gold': {'price': 2050.00, 'change': 1.2},
            'silver': {'price': 24.50, 'change': -0.8},
            'sentiment': '正面',
            'forecast': '短期看涨'
        }
        manager.send_daily_report(summary_data=summary)
        print("✓ 每日报告已发送")
    else:
        print("再见！")

if __name__ == '__main__':
    main()
