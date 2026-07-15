import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';

function coerceValue(v: string): string | number | boolean {
  if (v === '') return '';
  if (v === 'true') return true;
  if (v === 'false') return false;
  if (!isNaN(Number(v))) return Number(v);
  return v;
}

interface KeyValueEditorProps {
  label: string;
  object: Record<string, any>;
  onChange: (object: Record<string, any>) => void;
  disabled?: boolean;
}

export default function KeyValueEditor({
  label, 
  object, 
  onChange, 
  disabled = false
}: KeyValueEditorProps) {
  const { t } = useTranslation(['configuration', 'common']);
  const entries = Object.entries(object ?? {});
  
  const setKV = (k: string, v: any): void => {
    const next = { ...(object ?? {}) };
    next[k] = v;
    onChange(next);
  };

  const del = (k: string): void => {
    const next = { ...(object ?? {}) };
    delete next[k];
    onChange(next);
  };

  const updateKey = (oldKey: string, newKey: string): void => {
    if (oldKey === newKey) return;
    const val = object[oldKey];
    const next = { ...(object ?? {}) };
    delete next[oldKey];
    next[newKey] = val;
    onChange(next);
  };

  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');

  const addEntry = (): void => {
    if (!newKey.trim()) return;
    const next = { ...(object ?? {}) };
    next[newKey] = coerceValue(newVal);
    onChange(next);
    setNewKey('');
    setNewVal('');
  };

  return (
    <div className="mb-4">
      <div className="font-medium mb-2">{label}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-2">
            <input
              className={`border border-input bg-background rounded-md px-3 py-2 flex-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                disabled ? 'bg-muted cursor-not-allowed' : ''
              }`}
              value={k}
              onChange={(e) => updateKey(k, e.target.value)}
              disabled={disabled}
              placeholder={t('keyValue.keyPlaceholder')}
            />
            <input
              className={`border border-input bg-background rounded-md px-3 py-2 flex-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                disabled ? 'bg-muted cursor-not-allowed' : ''
              }`}
              value={String(v)}
              onChange={(e) => setKV(k, coerceValue(e.target.value))}
              disabled={disabled}
              placeholder={t('keyValue.valuePlaceholder')}
            />
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => del(k)}
                  disabled={disabled}
                  aria-label={t('keyValue.removeEntry')}
                >
                  ✕
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('keyValue.removeEntry')}</TooltipContent>
            </Tooltip>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <input
          className={`border border-input bg-background rounded-md px-3 py-2 flex-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
            disabled ? 'bg-muted cursor-not-allowed' : ''
          }`}
          placeholder={t('keyValue.keyPlaceholder')}
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          disabled={disabled}
        />
        <input
          className={`border border-input bg-background rounded-md px-3 py-2 flex-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
            disabled ? 'bg-muted cursor-not-allowed' : ''
          }`}
          placeholder={t('keyValue.valuePlaceholder')}
          value={newVal}
          onChange={(e) => setNewVal(e.target.value)}
          disabled={disabled}
        />
        <Button
          variant="outline"
          onClick={addEntry}
          disabled={disabled || !newKey.trim()}
        >
          {t('common:actions.add')}
        </Button>
      </div>
    </div>
  );
}
