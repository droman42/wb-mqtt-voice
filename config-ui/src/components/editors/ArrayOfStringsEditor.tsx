import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import type { ArrayOfStringsEditorProps } from '@/types';

export default function ArrayOfStringsEditor({
  label,
  value,
  onChange,
  placeholder,
  disabled = false
}: ArrayOfStringsEditorProps & { addLabel?: string }) {
  const { t } = useTranslation(['donations', 'common']);
  const arr = value ?? [];
  
  const update = (idx: number, v: string): void => {
    const next = [...arr];
    next[idx] = v;
    onChange(next);
  };

  const remove = (idx: number): void => {
    const next = arr.filter((_, i) => i !== idx);
    onChange(next);
  };

  const add = (): void => {
    onChange([...arr, '']);
  };

  return (
    <div className="mb-4">
      <div className="font-medium mb-2">{label}</div>
      {arr.length === 0 ? (
        <div className="text-sm text-muted-foreground mb-2">{t('editors.noItems')}</div>
      ) : null}
      {arr.map((item, idx) => (
        <div key={idx} className="flex items-center gap-2 mb-2">
          <input
            className={`flex-1 border border-input bg-background rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              disabled ? 'bg-muted cursor-not-allowed' : ''
            }`}
            value={item}
            onChange={(e) => update(idx, e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
          />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={() => remove(idx)}
                aria-label={t('common:actions.remove')}
                disabled={disabled}
              >
                <Trash2 />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('common:actions.remove')}</TooltipContent>
          </Tooltip>
        </div>
      ))}
      <Button
        variant="outline"
        onClick={add}
        disabled={disabled}
      >
        <Plus /> {t('common:actions.add')}
      </Button>
    </div>
  );
}
