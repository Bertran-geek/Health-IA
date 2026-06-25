import { QueryResponse } from '../types';
import { Brain, Clock, Database, Zap } from 'lucide-react';

interface ResultCardProps {
  response: QueryResponse;
}

export function ResultCard({ response }: ResultCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-5">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
            <Brain className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
              {response.answer}
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-100 px-5 py-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          {response.elapsed_ms} ms
        </span>
        <span className="flex items-center gap-1">
          <Database className="w-3.5 h-3.5" />
          {response.row_count} ligne(s)
        </span>
        {response.cached && (
          <span className="flex items-center gap-1 text-amber-600">
            <Zap className="w-3.5 h-3.5" />
            Cache
          </span>
        )}
        <span className="ml-auto font-mono text-gray-400 bg-gray-50 px-2 py-0.5 rounded text-[11px] max-w-full truncate">
          {response.sql}
        </span>
      </div>
    </div>
  );
}
