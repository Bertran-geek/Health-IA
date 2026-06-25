import { useState } from 'react';
import { QueryResponse } from './types';
import { queryAI } from './api';
import { Header } from './components/Header';
import { LoginScreen } from './components/LoginScreen';
import { QueryInput } from './components/QueryInput';
import { ResultCard } from './components/ResultCard';
import { DataTable } from './components/DataTable';
import { ChartView } from './components/ChartView';
import { TrendBadge } from './components/TrendBadge';

interface HistoryEntry {
  question: string;
  response: QueryResponse;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(
    !!localStorage.getItem('access_token') || !!localStorage.getItem('api_key')
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentResult, setCurrentResult] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const handleQuery = async (question: string) => {
    setLoading(true);
    setError(null);
    setCurrentResult(null);
    try {
      const response = await queryAI({ question, include_chart: true });
      setCurrentResult(response);
      setHistory((prev) => [{ question, response }, ...prev]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (token: string) => {
    localStorage.setItem('access_token', token);
    setAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('api_key');
    setAuthenticated(false);
    setCurrentResult(null);
    setHistory([]);
  };

  if (!authenticated) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-emerald-50">
      <Header onLogout={handleLogout} />

      <main className="max-w-6xl mx-auto px-4 py-6">
        <QueryInput onQuery={handleQuery} loading={loading} />

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="mt-8 flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <p className="text-gray-500 text-sm">Analyse en cours...</p>
          </div>
        )}

        {currentResult && !loading && (
          <div className="mt-6 space-y-6">
            <ResultCard response={currentResult} />

            {currentResult.chart && (
              <ChartView chart={currentResult.chart} />
            )}

            {currentResult.trend && (
              <TrendBadge trend={currentResult.trend} />
            )}

            {currentResult.rows.length > 0 && (
              <DataTable
                columns={currentResult.columns}
                rows={currentResult.rows}
              />
            )}
          </div>
        )}

        {history.length > 1 && (
          <div className="mt-10">
            <h3 className="text-lg font-semibold text-gray-700 mb-3">
              Historique des requêtes
            </h3>
            <div className="space-y-2">
              {history.slice(1).map((entry, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentResult(entry.response)}
                  className="w-full text-left p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all"
                >
                  <span className="text-sm text-gray-600">{entry.question}</span>
                  <span className="ml-2 text-xs text-gray-400">
                    {entry.response.elapsed_ms}ms
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
