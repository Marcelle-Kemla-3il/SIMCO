import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({ error: error.message });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f3f4f6',
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '8px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            maxWidth: '400px',
            textAlign: 'center'
          }}>
            <h2 style={{ color: '#dc2626', marginBottom: '16px' }}>
              Une erreur est survenue
            </h2>
            <p style={{ marginBottom: '20px', color: '#6b7280' }}>
              L'application a rencontré une erreur. Veuillez rafraîchir la page.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                padding: '12px 24px',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer'
              }}
            >
              Rafraîchir
            </button>
            {import.meta.env.MODE === 'development' && this.state.error && (
              <div style={{ marginTop: '20px', textAlign: 'left' }}>
                <details>
                  <summary style={{ cursor: 'pointer', color: '#6b7280' }}>
                    Détails techniques
                  </summary>
                  <pre style={{
                    marginTop: '10px',
                    padding: '10px',
                    backgroundColor: '#fef2f2',
                    borderRadius: '4px',
                    fontSize: '12px',
                    overflow: 'auto',
                    maxHeight: '200px'
                  }}>
                    {this.state.error}
                  </pre>
                </details>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
