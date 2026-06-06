/**
 * PatternTester (UI-3, UI-1 §6) — "does this actually work?". Runs a sample sentence through the REAL recognizer
 * (POST /nlu/recognize — the same path production uses, no JS re-implementation) and shows what was recognized and
 * which values were filled, so the author validates phrasings by example.
 */

import { useState } from 'react';
import { Play, CheckCircle2, XCircle } from 'lucide-react';
import apiClient from '@/utils/apiClient';
import type { RecognizeResponse } from '@/types';

interface PatternTesterProps {
  /** The intent this method should produce, e.g. "timer.set" — used to show a match/no-match badge. */
  expectedIntent?: string;
  placeholder?: string;
}

export default function PatternTester({ expectedIntent, placeholder }: PatternTesterProps) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RecognizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (): Promise<void> => {
    if (!text.trim()) return;
    setBusy(true); setResult(null); setError(null);
    try {
      setResult(await apiClient.recognizeText(text.trim()));
    } catch (e) {
      // 422 = nothing recognized; surface it plainly.
      setError(e instanceof Error ? e.message : 'Recognition failed');
    } finally {
      setBusy(false);
    }
  };

  const entities = result?.entities ?? {};
  const matched = result && expectedIntent ? result.name === expectedIntent : undefined;

  return (
    <div className="border rounded-xl p-3 bg-blue-50/40">
      <div className="flex items-center gap-2">
        <input
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder={placeholder ?? 'Type something a user might say…'}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void run(); }}
        />
        <button
          type="button"
          className="inline-flex items-center gap-1 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          onClick={() => void run()} disabled={busy || !text.trim()}
        >
          <Play className="w-4 h-4" /> Test
        </button>
      </div>

      {error && <div className="mt-2 text-sm text-amber-700">{error}</div>}

      {result && (
        <div className="mt-2 text-sm">
          <div className="flex items-center gap-2">
            {matched === true && <CheckCircle2 className="w-4 h-4 text-green-600" />}
            {matched === false && <XCircle className="w-4 h-4 text-red-600" />}
            <span>
              Recognized <b>{result.name}</b>
              {typeof result.confidence === 'number' && (
                <span className="text-gray-500"> ({Math.round(result.confidence * 100)}%)</span>
              )}
              {matched === false && expectedIntent && (
                <span className="text-red-600"> — expected {expectedIntent}</span>
              )}
            </span>
          </div>
          {Object.keys(entities).length > 0 && (
            <div className="mt-1 text-gray-700">
              Values:{' '}
              {Object.entries(entities).map(([k, v]) => (
                <span key={k} className="inline-block mr-2">
                  <span className="font-mono text-gray-500">{k}</span>=<b>{String(v)}</b>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
