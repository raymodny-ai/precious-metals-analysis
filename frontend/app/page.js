'use client';

import { useState, useEffect } from 'react';
import PriceCard from '../components/PriceCard';
import SentimentCard from '../components/SentimentCard';
import NewsCard from '../components/NewsCard';
import ETFFlowCard from '../components/ETFFlowCard';
import Header from '../components/Header';

// Mock data for demo (replace with API calls)
const mockPrices = {
    GLD: { price: 185.42, change: 1.23, change_pct: 0.67, volume: 8456000 },
    SLV: { price: 21.85, change: -0.15, change_pct: -0.68, volume: 12340000 },
    IAU: { price: 37.89, change: 0.28, change_pct: 0.74, volume: 3210000 },
};

const mockSentiment = {
    GLD: {
        current_sentiment: 0.35,
        sentiment_label: 'positive',
        trend: 'improving',
        bullish_ratio: 0.58,
        bearish_ratio: 0.22,
        heat_index: 72,
        news_volume_24h: 47
    }
};

const mockNews = [
    {
        id: 1,
        title: 'Gold Prices Surge as Fed Signals Potential Rate Pause in 2024',
        source: 'Financial Times',
        time: '2h ago',
        sentiment: 'positive'
    },
    {
        id: 2,
        title: 'Central Banks Continue Gold Buying Streak in Q4',
        source: 'Bloomberg',
        time: '4h ago',
        sentiment: 'positive'
    },
    {
        id: 3,
        title: 'Dollar Weakness Supports Precious Metals Rally',
        source: 'Reuters',
        time: '6h ago',
        sentiment: 'positive'
    },
    {
        id: 4,
        title: 'Silver Prices Dip on Profit Taking After Recent Gains',
        source: 'CNBC',
        time: '8h ago',
        sentiment: 'negative'
    }
];

const mockETFFlows = {
    GLD: { net_flow: 245000000, flow_5d: 890000000, aum: 56700000000 },
    SLV: { net_flow: -45000000, flow_5d: 120000000, aum: 12300000000 },
};

export default function Dashboard() {
    const [prices, setPrices] = useState(mockPrices);
    const [sentiment, setSentiment] = useState(mockSentiment);
    const [news, setNews] = useState(mockNews);
    const [etfFlows, setETFFlows] = useState(mockETFFlows);
    const [loading, setLoading] = useState(false);
    const [selectedSymbol, setSelectedSymbol] = useState('GLD');

    // Fetch data from API
    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch prices
            const pricesRes = await fetch('/api/v1/prices/latest');
            if (pricesRes.ok) {
                const pricesData = await pricesRes.json();
                if (pricesData.success) {
                    setPrices(pricesData.data);
                }
            }

            // Fetch sentiment
            const sentimentRes = await fetch(`/api/v1/sentiment/dashboard/${selectedSymbol}`);
            if (sentimentRes.ok) {
                const sentimentData = await sentimentRes.json();
                if (sentimentData.success) {
                    setSentiment({ ...sentiment, [selectedSymbol]: sentimentData.data });
                }
            }

            // Fetch news
            const newsRes = await fetch('/api/v1/news?limit=10');
            if (newsRes.ok) {
                const newsData = await newsRes.json();
                if (newsData.success && newsData.data) {
                    setNews(newsData.data);
                }
            }
        } catch (error) {
            console.error('Error fetching data:', error);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchData();
        // Refresh every 60 seconds
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, [selectedSymbol]);

    return (
        <div>
            <Header />

            <main className="container" style={{ paddingTop: '24px', paddingBottom: '48px' }}>
                {/* Symbol Selector */}
                <div style={{ marginBottom: '24px', display: 'flex', gap: '12px' }}>
                    {['GLD', 'SLV', 'IAU'].map(symbol => (
                        <button
                            key={symbol}
                            className={`btn ${selectedSymbol === symbol ? 'btn-primary' : 'btn-outline'}`}
                            onClick={() => setSelectedSymbol(symbol)}
                        >
                            {symbol}
                        </button>
                    ))}
                </div>

                {/* Main Dashboard Grid */}
                <div className="dashboard-grid">
                    {/* Price Cards */}
                    <PriceCard
                        symbol="GLD"
                        name="Gold ETF"
                        data={prices['GLD']}
                        isActive={selectedSymbol === 'GLD'}
                    />
                    <PriceCard
                        symbol="SLV"
                        name="Silver ETF"
                        data={prices['SLV']}
                        isActive={selectedSymbol === 'SLV'}
                    />
                    <PriceCard
                        symbol="IAU"
                        name="iShares Gold"
                        data={prices['IAU']}
                        isActive={selectedSymbol === 'IAU'}
                    />
                </div>

                {/* Second Row: Sentiment + ETF Flows */}
                <div className="dashboard-grid" style={{ marginTop: '24px' }}>
                    <SentimentCard
                        symbol={selectedSymbol}
                        data={sentiment[selectedSymbol] || mockSentiment.GLD}
                    />
                    <ETFFlowCard flows={etfFlows} />
                </div>

                {/* Third Row: News */}
                <div style={{ marginTop: '24px' }}>
                    <NewsCard news={news} />
                </div>
            </main>
        </div>
    );
}
