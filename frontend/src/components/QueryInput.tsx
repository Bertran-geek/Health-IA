import { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

interface QueryInputProps {
  onQuery: (question: string) => void;
  loading: boolean;
}

const SUGGESTIONS = [
  "Combien d'enfants vaccinés par région ?",
  "Taux de couverture vaccinale par département",
  "Nombre de cibles par campagne active",
  "Top 10 des ASC les plus performants",
];

export function QueryInput({ onQuery, loading }: QueryInputProps) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !loading) {
      onQuery(question.trim());
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            placeholder="Posez votre question en français ou anglais..."
            className="flex-1 px-4 py-3 bg-white border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-800 placeholder-gray-400 disabled:opacity-50 shadow-sm"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-medium shadow-sm"
          >
            <Send className="w-4 h-4" />
            Analyser
          </button>
        </div>
      </form>

      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <Sparkles className="w-3 h-3" /> Suggestions :
        </span>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setQuestion(s);
              onQuery(s);
            }}
            disabled={loading}
            className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-full text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-40"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
