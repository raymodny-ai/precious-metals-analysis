import os
from datetime import date

class ReportGenerator:
    def __init__(self, template_path=None):
        if not template_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_path = os.path.join(base_dir, 'templates', 'precious_metals_daily_report.md')
        self.template_path = template_path

    def generate_report(self, data):
        if not os.path.exists(self.template_path):
            print(f"Template not found: {self.template_path}")
            return ""
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Fill template
        try:
            report = template.format(
                date=date.today(),
                executive_summary=data.get('executive_summary', 'N/A'),
                current_price_gold=data.get('gold', {}).get('price', 'N/A'),
                change_24h_gold=data.get('gold', {}).get('change', 'N/A'),
                support_gold=data.get('gold', {}).get('support', 'N/A'),
                resistance_gold=data.get('gold', {}).get('resistance', 'N/A'),
                current_price_silver=data.get('silver', {}).get('price', 'N/A'),
                change_24h_silver=data.get('silver', {}).get('change', 'N/A'),
                news_sentiment=data.get('sentiment', {}).get('news', 'N/A'),
                social_sentiment=data.get('sentiment', {}).get('social', 'N/A'),
                investor_sentiment=data.get('sentiment', {}).get('investor', 'N/A'),
                dxy=data.get('macro', {}).get('dxy', 'N/A'),
                treasury_yield=data.get('macro', {}).get('yield', 'N/A'),
                cpi=data.get('macro', {}).get('cpi', 'N/A'),
                mining_output=data.get('supply', {}).get('mining', 'N/A'),
                industrial_demand=data.get('supply', {}).get('industrial', 'N/A'),
                central_bank_buying=data.get('supply', {}).get('central_bank', 'N/A'),
                trend_forecast=data.get('forecast', 'N/A'),
                investment_advice=data.get('advice', 'N/A')
            )
            return report
        except KeyError as e:
            print(f"Missing key in data for report generation: {e}")
            return "Error generating report: Missing data"

    def save_report(self, report_content, output_dir='reports'):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filename = f"report_{date.today()}.md"
        path = os.path.join(output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return path
