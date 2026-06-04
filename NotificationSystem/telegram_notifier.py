"""
Telegram 推送模块
通过 Telegram Bot 发送通知
"""
import os
import requests
from datetime import datetime

class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message, parse_mode='HTML'):
        """
        发送消息
        
        Args:
            message: 消息内容
            parse_mode: 'HTML' or 'Markdown'
        
        Returns:
            bool: 发送是否成功
        """
        if not self.bot_token or not self.chat_id:
            print("错误: Telegram 配置未完成")
            print("请设置环境变量: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
            return False
        
        try:
            url = f"{self.api_base}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            print(f"✓ Telegram 消息已发送")
            return True
            
        except Exception as e:
            print(f"✗ Telegram 消息发送失败: {e}")
            return False
    
    def send_price_alert(self, metal, current_price, threshold, direction):
        """发送价格预警"""
        metal_names = {
            'gold': '黄金 🟡',
            'silver': '白银 ⚪',
            'platinum': '铂金 ⚫',
            'palladium': '钯金 🔘'
        }
        
        metal_display = metal_names.get(metal, metal)
        direction_text = '突破 📈' if direction == 'above' else '跌破 📉'
        
        message = f"""
<b>🚨 价格预警通知</b>

{metal_display} 价格已{direction_text}预警阈值

<b>当前价格:</b> ${current_price:.2f}
<b>预警阈值:</b> ${threshold:.2f}
<b>时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请及时关注市场动态 📊
        """
        
        return self.send_message(message.strip())
    
    def send_daily_summary(self, summary_data):
        """
        发送每日摘要
        
        Args:
            summary_data: dict with price info
        """
        message = f"""
<b>📊 每日市场摘要</b>
<i>{datetime.now().strftime('%Y年%m月%d日')}</i>

<b>黄金 🟡</b>
价格: ${summary_data.get('gold', {}).get('price', 'N/A')}
涨跌: {summary_data.get('gold', {}).get('change', 'N/A')}%

<b>白银 ⚪</b>
价格: ${summary_data.get('silver', {}).get('price', 'N/A')}
涨跌: {summary_data.get('silver', {}).get('change', 'N/A')}%

<b>市场情绪:</b> {summary_data.get('sentiment', 'N/A')}
<b>趋势预测:</b> {summary_data.get('forecast', 'N/A')}

---
<i>PreciousInsight 自动推送</i>
        """
        
        return self.send_message(message.strip())

def test_telegram_notifier():
    """测试 Telegram 通知"""
    print("="*60)
    print("Telegram 通知模块测试")
    print("="*60)
    
    notifier = TelegramNotifier()
    
    if not notifier.bot_token or not notifier.chat_id:
        print("\n⚠️  Telegram 配置未完成")
        print("请在 .env 文件中设置:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("\n获取 Bot Token:")
        print("1. 在 Telegram 中搜索 @BotFather")
        print("2. 发送 /newbot 创建新bot")
        print("3. 获取 token")
        print("\n获取 Chat ID:")
        print("1. 与你的 bot 发送消息")
        print("2. 访问: https://api.telegram.org/bot<YourBOTToken>/getUpdates")
        return
    
    print("\n发送测试消息...")
    success = notifier.send_price_alert('gold', 2050.00, 2040.00, 'above')
    
    if success:
        print("✓ 测试成功！请检查您的 Telegram")
    else:
        print("✗ 测试失败，请检查配置")

if __name__ == '__main__':
    test_telegram_notifier()
