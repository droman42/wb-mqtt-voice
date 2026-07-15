/**
 * SpacyValueEditor - Specialized input components for different SpaCy attribute value types
 * 
 * Provides appropriate input controls based on the SpaCy attribute structure,
 * ensuring proper editing while maintaining the underlying data integrity.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import {
  Alert, AlertDescription, Button, Input,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea,
  Tooltip, TooltipTrigger, TooltipContent
} from 'locveil-ui-kit';
import { SpacyAttributeStructure, getOperatorOptions } from '@/utils/spacyAttributeHelpers';

type OperatorKey =
  | 'zeroOrOne' | 'zeroOrMore' | 'oneOrMore' | 'negation'
  | 'exactly2' | 'between2And4' | 'twoOrMore' | 'upTo4' | 'custom';

const OPERATOR_KEYS: Record<string, OperatorKey> = {
  '?': 'zeroOrOne',
  '*': 'zeroOrMore',
  '+': 'oneOrMore',
  '!': 'negation',
  '{2}': 'exactly2',
  '{2,4}': 'between2And4',
  '{2,}': 'twoOrMore',
  '{,4}': 'upTo4',
};

interface SpacyValueEditorProps {
  structure: SpacyAttributeStructure;
  onChange: (newValue: any) => void;
  disabled?: boolean;
}

const SpacyValueEditor: React.FC<SpacyValueEditorProps> = ({
  structure,
  onChange,
  disabled = false
}) => {
  const { t } = useTranslation('donations');
  const { valueType, editableValue } = structure;

  // String input for simple text values and regex patterns
  const renderStringInput = (placeholder?: string) => (
    <Input
      type="text"
      value={editableValue || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
    />
  );

  // Boolean toggle for true/false values
  const renderBooleanInput = () => (
    <Select
      value={String(editableValue)}
      onValueChange={(v) => onChange(v === 'true')}
      disabled={disabled}
    >
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="true">{t('editors.spacyValue.true')}</SelectItem>
        <SelectItem value="false">{t('editors.spacyValue.false')}</SelectItem>
      </SelectContent>
    </Select>
  );

  // Number input for numeric values
  const renderNumberInput = () => (
    <Input
      type="number"
      value={editableValue || ''}
      onChange={(e) => onChange(Number(e.target.value))}
      disabled={disabled}
    />
  );

  // Operator dropdown for OP attribute (kept native: the empty-string
  // "select an operator" placeholder value is not representable in the radix Select)
  const renderOperatorInput = () => {
    const operators = getOperatorOptions();

    return (
      <select
        value={editableValue || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full appearance-none rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        disabled={disabled}
      >
        <option value="">{t('editors.spacyValue.selectOperator')}</option>
        {operators.map(op => (
          <option key={op} value={op}>
            {op} - {t(`editors.spacyValue.operator.${OPERATOR_KEYS[op] ?? 'custom'}` as const)}
          </option>
        ))}
      </select>
    );
  };

  // Array editor for IN/NOT_IN lists
  const renderListInput = () => {
    const listValue: string[] = Array.isArray(editableValue) ? editableValue : [];
    
    const addItem = () => {
      onChange([...listValue, '']);
    };

    const updateItem = (index: number, newValue: string) => {
      const newList = [...listValue];
      newList[index] = newValue;
      onChange(newList);
    };

    const removeItem = (index: number) => {
      const newList = listValue.filter((_, i) => i !== index);
      onChange(newList);
    };

    return (
      <div className="space-y-2">
        <div className="space-y-2">
          {listValue.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-6">{index + 1}.</span>
              <Input
                type="text"
                value={item}
                onChange={(e) => updateItem(index, e.target.value)}
                className="flex-1"
                placeholder={t('editors.spacyValue.itemPlaceholder', { index: index + 1 })}
                disabled={disabled}
              />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeItem(index)}
                    className="text-destructive"
                    disabled={disabled}
                    aria-label={t('editors.spacyValue.removeItem')}
                  >
                    <Trash2 />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>{t('editors.spacyValue.removeItem')}</TooltipContent>
              </Tooltip>
            </div>
          ))}
        </div>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={addItem}
          className="text-primary"
          disabled={disabled}
        >
          <Plus />
          {t('editors.spacyValue.addItem')}
        </Button>

        {listValue.length === 0 && (
          <div className="text-sm text-muted-foreground italic">
            {t('editors.spacyValue.noItems')}
          </div>
        )}
      </div>
    );
  };

  // JSON editor for unknown/custom structures
  const renderJsonInput = () => (
    <div className="space-y-2">
      <Alert>
        <AlertDescription className="text-xs">
          {t('editors.spacyValue.jsonWarning')}
        </AlertDescription>
      </Alert>
      <Textarea
        value={editableValue || ''}
        onChange={(e) => onChange(e.target.value)}
        className="font-mono"
        rows={3}
        placeholder={t('editors.spacyValue.jsonPlaceholder')}
        disabled={disabled}
      />
    </div>
  );

  // Main render logic based on value type
  switch (valueType) {
    case 'string':
      return renderStringInput();
    
    case 'regex':
      return renderStringInput(t('editors.spacyValue.regexPlaceholder'));
    
    case 'boolean':
      return renderBooleanInput();
    
    case 'number':
      return renderNumberInput();
    
    case 'operator':
      return renderOperatorInput();
    
    case 'list':
      return renderListInput();
    
    case 'unknown':
      return renderJsonInput();
    
    default:
      return renderStringInput();
  }
};

export default SpacyValueEditor;
