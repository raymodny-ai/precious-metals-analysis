'use client';

export default function ETFFlowCard({ flows }) {
    const formatCurrency = (num) => {
        if (num === undefined || num === null) return '-';
        const absNum = Math.abs(num);
        if (absNum >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
        if (absNum >= 1e6) return `$${(num / 1e6).toFixed(1)}M`;
        if (absNum >= 1e3) return `$${(num / 1e3).toFixed(1)}K`;
        return `$${num.toFixed(0)}`;
    };

    const isPositive = (val) => val >= 0;

    const etfList = Object.entries(flows || {}).map(([symbol, data]) => ({
        symbol,
        ...data
    }));

    return (
        <div className="card">
            <div className="card-header">
                <div>
                    <div className="card-title">ETF Fund Flows</div>
                    <div className="card-subtitle">Real-time money flow tracking</div>
                </div>
                <span style={{ fontSize: '24px' }}>💰</span>
            </div>

            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ETF</th>
                            <th style={{ textAlign: 'right' }}>Net Flow</th>
                            <th style={{ textAlign: 'right' }}>5D Flow</th>
                            <th style={{ textAlign: 'right' }}>AUM</th>
                        </tr>
                    </thead>
                    <tbody>
                        {etfList.map((etf) => (
                            <tr key={etf.symbol}>
                                <td>
                                    <span style={{ fontWeight: 600 }}>{etf.symbol}</span>
                                </td>
                                <td style={{
                                    textAlign: 'right',
                                    color: isPositive(etf.net_flow) ? 'var(--accent-green)' : 'var(--accent-red)'
                                }}>
                                    {isPositive(etf.net_flow) ? '+' : ''}{formatCurrency(etf.net_flow)}
                                </td>
                                <td style={{
                                    textAlign: 'right',
                                    color: isPositive(etf.flow_5d) ? 'var(--accent-green)' : 'var(--accent-red)'
                                }}>
                                    {isPositive(etf.flow_5d) ? '+' : ''}{formatCurrency(etf.flow_5d)}
                                </td>
                                <td style={{ textAlign: 'right' }}>
                                    {formatCurrency(etf.aum)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Flow Summary */}
            <div style={{
                marginTop: '16px',
                padding: '12px',
                background: 'var(--bg-primary)',
                borderRadius: 'var(--radius-md)'
            }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.875rem'
                }}>
                    <span style={{ color: 'var(--text-muted)' }}>Total Net Inflows:</span>
                    <span style={{
                        fontWeight: 600,
                        color: etfList.reduce((sum, etf) => sum + (etf.net_flow || 0), 0) >= 0
                            ? 'var(--accent-green)'
                            : 'var(--accent-red)'
                    }}>
                        {formatCurrency(etfList.reduce((sum, etf) => sum + (etf.net_flow || 0), 0))}
                    </span>
                </div>
            </div>
        </div>
    );
}
