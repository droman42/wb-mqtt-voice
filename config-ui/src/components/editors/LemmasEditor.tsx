import { Plus, Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
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
        <label className="block text-sm font-medium text-muted-foreground">
          {t('editors.lemmas.title')}
        </label>
        <div className="flex items-center space-x-2">
          {showSyncWarning && (
            <div className="flex items-center text-xs text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]">
              <AlertTriangle className="w-3 h-3 mr-1" />
              {t('editors.lemmas.unsynced', { count: suggestedLemmas.length })}
            </div>
          )}
          {onAutoSync && suggestedLemmas.length > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onAutoSync}
                  disabled={disabled}
                >
                  <RefreshCw />
                  {t('editors.lemmas.sync', { count: suggestedLemmas.length })}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('editors.lemmas.syncTitle', { count: suggestedLemmas.length })}</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground mb-3">
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
                  className={`w-full px-3 py-2 border rounded-md text-sm bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:bg-muted ${
                    hasConflicts ? 'border-destructive' : 'border-input'
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
                      <Badge variant="error" className="text-xs">
                        +{lemmaConflicts.length - 2}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeLemma(index)}
                    disabled={disabled}
                    className="text-destructive"
                    aria-label={t('editors.lemmas.removeLemma')}
                  >
                    <Trash2 />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>{t('editors.lemmas.removeLemma')}</TooltipContent>
              </Tooltip>
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
          className="flex-1 px-3 py-2 border border-input bg-background rounded-md text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:bg-muted"
          placeholder={t('editors.lemmas.addPlaceholder')}
        />
        <Button
          type="button"
          onClick={addLemma}
          disabled={disabled || !newLemma.trim()}
        >
          <Plus />
          {t('common:actions.add')}
        </Button>
      </div>

      {/* Suggested lemmas from token patterns */}
      {suggestedLemmas.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-muted-foreground mb-2">
            {t('editors.lemmas.suggestedFrom')}
          </p>
          <div className="flex flex-wrap gap-1">
            {suggestedLemmas.map((lemma, index) => (
              <Tooltip key={index}>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => onChange([...value, lemma])}
                    disabled={disabled}
                  >
                    + {lemma}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>{t('editors.lemmas.addToLemmas', { lemma })}</TooltipContent>
              </Tooltip>
            ))}
          </div>
        </div>
      )}

      {/* Info about lemmas */}
      <div className="mt-2 text-xs text-muted-foreground">
        <p>{t('editors.lemmas.info')}</p>
      </div>
    </div>
  );
}
