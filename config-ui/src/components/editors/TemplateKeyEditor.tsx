/**
 * TemplateKeyEditor Component - Specialized editor for template key-value pairs
 * 
 * Handles different template value types: strings, arrays, and objects
 * with appropriate UI components for each type.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Trash2, Plus, ChevronDown, ChevronRight } from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Input from '@/components/ui/Input';
import TextArea from '@/components/ui/TextArea';
import ArrayOfStringsEditor from './ArrayOfStringsEditor';
import { safeDisplayValue } from '@/utils/safeStringify';

interface TemplateKeyEditorProps {
  templateKey: string;
  value: string | string[] | Record<string, any>;
  onChange: (key: string, value: string | string[] | Record<string, any>) => void;
  onDelete: (key: string) => void;
}

const TemplateKeyEditor: React.FC<TemplateKeyEditorProps> = ({
  templateKey,
  value,
  onChange,
  onDelete
}) => {
  const { t } = useTranslation('templates');
  const [isExpanded, setIsExpanded] = useState(false);
  // Key names are read-only since they connect to code

  const getValueType = (): 'string' | 'array' | 'object' => {
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object' && value !== null) return 'object';
    return 'string';
  };

  const handleValueChange = (newValue: string | string[] | Record<string, any>) => {
    onChange(templateKey, newValue);
  };

  const handleStringChange = (newValue: string) => {
    handleValueChange(newValue);
  };

  const handleArrayChange = (newArray: string[]) => {
    handleValueChange(newArray);
  };

  const handleObjectKeyChange = (oldKey: string, newKey: string, objValue: any) => {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const newObj = { ...value };
      delete newObj[oldKey];
      newObj[newKey] = objValue;
      handleValueChange(newObj);
    }
  };

  const handleObjectValueChange = (objKey: string, objValue: string) => {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const newObj = { ...value, [objKey]: objValue };
      handleValueChange(newObj);
    }
  };

  const handleObjectKeyDelete = (objKey: string) => {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const newObj = { ...value };
      delete newObj[objKey];
      handleValueChange(newObj);
    }
  };

  const addObjectKey = () => {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const newKey = `new_key_${Date.now()}`;
      const newObj = { ...value, [newKey]: '' };
      handleValueChange(newObj);
    }
  };

  const renderValueEditor = () => {
    const valueType = getValueType();

    switch (valueType) {
      case 'string':
        return (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-muted-foreground">
              {t('keyEditor.stringLabel')}
            </label>
            {typeof value === 'string' && value.length > 100 ? (
              <TextArea
                value={value}
                onChange={handleStringChange}
                placeholder={t('keyEditor.stringPlaceholder')}
                rows={4}
              />
            ) : (
              <Input
                value={value as string}
                onChange={handleStringChange}
                placeholder={t('keyEditor.stringPlaceholder')}
              />
            )}
          </div>
        );

      case 'array':
        return (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-muted-foreground">
              {t('keyEditor.arrayLabel')}
            </label>
            <ArrayOfStringsEditor
              label=""
              value={value as string[]}
              onChange={handleArrayChange}
              placeholder={t('keyEditor.arrayPlaceholder')}
            />
          </div>
        );

      case 'object':
        return (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="block text-sm font-medium text-muted-foreground">
                {t('keyEditor.objectLabel')}
              </label>
              <Button
                type="button"
                variant="link"
                size="sm"
                onClick={addObjectKey}
              >
                <Plus />
                <span>{t('keyEditor.addKey')}</span>
              </Button>
            </div>
            <div className="space-y-3 bg-muted p-3 rounded-md">
              {typeof value === 'object' && value !== null && !Array.isArray(value) && (
                Object.entries(value).map(([objKey, objValue]) => (
                  <div key={objKey} className="flex space-x-2">
                    <Input
                      value={objKey}
                      onChange={(newKey) => handleObjectKeyChange(objKey, newKey, objValue)}
                      placeholder={t('keyEditor.keyNamePlaceholder')}
                      className="w-1/3"
                    />
                    <Input
                      value={safeDisplayValue(objValue)}
                      onChange={(newValue) => handleObjectValueChange(objKey, newValue)}
                      placeholder={t('keyEditor.valuePlaceholder')}
                      className="flex-1"
                    />
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => handleObjectKeyDelete(objKey)}
                          className="text-destructive"
                          aria-label={t('keyEditor.deleteKey')}
                        >
                          <Trash2 />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>{t('keyEditor.deleteKey')}</TooltipContent>
                    </Tooltip>
                  </div>
                ))
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="border border-border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? <ChevronDown /> : <ChevronRight />}
          <span>{templateKey}</span>
        </Button>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => onDelete(templateKey)}
              className="text-destructive"
              aria-label={t('keyEditor.deleteTemplateKey')}
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('keyEditor.deleteTemplateKey')}</TooltipContent>
        </Tooltip>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              {t('keyEditor.keyNameReadonly')}
            </label>
            <Input
              value={templateKey}
              onChange={() => {}} // Read-only
              placeholder={t('keyEditor.keyIdentifierPlaceholder')}
              disabled={true}
              className="cursor-not-allowed"
            />
          </div>

          {renderValueEditor()}

          <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
            <strong>{t('keyEditor.typeLabel')}</strong> {getValueType()} |
            <strong> {t('keyEditor.lengthLabel')}</strong> {
              getValueType() === 'string' 
                ? (value as string).length
                : getValueType() === 'array'
                ? (value as string[]).length
                : Object.keys(value as object).length
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default TemplateKeyEditor;
