"""
美股数据采集客户端
使用 yfinance 获取贵金属相关股票数据
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class YFinanceStockClient:
    """yfinance 股票数据客户端"""
    
    # 贵金属相关股票列表
    PRECIOUS_METAL_ETFS = ['GLD', 'SLV', 'GDX', 'GDXJ', 'PPLT', 'PALL']
    MINING_STOCKS = ['NEM', 'GOLD', 'AEM', 'KGC', 'WPM', 'FNV', 'RGLD', 'AU']
    INDICES = ['^GSPC', '^DJI', 'DX-Y.NYB']  # S&P500, Dow Jones, USD Index
    
    def __init__(self):
        self.all_symbols = self.PRECIOUS_METAL_ETFS + self.MINING_STOCKS + self.INDICES
    
    def get_current_price(self, symbol):
        """
        获取当前价格
        
        Args:
            symbol: 股票代码 (e.g., 'GLD')
        
        Returns:
            dict: 价格数据
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
                'change': info.get('currentPrice', 0) - info.get('previousClose', 0),
                'change_percent': ((info.get('currentPrice', 0) - info.get('previousClose', 0)) / info.get('previousClose', 1)) * 100 if info.get('previousClose') else 0,
                'volume': info.get('volume'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 价格失败: {e}")
            return None
    
    def get_historical_data(self, symbol, period='1mo', interval='1d'):
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            period: 时间周期 ('1d', '5d', '1mo', '3mo', '1y', '5y')
            interval: 数据间隔 ('1m', '5m', '1h', '1d', '1wk', '1mo')
        
        Returns:
            DataFrame: 历史价格数据
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"未获取到 {symbol} 的历史数据")
                return None
            
            hist['symbol'] = symbol
            return hist
        except Exception as e:
            logger.error(f"获取 {symbol} 历史数据失败: {e}")
            return None
    
    def get_fundamentals(self, symbol):
        """
        获取基本面数据
        
        Returns:
            dict: 基本面信息
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName') or info.get('shortName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'eps': info.get('trailingEps'),
                'revenue': info.get('totalRevenue'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'website': info.get('website'),
                'description': info.get('longBusinessSummary')
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 基本面数据失败: {e}")
            return None
    
    def get_all_current_prices(self):
        """
        批量获取所有监控股票的当前价格
        
        Returns:
            list: 所有股票价格数据
        """
        results = []
        
        for symbol in self.all_symbols:
            price_data = self.get_current_price(symbol)
            if price_data:
                results.append(price_data)
        
        return results
    
    def get_category(self, symbol):
        """获取股票分类"""
        if symbol in self.PRECIOUS_METAL_ETFS:
            return 'ETF'
        elif symbol in self.MINING_STOCKS:
            return 'Mining'
        elif symbol in self.INDICES:
            return 'Index'
        else:
            return 'Other'
    
    def calculate_correlation_with_gold(self, symbol, gold_symbol='GLD', period='3mo'):
        """
        计算与金价的相关系数
        
        Args:
            symbol: 目标股票代码
            gold_symbol: 黄金ETF代码（默认GLD）
            period: 计算周期
        
        Returns:
            float: 相关系数 (-1 到 1)
        """
        try:
            # 获取两个标的的历史数据
            stock_hist = self.get_historical_data(symbol, period=period)
            gold_hist = self.get_historical_data(gold_symbol, period=period)
            
            if stock_hist is None or gold_hist is None:
                return None
            
            # 对齐日期并计算相关系数
            merged = pd.merge(
                stock_hist[['Close']].rename(columns={'Close': 'stock'}),
                gold_hist[['Close']].rename(columns={'Close': 'gold'}),
                left_index=True,
                right_index=True,
                how='inner'
            )
            
            if len(merged) < 10:  # 至少需要10个数据点
                return None
            
            correlation = merged['stock'].corr(merged['gold'])
            return round(correlation, 4)
            
        except Exception as e:
            logger.error(f"计算 {symbol} 与金价相关性失败: {e}")
            return None
    
    def screen_stocks(self, criteria):
        """
        根据条件筛选股票
        
        Args:
            criteria: dict with screening criteria
                - min_correlation: 最小相关系数
                - min_volume: 最小成交量
                - max_pe: 最大PE比率
                - category: 股票类别
        
        Returns:
            list: 符合条件的股票
        """
        results = []
        
        symbols_to_check = self.all_symbols
        if criteria.get('category'):
            if criteria['category'] == 'ETF':
                symbols_to_check = self.PRECIOUS_METAL_ETFS
            elif criteria['category'] == 'Mining':
                symbols_to_check = self.MINING_STOCKS
            elif criteria['category'] == 'Index':
                symbols_to_check = self.INDICES
        
        for symbol in symbols_to_check:
            price_data = self.get_current_price(symbol)
            
            if not price_data:
                continue
            
            # 应用筛选条件
            if criteria.get('min_volume') and price_data.get('volume', 0) < criteria['min_volume']:
                continue
            
            if criteria.get('max_pe') and price_data.get('pe_ratio'):
                if price_data['pe_ratio'] > criteria['max_pe']:
                    continue
            
            if criteria.get('min_correlation'):
                corr = self.calculate_correlation_with_gold(symbol)
                if corr is None or corr < criteria['min_correlation']:
                    continue
                price_data['gold_correlation'] = corr
            
            results.append(price_data)
        
        # 按照特定字段排序
        if criteria.get('sort_by') == 'correlation':
            results.sort(key=lambda x: x.get('gold_correlation', 0), reverse=True)
        elif criteria.get('sort_by') == 'change_percent':
            results.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
        elif criteria.get('sort_by') == 'volume':
            results.sort(key=lambda x: x.get('volume', 0), reverse=True)
        
        return results

def demo():
    """演示功能"""
    print("="*60)
    print("yfinance 股票数据采集演示")
    print("="*60)
    
    client = YFinanceStockClient()
    
    # 1. 获取GLD当前价格
    print("\n【1】获取 GLD (黄金ETF) 当前价格:")
    gld_price = client.get_current_price('GLD')
    if gld_price:
        print(f"  价格: ${gld_price['price']:.2f}")
        print(f"  涨跌: {gld_price['change_percent']:+.2f}%")
        print(f"  成交量: {gld_price['volume']:,}")
    
    # 2. 获取NEM基本面
    print("\n【2】获取 NEM (纽蒙特矿业) 基本面:")
    nem_info = client.get_fundamentals('NEM')
    if nem_info:
        print(f"  公司: {nem_info['company_name']}")
        print(f"  行业: {nem_info['sector']}")
        print(f"  市值: ${nem_info['market_cap']/1e9:.1f}B")
        print(f"  PE比率: {nem_info['pe_ratio']:.2f}" if nem_info['pe_ratio'] else "  PE比率: N/A")
    
    # 3. 计算相关性
    print("\n【3】计算 NEM 与 GLD 的相关性:")
    correlation = client.calculate_correlation_with_gold('NEM')
    if correlation is not None:
        print(f"  相关系数: {correlation:.4f}")
        if correlation > 0.7:
            print("  ✓ 高度正相关")
        elif correlation > 0.3:
            print("  ✓ 中度正相关")
    
    # 4. 筛选高相关股票
    print("\n【4】筛选与金价高度相关的股票:")
    criteria = {
        'min_correlation': 0.5,
        'category': 'Mining',
        'sort_by': 'correlation'
    }
    filtered = client.screen_stocks(criteria)
    print(f"  找到 {len(filtered)} 只高相关股票:")
    for stock in filtered[:3]:  # 显示前3个
        print(f"    {stock['symbol']}: 相关性 {stock.get('gold_correlation', 0):.2f}")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    demo()
