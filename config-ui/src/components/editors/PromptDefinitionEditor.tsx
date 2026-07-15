/**
 * PromptDefinitionEditor Component - Editor for individual prompt definitions
 * 
 * Handles prompt metadata, variables, and content editing with collapsible sections.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Trash2, Plus, ChevronDown, ChevronRight, MessageSquare } from 'lucide-react';
import { Button, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Input from '@/components/ui/Input';
import TextArea from '@/components/ui/TextArea';
import Badge from '@/components/ui/Badge';
import type { PromptDefinition } from '@/types/api';

interface PromptDefinitionEditorProps {
  promptName: string;
  value: PromptDefinition;
  onChange: (promptName: string, value: PromptDefinition) => void;
  onDelete: (promptName: string) => void;
}

interface PromptVariable {
  name: string;
  description: string;
}

const PromptDefinitionEditor: React.FC<PromptDefinitionEditorProps> = ({
  promptName,
  value,
  onChange,
  onDelete
}) => {
  const { t } = useTranslation('prompts');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleFieldChange = (field: keyof PromptDefinition, newValue: any) => {
    onChange(promptName, {
      ...value,
      [field]: newValue
    });
  };

  const handleVariableChange = (index: number, field: keyof PromptVariable, newValue: string) => {
    const newVariables = [...value.variables];
    newVariables[index] = {
      ...newVariables[index],
      [field]: newValue
    };
    handleFieldChange('variables', newVariables);
  };

  const addVariable = () => {
    const newVariable: PromptVariable = {
      name: '',
      description: ''
    };
    handleFieldChange('variables', [...value.variables, newVariable]);
  };

  const removeVariable = (index: number) => {
    const newVariables = value.variables.filter((_, i) => i !== index);
    handleFieldChange('variables', newVariables);
  };

  const handleDelete = () => {
    if (confirm(t('keyEditor.deleteConfirm', { prompt: promptName }))) {
      onDelete(promptName);
    }
  };

  const getPromptTypeColor = (type: string) => {
    switch (type) {
      case 'system': return 'info';
      case 'template': return 'warning';
      case 'user': return 'default';
      default: return 'default';
    }
  };

  return (
    <div className="border border-border rounded-lg bg-card">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center space-x-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-muted-foreground"
          >
            {isExpanded ? <ChevronDown /> : <ChevronRight />}
          </Button>
          <MessageSquare className="w-5 h-5 text-primary" />
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium text-foreground">{promptName}</h3>
            <Badge variant={getPromptTypeColor(value.prompt_type)}>
              {value.prompt_type}
            </Badge>
          </div>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleDelete}
              className="text-destructive"
              aria-label={t('keyEditor.deleteTitle', { prompt: promptName })}
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('keyEditor.deleteTitle', { prompt: promptName })}</TooltipContent>
        </Tooltip>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              {t('keyEditor.description')}
            </label>
            <Input
              value={value.description}
              onChange={(newValue) => handleFieldChange('description', newValue)}
              placeholder={t('keyEditor.descriptionPlaceholder')}
            />
          </div>

          {/* Usage Context */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              {t('keyEditor.usageContext')}
            </label>
            <Input
              value={value.usage_context}
              onChange={(newValue) => handleFieldChange('usage_context', newValue)}
              placeholder={t('keyEditor.usageContextPlaceholder')}
            />
          </div>

          {/* Prompt Type */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              {t('keyEditor.promptType')}
            </label>
            <Select
              value={value.prompt_type}
              onValueChange={(newValue) => handleFieldChange('prompt_type', newValue)}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="system">{t('keyEditor.types.system')}</SelectItem>
                <SelectItem value="template">{t('keyEditor.types.template')}</SelectItem>
                <SelectItem value="user">{t('keyEditor.types.user')}</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              {t(`keyEditor.typeHints.${value.prompt_type}`)}
            </p>
          </div>

          {/* Variables */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-muted-foreground">
                {t('keyEditor.variables')}
              </label>
              <Button
                type="button"
                size="sm"
                onClick={addVariable}
              >
                <Plus />
                <span>{t('keyEditor.addVariable')}</span>
              </Button>
            </div>

            {value.variables.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground border-2 border-dashed border-border rounded-md">
                <p className="text-sm">{t('keyEditor.noVariables')}</p>
                <p className="text-xs">{t('keyEditor.noVariablesHint')}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {value.variables.map((variable, index) => (
                  <div key={index} className="flex items-start space-x-2 p-3 bg-muted rounded-md">
                    <div className="flex-1 space-y-2">
                      <Input
                        value={variable.name}
                        onChange={(newValue) => handleVariableChange(index, 'name', newValue)}
                        placeholder={t('keyEditor.variableNamePlaceholder')}
                      />
                      <Input
                        value={variable.description}
                        onChange={(newValue) => handleVariableChange(index, 'description', newValue)}
                        placeholder={t('keyEditor.variableDescriptionPlaceholder')}
                      />
                    </div>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeVariable(index)}
                          className="text-destructive mt-1"
                          aria-label={t('keyEditor.removeVariable')}
                        >
                          <Trash2 />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>{t('keyEditor.removeVariable')}</TooltipContent>
                    </Tooltip>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              {t('keyEditor.content')}
            </label>
            <TextArea
              value={value.content}
              onChange={(newValue) => handleFieldChange('content', newValue)}
              placeholder={t('keyEditor.contentPlaceholder')}
              rows={6}
            />
            <div className="mt-1 text-xs text-muted-foreground">
              <p>{t('keyEditor.contentHint')}</p>
              {value.variables.length > 0 && (
                <p>{t('keyEditor.availableVariables', { variables: value.variables.map(v => `{${v.name}}`).join(', ') })}</p>
              )}
            </div>
          </div>

          {/* Preview */}
          {value.content && (
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('keyEditor.preview')}
              </label>
              <div className="bg-muted border border-border rounded-md p-3">
                <pre className="text-sm text-foreground whitespace-pre-wrap">{value.content}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PromptDefinitionEditor;
