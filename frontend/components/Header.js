'use client';

export default function Header() {
    return (
        <header className="header">
            <div className="container">
                <div className="header-content">
                    <div className="logo">
                        <span style={{ fontSize: '24px' }}>⚜️</span>
                        <h1>Precious Metals Dashboard</h1>
                    </div>

                    <nav className="nav-links">
                        <a href="/" className="nav-link active">Dashboard</a>
                        <a href="/sentiment" className="nav-link">Sentiment</a>
                        <a href="/predictions" className="nav-link">Predictions</a>
                        <a href="/etf-flows" className="nav-link">ETF Flows</a>
                    </nav>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className="badge badge-green">Live</span>
                        <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                            Last updated: {new Date().toLocaleTimeString()}
                        </span>
                    </div>
                </div>
            </div>
        </header>
    );
}
