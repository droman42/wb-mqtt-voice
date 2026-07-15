/**
 * SpacyAttributeEditor - Enhanced editor for spaCy token attributes
 * 
 * Provides structured editing for spaCy token patterns with:
 * - Intelligent parsing of SpaCy attribute structures  
 * - Type-aware value editors that preserve attribute semantics
 * - Support for complex patterns (REGEX, IN, NOT_IN, etc.)
 * - User-friendly display of attribute names and types
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
import { Alert, AlertDescription, Button, Input, Label, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import {
  parseSpacyAttribute,
  reconstructSpacyAttribute,
  SPACY_ATTRIBUTE_SUGGESTIONS,
  type SpacyAttributeStructure
} from '@/utils/spacyAttributeHelpers';
import SpacyValueEditor from './SpacyValueEditor';

interface SpacyAttributeEditorProps {
  value: Record<string, any>;
  onChange: (value: Record<string, any>) => void;
  disabled?: boolean;
}

interface StructuredAttributeEditorProps {
  attributeName: string;
  structure: SpacyAttributeStructure;
  onChange: (newValue: any) => void;
  onRemove: () => void;
  disabled?: boolean;
}

// Structured attribute editor that handles complex SpaCy patterns
function StructuredAttributeEditor({ 
  attributeName: _, // Mark as unused with underscore
  structure, 
  onChange, 
  onRemove,
  disabled
}: StructuredAttributeEditorProps) {
  const { t } = useTranslation('donations');
  const [isExpanded, setIsExpanded] = useState(true);

  const handleValueChange = (newValue: any) => {
    const reconstructedValue = reconstructSpacyAttribute(structure, newValue);
    onChange(reconstructedValue);
  };

  const getTypeIndicator = () => {
    // Value-type indicator is a neutral pill (raw palette per type is not part of the
    // design system's status vocabulary).
    return (
      <Badge variant="custom">
        {structure.valueType}
      </Badge>
    );
  };

  return (
    <div className="border border-border rounded-lg bg-card">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-left flex-1 hover:bg-muted/60 -m-1 p-1 rounded transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          disabled={disabled}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <span className="font-medium text-foreground">{structure.displayLabel}</span>
          {getTypeIndicator()}
        </button>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRemove}
              className="h-7 w-7 text-destructive"
              disabled={disabled}
              aria-label={t('editors.spacy.removeAttribute')}
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('editors.spacy.removeAttribute')}</TooltipContent>
        </Tooltip>
      </div>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="p-3 space-y-3">
          {/* Description/Help */}
          {structure.isComplex && (
            <Alert variant="accent">
              <AlertDescription>
                {t('editors.spacy.matchPrefix')}<strong>{structure.attributeName}</strong>{t('editors.spacy.matchInfix')}<strong>{structure.valueType}</strong>{t('editors.spacy.matchSuffix')}
              </AlertDescription>
            </Alert>
          )}
          
          {/* Value Editor */}
          <SpacyValueEditor
            structure={structure}
            onChange={handleValueChange}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
}

// Main SpaCy Attribute Editor component
export default function SpacyAttributeEditor({ 
  value, 
  onChange,
  disabled = false
}: SpacyAttributeEditorProps) {
  const { t } = useTranslation(['donations', 'common']);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newAttributeName, setNewAttributeName] = useState('');

  // Parse all current attributes into structured format
  const structuredAttributes = Object.entries(value || {}).map(([key, val]) => ({
    key,
    structure: parseSpacyAttribute(key, val)
  }));

  const handleAttributeChange = (attributeKey: string, newValue: any) => {
    const newAttributes = { ...value };
    newAttributes[attributeKey] = newValue;
    onChange(newAttributes);
  };

  const handleAttributeRemove = (attributeKey: string) => {
    const newAttributes = { ...value };
    delete newAttributes[attributeKey];
    onChange(newAttributes);
  };

  const handleAddAttribute = () => {
    if (!newAttributeName.trim()) return;
    
    const attributeName = newAttributeName.trim();
    const newAttributes = { ...value };
    
    // Set default value based on common attribute patterns
    if (attributeName === 'OP') {
      newAttributes[attributeName] = '?';
    } else if (attributeName.includes('IS_') || attributeName.includes('LIKE_')) {
      newAttributes[attributeName] = true;
    } else {
      newAttributes[attributeName] = '';
    }
    
    onChange(newAttributes);
    setNewAttributeName('');
    setShowAddForm(false);
  };

  const getAttributeSuggestions = () => {
    const currentKeys = Object.keys(value || {});
    return SPACY_ATTRIBUTE_SUGGESTIONS.filter(key => !currentKeys.includes(key));
  };

  return (
    <div className="space-y-3">
      {/* Current Attributes */}
      {structuredAttributes.length > 0 ? (
        <div className="space-y-2">
          {structuredAttributes.map(({ key, structure }) => (
            <StructuredAttributeEditor
              key={key}
              attributeName={key}
              structure={structure}
              onChange={(newValue) => handleAttributeChange(key, newValue)}
              onRemove={() => handleAttributeRemove(key)}
              disabled={disabled}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground bg-muted rounded-lg border border-border">
          <div className="text-sm font-medium mb-1">{t('editors.spacy.noAttributes')}</div>
          <div className="text-xs">{t('editors.spacy.addHint')}</div>
        </div>
      )}

      {/* Add New Attribute */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-border rounded-lg text-muted-foreground hover:border-muted-foreground hover:text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          disabled={disabled}
        >
          <Plus className="w-4 h-4" />
          {t('editors.spacy.addAttribute')}
        </button>
      ) : (
        <div className="border border-border rounded-lg p-3 bg-muted">
          <div className="space-y-3">
            <div>
              <Label className="mb-1">
                {t('editors.spacy.attributeName')}
              </Label>
              <select
                value={newAttributeName}
                onChange={(e) => setNewAttributeName(e.target.value)}
                className="w-full appearance-none rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">{t('editors.spacy.selectAttribute')}</option>
                {getAttributeSuggestions().map(attr => (
                  <option key={attr} value={attr}>{attr}</option>
                ))}
                <option value="custom">{t('editors.spacy.customAttribute')}</option>
              </select>
            </div>

            {newAttributeName === 'custom' && (
              <div>
                <Label className="mb-1">
                  {t('editors.spacy.customAttributeName')}
                </Label>
                <Input
                  type="text"
                  value=""
                  onChange={(e) => setNewAttributeName(e.target.value)}
                  placeholder={t('editors.spacy.customAttributePlaceholder')}
                />
              </div>
            )}

            <div className="flex gap-2">
              <Button
                onClick={handleAddAttribute}
                disabled={!newAttributeName || disabled}
              >
                {t('common:actions.add')}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowAddForm(false);
                  setNewAttributeName('');
                }}
                disabled={disabled}
              >
                {t('common:actions.cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}