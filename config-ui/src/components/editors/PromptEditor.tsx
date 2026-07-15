/**
 * PromptEditor Component - Multi-section editor for prompt definitions
 * 
 * Provides structured editing for prompt YAML files with metadata support.
 * Handles prompt definitions with description, usage context, variables, and content.
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Eye, Code, Layout, MessageSquare, AlertCircle } from 'lucide-react';
import { Button, Alert, AlertTitle, AlertDescription, Tabs, TabsList, TabsTrigger, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import PromptDefinitionEditor from './PromptDefinitionEditor';
import Section from '@/components/ui/Section';
import TextArea from '@/components/ui/TextArea';
import Badge from '@/components/ui/Badge';
import type { PromptDefinition } from '@/types/api';

interface PromptEditorProps {
  value: Record<string, PromptDefinition>;
  onChange: (value: Record<string, PromptDefinition>) => void;
  onValidationChange?: (isValid: boolean, errors: string[]) => void;
}

type ViewMode = 'structured' | 'yaml' | 'preview';

const PromptEditor: React.FC<PromptEditorProps> = ({
  value,
  onChange,
  onValidationChange
}) => {
  const { t } = useTranslation('prompts');
  const [viewMode, setViewMode] = useState<ViewMode>('structured');
  const [yamlContent, setYamlContent] = useState('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Convert prompt definitions to YAML string
  const promptsToYaml = (prompts: Record<string, PromptDefinition>): string => {
    const yamlLines: string[] = [];
    
    Object.entries(prompts).forEach(([promptName, prompt]) => {
      yamlLines.push(`${promptName}:`);
      yamlLines.push(`  description: "${prompt.description}"`);
      yamlLines.push(`  usage_context: "${prompt.usage_context}"`);
      yamlLines.push(`  prompt_type: "${prompt.prompt_type}"`);
      
      if (prompt.variables && prompt.variables.length > 0) {
        yamlLines.push(`  variables:`);
        prompt.variables.forEach(variable => {
          yamlLines.push(`    - name: "${variable.name}"`);
          yamlLines.push(`      description: "${variable.description}"`);
        });
      } else {
        yamlLines.push(`  variables: []`);
      }
      
      // Handle multiline content
      if (prompt.content.includes('\n')) {
        yamlLines.push(`  content: |`);
        prompt.content.split('\n').forEach(line => {
          yamlLines.push(`    ${line}`);
        });
      } else {
        yamlLines.push(`  content: "${prompt.content.replace(/"/g, '\\"')}"`);
      }
      yamlLines.push('');
    });

    return yamlLines.join('\n');
  };

  // Parse YAML string to prompt definitions (simple implementation)
  const yamlToPrompts = (yamlStr: string): Record<string, PromptDefinition> => {
    try {
      // This is a simplified YAML parser for prompt structure
      // In a real implementation, you'd use a proper YAML library
      const lines = yamlStr.split('\n');
      const prompts: Record<string, PromptDefinition> = {};
      let currentPrompt: string | null = null;
      let currentSection: string | null = null;
      let content: string[] = [];
      let variables: Array<{ name: string; description: string }> = [];
      let currentVariable: { name?: string; description?: string } = {};

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;

        // Main prompt name
        if (line.match(/^[a-zA-Z_][a-zA-Z0-9_]*:$/)) {
          if (currentPrompt) {
            // Save previous prompt
            prompts[currentPrompt] = {
              description: prompts[currentPrompt]?.description || '',
              usage_context: prompts[currentPrompt]?.usage_context || '',
              variables: variables,
              prompt_type: prompts[currentPrompt]?.prompt_type || 'system',
              content: content.join('\n')
            };
          }
          currentPrompt = line.replace(':', '');
          currentSection = null;
          content = [];
          variables = [];
          prompts[currentPrompt] = {
            description: '',
            usage_context: '',
            variables: [],
            prompt_type: 'system',
            content: ''
          };
          continue;
        }

        if (!currentPrompt) continue;

        // Handle sections
        // (must exclude the variables section: a variable's `description:` is handled below;
        //  without this guard it was shadowed by this branch and never parsed.)
        if (currentSection !== 'variables' && line.match(/^\s+description:/)) {
          currentSection = 'description';
          const value = line.split('description:')[1]?.trim().replace(/^"|"$/g, '') || '';
          prompts[currentPrompt].description = value;
        } else if (line.match(/^\s+usage_context:/)) {
          currentSection = 'usage_context';
          const value = line.split('usage_context:')[1]?.trim().replace(/^"|"$/g, '') || '';
          prompts[currentPrompt].usage_context = value;
        } else if (line.match(/^\s+prompt_type:/)) {
          currentSection = 'prompt_type';
          const value = line.split('prompt_type:')[1]?.trim().replace(/^"|"$/g, '') || 'system';
          prompts[currentPrompt].prompt_type = value as 'system' | 'template' | 'user';
        } else if (line.match(/^\s+variables:/)) {
          currentSection = 'variables';
        } else if (line.match(/^\s+content:/)) {
          currentSection = 'content';
          const value = line.split('content:')[1]?.trim();
          if (value && !value.startsWith('|')) {
            content = [value.replace(/^"|"$/g, '')];
          }
        } else if (currentSection === 'content' && line.match(/^\s{4,}/)) {
          content.push(line.substring(4));
        } else if (currentSection === 'variables' && line.match(/^\s+- name:/)) {
          if (currentVariable.name) {
            variables.push(currentVariable as { name: string; description: string });
          }
          currentVariable = { name: line.split('name:')[1]?.trim().replace(/^"|"$/g, '') };
        } else if (currentSection === 'variables' && line.match(/^\s+description:/)) {
          currentVariable.description = line.split('description:')[1]?.trim().replace(/^"|"$/g, '') || '';
        }
      }

      // Save the last prompt
      if (currentPrompt) {
        if (currentVariable.name) {
          variables.push(currentVariable as { name: string; description: string });
        }
        prompts[currentPrompt] = {
          ...prompts[currentPrompt],
          variables: variables,
          content: content.join('\n')
        };
      }

      return prompts;
    } catch (error) {
      throw new Error(t('editor.yamlParseError', { message: error instanceof Error ? error.message : 'Unknown error' }));
    }
  };

  // Update YAML content when value changes (structured -> YAML)
  useEffect(() => {
    if (viewMode !== 'yaml') {
      setYamlContent(promptsToYaml(value));
    }
  }, [value, viewMode]);

  // Validate prompts
  useEffect(() => {
    const errors: string[] = [];
    
    Object.entries(value).forEach(([promptName, prompt]) => {
      if (!prompt.description) {
        errors.push(t('editor.validation.descriptionRequired', { prompt: promptName }));
      }
      if (!prompt.usage_context) {
        errors.push(t('editor.validation.usageContextRequired', { prompt: promptName }));
      }
      if (!prompt.content) {
        errors.push(t('editor.validation.contentRequired', { prompt: promptName }));
      }
      if (prompt.variables) {
        prompt.variables.forEach((variable, index) => {
          if (!variable.name) {
            errors.push(t('editor.validation.variableMissingName', { prompt: promptName, index: index + 1 }));
          }
        });
      }
    });

    setValidationErrors(errors);
    onValidationChange?.(errors.length === 0, errors);
  }, [value, onValidationChange, t]);

  const handleYamlChange = (newYaml: string) => {
    setYamlContent(newYaml);
    setYamlError(null);
    
    try {
      const parsed = yamlToPrompts(newYaml);
      onChange(parsed);
    } catch (error) {
      setYamlError(error instanceof Error ? error.message : t('editor.invalidYaml'));
    }
  };

  const handlePromptChange = (promptName: string, promptData: PromptDefinition) => {
    onChange({
      ...value,
      [promptName]: promptData
    });
  };

  const handlePromptDelete = (promptName: string) => {
    const newValue = { ...value };
    delete newValue[promptName];
    onChange(newValue);
  };

  const addNewPrompt = () => {
    const newPromptName = prompt(t('editor.newPromptNamePrompt'));
    if (newPromptName && !value[newPromptName]) {
      const newPrompt: PromptDefinition = {
        description: t('editor.defaults.description'),
        usage_context: t('editor.defaults.usageContext'),
        variables: [],
        prompt_type: 'system',
        content: t('editor.defaults.content')
      };
      onChange({
        ...value,
        [newPromptName]: newPrompt
      });
    }
  };

  const renderStructuredView = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-foreground">{t('editor.definitions')}</h3>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              size="sm"
              onClick={addNewPrompt}
            >
              <Plus />
              <span>{t('editor.addPrompt')}</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('editor.addPromptTitle')}</TooltipContent>
        </Tooltip>
      </div>

      {Object.keys(value).length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <MessageSquare className="w-8 h-8 mx-auto mb-2" />
          <p>{t('editor.empty')}</p>
        </div>
      ) : (
        Object.entries(value).map(([promptName, promptData]) => (
          <PromptDefinitionEditor
            key={promptName}
            promptName={promptName}
            value={promptData}
            onChange={handlePromptChange}
            onDelete={handlePromptDelete}
          />
        ))
      )}
    </div>
  );

  const renderYamlView = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-muted-foreground mb-2">
          {t('editor.yamlContent')}
        </label>
        <TextArea
          value={yamlContent}
          onChange={handleYamlChange}
          placeholder={t('editor.yamlPlaceholder')}
          rows={20}
          className={yamlError ? 'border-destructive' : ''}
        />
        {yamlError && (
          <p className="mt-1 text-sm text-destructive">{yamlError}</p>
        )}
      </div>
    </div>
  );

  const renderPreviewView = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-foreground">{t('editor.preview')}</h3>
      {Object.entries(value).map(([promptName, promptData]) => (
        <div key={promptName} className="bg-muted rounded-lg p-4 border border-border">
          <div className="flex items-center space-x-2 mb-2">
            <h4 className="font-medium text-foreground">{promptName}</h4>
            <Badge variant={promptData.prompt_type === 'system' ? 'info' : promptData.prompt_type === 'template' ? 'warning' : 'default'}>
              {promptData.prompt_type}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-2">{promptData.description}</p>
          <p className="text-xs text-muted-foreground mb-3">{t('editor.contextLabel', { ctx: promptData.usage_context })}</p>

          {promptData.variables.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">{t('editor.variablesLabel')}</p>
              <div className="flex flex-wrap gap-1">
                {promptData.variables.map((variable, idx) => (
                  <Badge key={idx} variant="default" className="text-xs">
                    {variable.name}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          
          <div className="bg-card rounded border border-border p-3">
            <pre className="text-sm text-foreground whitespace-pre-wrap">{promptData.content}</pre>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <Section title={t('editor.title')}>
      {/* View Mode Toggle */}
      <Tabs value={viewMode} onValueChange={(mode) => setViewMode(mode as ViewMode)} className="mb-4">
        <TabsList>
          <TabsTrigger value="structured" className="gap-2">
            <Layout className="w-4 h-4" />
            <span>{t('editor.viewModes.structured')}</span>
          </TabsTrigger>
          <TabsTrigger value="yaml" className="gap-2">
            <Code className="w-4 h-4" />
            <span>{t('editor.viewModes.yaml')}</span>
          </TabsTrigger>
          <TabsTrigger value="preview" className="gap-2">
            <Eye className="w-4 h-4" />
            <span>{t('editor.viewModes.preview')}</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle />
          <div>
            <AlertTitle>{t('editor.validationErrors')}</AlertTitle>
            <AlertDescription>
              <ul className="space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      )}

      {/* Content based on view mode */}
      {viewMode === 'structured' && renderStructuredView()}
      {viewMode === 'yaml' && renderYamlView()}
      {viewMode === 'preview' && renderPreviewView()}
    </Section>
  );
};

export default PromptEditor;
