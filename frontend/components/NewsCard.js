'use client';

export default function NewsCard({ news }) {
    const getSentimentBorderColor = (sentiment) => {
        switch (sentiment) {
            case 'positive': return 'var(--accent-green)';
            case 'negative': return 'var(--accent-red)';
            default: return 'var(--accent-blue)';
        }
    };

    const formatTime = (time) => {
        if (typeof time === 'string' && time.includes('ago')) return time;
        try {
            const date = new Date(time);
            const now = new Date();
            const diffMs = now - date;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours}h ago`;
            return date.toLocaleDateString();
        } catch {
            return time;
        }
    };

    return (
        <div className="card">
            <div className="card-header">
                <div>
                    <div className="card-title">Latest News</div>
                    <div className="card-subtitle">Precious metals market news with sentiment</div>
                </div>
                <span className="badge badge-green">{news.length} articles</span>
            </div>

            <div className="news-list">
                {news.slice(0, 6).map((item, index) => (
                    <div
                        key={item.id || index}
                        className={`news-item ${item.sentiment || item.sentiment_label || ''}`}
                        style={{
                            borderLeftColor: getSentimentBorderColor(item.sentiment || item.sentiment_label)
                        }}
                    >
                        <div className="news-title">{item.title}</div>
                        <div className="news-meta">
                            <span>{item.source}</span>
                            <span>•</span>
                            <span>{formatTime(item.time)}</span>
                            {(item.sentiment || item.sentiment_label) && (
                                <>
                                    <span>•</span>
                                    <span style={{
                                        color: getSentimentBorderColor(item.sentiment || item.sentiment_label),
                                        textTransform: 'capitalize'
                                    }}>
                                        {item.sentiment || item.sentiment_label}
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {news.length > 6 && (
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                    <button className="btn btn-outline" style={{ width: '100%' }}>
                        View All News ({news.length})
                    </button>
                </div>
            )}
        </div>
    );
}
