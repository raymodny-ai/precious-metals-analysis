'use client';

export default function SentimentCard({ symbol, data }) {
    const getSentimentColor = (label) => {
        switch (label) {
            case 'positive': return 'var(--accent-green)';
            case 'negative': return 'var(--accent-red)';
            default: return 'var(--text-muted)';
        }
    };

    const getTrendIcon = (trend) => {
        switch (trend) {
            case 'improving': return '📈';
            case 'declining': return '📉';
            default: return '➡️';
        }
    };

    const positive = (data?.bullish_ratio || 0) * 100;
    const negative = (data?.bearish_ratio || 0) * 100;
    const neutral = 100 - positive - negative;

    return (
        <div className="card">
            <div className="card-header">
                <div>
                    <div className="card-title">Sentiment Analysis</div>
                    <div className="card-subtitle">{symbol} - Market Sentiment</div>
                </div>
                <span style={{ fontSize: '24px' }}>
                    {getTrendIcon(data?.trend)}
                </span>
            </div>

            {/* Sentiment Index */}
            <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 500 }}>Sentiment Index</span>
                    <span style={{
                        fontWeight: 700,
                        fontSize: '1.25rem',
                        color: getSentimentColor(data?.sentiment_label)
                    }}>
                        {((data?.current_sentiment || 0) * 50 + 50).toFixed(0)}
                    </span>
                </div>
                <div style={{
                    height: '8px',
                    background: 'var(--bg-primary)',
                    borderRadius: '4px',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        width: `${(data?.current_sentiment || 0) * 50 + 50}%`,
                        height: '100%',
                        background: getSentimentColor(data?.sentiment_label),
                        borderRadius: '4px',
                        transition: 'width 0.3s ease'
                    }} />
                </div>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    marginTop: '4px'
                }}>
                    <span>Bearish</span>
                    <span>Neutral</span>
                    <span>Bullish</span>
                </div>
            </div>

            {/* Sentiment Distribution */}
            <div className="sentiment-indicator" style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '0.875rem', marginBottom: '8px' }}>Distribution</div>
                <div className="sentiment-bar">
                    <div className="positive" style={{ width: `${positive}%` }} />
                    <div className="neutral" style={{ width: `${neutral}%` }} />
                    <div className="negative" style={{ width: `${negative}%` }} />
                </div>
                <div className="sentiment-labels">
                    <span style={{ color: 'var(--accent-green)' }}>Bullish {positive.toFixed(0)}%</span>
                    <span>Neutral {neutral.toFixed(0)}%</span>
                    <span style={{ color: 'var(--accent-red)' }}>Bearish {negative.toFixed(0)}%</span>
                </div>
            </div>

            {/* Stats */}
            <div className="stats-grid">
                <div className="stat-item">
                    <div className="stat-value">{data?.news_volume_24h || 0}</div>
                    <div className="stat-label">News (24h)</div>
                </div>
                <div className="stat-item">
                    <div className="stat-value" style={{ color: 'var(--accent-gold)' }}>
                        {data?.heat_index?.toFixed(0) || 0}
                    </div>
                    <div className="stat-label">Heat Index</div>
                </div>
                <div className="stat-item">
                    <div className="stat-value" style={{
                        color: getSentimentColor(data?.sentiment_label),
                        textTransform: 'capitalize'
                    }}>
                        {data?.trend || 'stable'}
                    </div>
                    <div className="stat-label">Trend</div>
                </div>
            </div>
        </div>
    );
}
