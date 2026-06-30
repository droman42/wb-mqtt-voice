import { Plus, Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ConflictBadge } from '@/components/analysis';
import type { ConflictReport } from '@/types';

interface LemmasEditorProps {
  value: string[];
  onChange: (lemmas: string[]) => void;
  disabled?: boolean;
  tokenPatterns?: Array<Array<Record<string, any>>>;
  slotPatterns?: Record<string, Array<Array<Record<string, any>>>>;
  onAutoSync?: () => void;
  showSyncWarning?: boolean;
  conflicts?: ConflictReport[];
}

export default function LemmasEditor({
  value = [],
  onChange,
  disabled = false,
  tokenPatterns = [],
  slotPatterns = {},
  onAutoSync,
  showSyncWarning = false,
  conflicts = []
}: LemmasEditorProps) {
  const { t } = useTranslation(['donations', 'common']);
  const [newLemma, setNewLemma] = useState('');
  
  const addLemma = (): void => {
    if (newLemma.trim() && !value.includes(newLemma.trim())) {
      onChange([...value, newLemma.trim()]);
      setNewLemma('');
    }
  };

  const removeLemma = (index: number): void => {
    onChange(value.filter((_, i) => i !== index));
  };

  const updateLemma = (index: number, newValue: string): void => {
    const updated = [...value];
    updated[index] = newValue;
    onChange(updated);
  };

  const handleKeyPress = (e: React.KeyboardEvent): void => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addLemma();
    }
  };

  // Extract suggested lemmas from token patterns and slot patterns.
  // UI-14 (E5): memoized — this nested-loop scan ran on every render before.
  const suggestedLemmas = useMemo((): string[] => {
    const suggested: Set<string> = new Set();

    const collect = (token: Record<string, any>): void => {
      if (token.LEMMA) {
        if (typeof token.LEMMA === 'string') {
          suggested.add(token.LEMMA);
        } else if (token.LEMMA.IN && Array.isArray(token.LEMMA.IN)) {
          token.LEMMA.IN.forEach((lemma: string) => suggested.add(lemma));
        }
      }
    };

    tokenPatterns.forEach(pattern => pattern.forEach(collect));
    Object.values(slotPatterns).forEach(slotPatternArray =>
      slotPatternArray.forEach(pattern => pattern.forEach(collect)));

    // Filter out lemmas that are already added
    return Array.from(suggested).filter(lemma => !value.includes(lemma));
  }, [tokenPatterns, slotPatterns, value]);

  // Conflicts that involve a specific lemma.
  // UI-14 (E5): precompute the lemma→conflicts map once per change instead of filtering all
  // conflicts inside every row's render.
  const conflictsByLemma = useMemo(() => {
    const matches = (lemma: string): ConflictReport[] => conflicts.filter(conflict => {
      const signals = conflict.signals;
      if (signals.shared_lemmas && Array.isArray(signals.shared_lemmas)) {
        return signals.shared_lemmas.includes(lemma);
      }
      if (signals.shared_phrases && Array.isArray(signals.shared_phrases)) {
        return signals.shared_phrases.some((phrase: string) =>
          phrase.toLowerCase().includes(lemma.toLowerCase()));
      }
      return false;
    });
    const map: Record<string, ConflictReport[]> = {};
    value.forEach(lemma => { if (!(lemma in map)) map[lemma] = matches(lemma); });
    return map;
  }, [value, conflicts]);

  const getLemmaConflicts = (lemma: string): ConflictReport[] => conflictsByLemma[lemma] ?? [];

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-gray-700">
          {t('editors.lemmas.title')}
        </label>
        <div className="flex items-center space-x-2">
          {showSyncWarning && (
            <div className="flex items-center text-amber-600 text-xs">
              <AlertTriangle className="w-3 h-3 mr-1" />
              {t('editors.lemmas.unsynced', { count: suggestedLemmas.length })}
            </div>
          )}
          {onAutoSync && suggestedLemmas.length > 0 && (
            <button
              type="button"
              onClick={onAutoSync}
              disabled={disabled}
              className="flex items-center text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-50"
              title={t('editors.lemmas.syncTitle', { count: suggestedLemmas.length })}
            >
              <RefreshCw className="w-3 h-3 mr-1" />
              {t('editors.lemmas.sync', { count: suggestedLemmas.length })}
            </button>
          )}
        </div>
      </div>
      
      <p className="text-xs text-gray-500 mb-3">
        {t('editors.lemmas.help')}
      </p>

      {/* Current lemmas */}
      <div className="space-y-2 mb-3">
        {value.map((lemma, index) => {
          const lemmaConflicts = getLemmaConflicts(lemma);
          const hasConflicts = lemmaConflicts.length > 0;
          
          return (
            <div key={index} className="flex items-center space-x-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={lemma}
                  onChange={(e) => updateLemma(index, e.target.value)}
                  disabled={disabled}
                  className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 ${
                    hasConflicts ? 'border-red-300 bg-red-50' : 'border-gray-300'
                  }`}
                  placeholder={t('editors.lemmas.placeholder')}
                />
                {hasConflicts && (
                  <div className="absolute right-2 top-2 flex space-x-1">
                    {lemmaConflicts.slice(0, 2).map((conflict, conflictIndex) => (
                      <ConflictBadge 
                        key={conflictIndex} 
                        conflict={conflict} 
                        className="scale-75"
                      />
                    ))}
                    {lemmaConflicts.length > 2 && (
                      <span className="text-xs text-red-600 bg-red-100 px-1 rounded">
                        +{lemmaConflicts.length - 2}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => removeLemma(index)}
                disabled={disabled}
                className="p-2 text-red-600 hover:bg-red-50 rounded-md disabled:opacity-50"
                title={t('editors.lemmas.removeLemma')}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>

      {/* Add new lemma */}
      <div className="flex items-center space-x-2 mb-3">
        <input
          type="text"
          value={newLemma}
          onChange={(e) => setNewLemma(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50"
          placeholder={t('editors.lemmas.addPlaceholder')}
        />
        <button
          type="button"
          onClick={addLemma}
          disabled={disabled || !newLemma.trim()}
          className="flex items-center px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4 mr-1" />
          {t('common:actions.add')}
        </button>
      </div>

      {/* Suggested lemmas from token patterns */}
      {suggestedLemmas.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-600 mb-2">
            {t('editors.lemmas.suggestedFrom')}
          </p>
          <div className="flex flex-wrap gap-1">
            {suggestedLemmas.map((lemma, index) => (
              <button
                key={index}
                type="button"
                onClick={() => onChange([...value, lemma])}
                disabled={disabled}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
                title={t('editors.lemmas.addToLemmas', { lemma })}
              >
                + {lemma}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Info about lemmas */}
      <div className="mt-2 text-xs text-gray-500">
        <p>{t('editors.lemmas.info')}</p>
      </div>
    </div>
  );
}
