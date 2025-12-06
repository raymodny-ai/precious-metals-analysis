'use client';

export default function PriceCard({ symbol, name, data, isActive }) {
    const isPositive = data?.change_pct >= 0;

    const formatNumber = (num, decimals = 2) => {
        if (num === undefined || num === null) return '-';
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    };

    const formatVolume = (num) => {
        if (num === undefined || num === null) return '-';
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toString();
    };

    return (
        <div
            className="card"
            style={{
                borderColor: isActive ? 'var(--accent-gold)' : 'var(--border-color)',
                borderWidth: isActive ? '2px' : '1px'
            }}
        >
            <div className="card-header">
                <div>
                    <div className="card-title">{symbol}</div>
                    <div className="card-subtitle">{name}</div>
                </div>
                <span className={`badge ${symbol.includes('SLV') ? '' : 'badge-gold'}`} style={{
                    background: symbol.includes('SLV') ? 'rgba(160, 174, 192, 0.2)' : undefined,
                    color: symbol.includes('SLV') ? 'var(--accent-silver)' : undefined
                }}>
                    {symbol.includes('SLV') ? 'Silver' : 'Gold'}
                </span>
            </div>

            <div className="price-display">
                <span className="price-value">
                    ${formatNumber(data?.price)}
                </span>
                <span className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? '+' : ''}{formatNumber(data?.change_pct)}%
                </span>
            </div>

            <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Change</div>
                    <div style={{ fontWeight: 600, color: isPositive ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {isPositive ? '+' : ''}${formatNumber(data?.change)}
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Volume</div>
                    <div style={{ fontWeight: 600 }}>
                        {formatVolume(data?.volume)}
                    </div>
                </div>
            </div>
        </div>
    );
}
