import { useTranslation } from 'react-i18next';
import { Trash2, Plus } from 'lucide-react';
import TextArea from '@/components/ui/TextArea';
import KeyValueEditor from './KeyValueEditor';
import type { ExamplesEditorProps } from '@/types';

interface Example {
  text: string;
  parameters: Record<string, any>;
}

export default function ExamplesEditor({
  value, 
  onChange, 
  globalParams,
  disabled = false
}: ExamplesEditorProps) {
  const { t } = useTranslation('donations');
  const arr: Example[] = value?.map(item => {
    if (typeof item === 'string') {
      return { text: item, parameters: {} };
    }
    return item;
  }) ?? [];

  const add = (): void => {
    onChange([...arr, { text: '', parameters: {} }]);
  };

  const del = (idx: number): void => {
    onChange(arr.filter((_, i) => i !== idx));
  };

  const set = (idx: number, obj: Example): void => {
    const newArr = arr.map((o, i) => i === idx ? obj : o);
    onChange(newArr);
  };

  return (
    <div className="flex flex-col gap-2">
      {arr.length === 0 ? (
        <div className="text-sm text-gray-500 mb-2">{t('editors.examples.empty')}</div>
      ) : null}
      {arr.map((ex, idx) => (
        <div key={idx} className="border rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">{t('editors.examples.example', { index: idx + 1 })}</div>
            <button
              className="p-2 rounded-lg border hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => del(idx)}
              disabled={disabled}
              title={t('editors.examples.removeExample')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <TextArea
            label={t('editors.examples.userText')}
            value={ex.text ?? ''}
            onChange={(v) => set(idx, { ...ex, text: v })}
            disabled={disabled}
            placeholder={t('editors.examples.userTextPlaceholder')}
          />
          <div className="text-sm font-medium mb-2">{t('editors.examples.expectedParameters')}</div>
          <KeyValueEditor
            label={t('editors.examples.parameters')}
            object={ex.parameters ?? {}}
            onChange={(o) => set(idx, { ...ex, parameters: o })}
            disabled={disabled}
          />
          {globalParams?.length ? (
            <div className="text-xs text-gray-500 mt-2">
              {t('editors.examples.availableParameters', { params: globalParams.join(', ') })}
            </div>
          ) : null}
        </div>
      ))}
      <button
        onClick={add}
        className="inline-flex items-center gap-2 px-3 py-2 border rounded-xl hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={disabled}
      >
        <Plus className="w-4 h-4" /> {t('editors.examples.addExample')}
      </button>
    </div>
  );
}
