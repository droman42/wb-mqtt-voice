/**
 * TemplateEditor Component - YAML-aware editor for response templates
 * 
 * Provides structured editing for template YAML files with support for
 * strings, arrays, and objects. Includes real-time validation and preview.
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, FileText, Eye, Code, Layout, AlertCircle } from 'lucide-react';
import { Button, Alert, AlertTitle, AlertDescription, Tabs, TabsList, TabsTrigger, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import TemplateKeyEditor from './TemplateKeyEditor';
import Section from '@/components/ui/Section';
import TextArea from '@/components/ui/TextArea';
import Badge from '@/components/ui/Badge';

interface TemplateEditorProps {
  value: Record<string, any>;
  onChange: (value: Record<string, any>) => void;
  schema?: Record<string, any>;
  onValidationChange?: (isValid: boolean, errors: string[]) => void;
}

type ViewMode = 'structured' | 'yaml' | 'preview';

const TemplateEditor: React.FC<TemplateEditorProps> = ({
  value,
  onChange,
  schema,
  onValidationChange
}) => {
  const { t } = useTranslation('templates');
  const [viewMode, setViewMode] = useState<ViewMode>('structured');
  const [yamlContent, setYamlContent] = useState('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Convert object to YAML string (simple implementation)
  const objectToYaml = (obj: Record<string, any>): string => {
    const yamlLines: string[] = [];
    
    const processValue = (val: any, indent: string = ''): string => {
      if (typeof val === 'string') {
        // Handle multiline strings
        if (val.includes('\n')) {
          return `|\n${val.split('\n').map(line => `${indent}  ${line}`).join('\n')}`;
        }
        return `"${val.replace(/"/g, '\\"')}"`;
      }
      
      if (Array.isArray(val)) {
        if (val.length === 0) return '[]';
        return '\n' + val.map(item => `${indent}- ${processValue(item, indent + '  ')}`).join('\n');
      }
      
      if (typeof val === 'object' && val !== null) {
        const entries = Object.entries(val);
        if (entries.length === 0) return '{}';
        return '\n' + entries.map(([k, v]) => 
          `${indent}${k}: ${processValue(v, indent + '  ')}`
        ).join('\n');
      }
      
      return String(val);
    };

    Object.entries(obj).forEach(([key, value]) => {
      yamlLines.push(`${key}: ${processValue(value)}`);
    });

    return yamlLines.join('\n');
  };

  // Parse YAML string to object (simple implementation)
  const yamlToObject = (yamlStr: string): Record<string, any> => {
    try {
      // This is a simplified YAML parser - in production you'd use a proper YAML library
      const lines = yamlStr.split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
      const result: Record<string, any> = {};
      
      for (const line of lines) {
        const match = line.match(/^([^:]+):\s*(.*)$/);
        if (match) {
          const key = match[1].trim();
          const value = match[2].trim();
          
          if (value.startsWith('"') && value.endsWith('"')) {
            result[key] = value.slice(1, -1).replace(/\\"/g, '"');
          } else if (value === '[]') {
            result[key] = [];
          } else if (value === '{}') {
            result[key] = {};
          } else if (value.startsWith('[') && value.endsWith(']')) {
            try {
              result[key] = JSON.parse(value);
            } catch {
              result[key] = value;
            }
          } else {
            result[key] = value;
          }
        }
      }
      
      return result;
    } catch (error) {
      throw new Error(t('editor.yamlParseError', { message: error instanceof Error ? error.message : 'Unknown error' }));
    }
  };

  // Update YAML content when value changes
  useEffect(() => {
    if (viewMode !== 'yaml') {
      setYamlContent(objectToYaml(value));
    }
  }, [value, viewMode]);

  // Validate template data
  useEffect(() => {
    const errors: string[] = [];
    
    // Basic validation
    if (typeof value !== 'object' || value === null) {
      errors.push(t('editor.validation.mustBeObject'));
    } else {
      // Check for empty keys
      Object.keys(value).forEach(key => {
        if (!key.trim()) {
          errors.push(t('editor.validation.keysNotEmpty'));
        }
      });

      // Check schema if provided
      if (schema && schema.expected_keys) {
        const missingKeys = schema.expected_keys.filter((key: string) => !(key in value));
        if (missingKeys.length > 0) {
          errors.push(t('editor.validation.missingKeys', { keys: missingKeys.join(', ') }));
        }
      }
    }

    setValidationErrors(errors);
    if (onValidationChange) {
      onValidationChange(errors.length === 0, errors);
    }
  }, [value, schema, onValidationChange, t]);

  const handleYamlChange = (newYaml: string) => {
    setYamlContent(newYaml);
    setYamlError(null);
    
    try {
      const parsed = yamlToObject(newYaml);
      onChange(parsed);
    } catch (error) {
      setYamlError(error instanceof Error ? error.message : t('editor.yamlParseErrorShort'));
    }
  };

  const handleKeyChange = (key: string, newValue: string | string[] | Record<string, any>) => {
    const newData = { ...value, [key]: newValue };
    onChange(newData);
  };

  const handleKeyDelete = (key: string) => {
    const newData = { ...value };
    delete newData[key];
    onChange(newData);
  };

  // Key renaming removed - template keys are read-only

  const addNewKey = () => {
    const newKey = `new_template_${Date.now()}`;
    const newData = { ...value, [newKey]: '' };
    onChange(newData);
  };

  const renderStructuredView = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-foreground">{t('editor.keys')}</h3>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              size="sm"
              onClick={addNewKey}
            >
              <Plus />
              <span>{t('editor.addKey')}</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('editor.addKeyTitle')}</TooltipContent>
        </Tooltip>
      </div>

      {Object.keys(value).length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <FileText className="w-8 h-8 mx-auto mb-2" />
          <p>{t('editor.empty')}</p>
        </div>
      ) : (
        Object.entries(value).map(([key, val]) => (
          <TemplateKeyEditor
            key={key}
            templateKey={key}
            value={val}
            onChange={handleKeyChange}
            onDelete={handleKeyDelete}
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
      <div className="bg-muted p-4 rounded-lg">
        <pre className="text-sm text-foreground whitespace-pre-wrap">
          {objectToYaml(value)}
        </pre>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">{t('editor.statistics')}</h4>
          <div className="space-y-1 text-sm text-muted-foreground">
            <div>{t('editor.totalKeys', { count: Object.keys(value).length })}</div>
            <div>{t('editor.stringValues', { count: Object.values(value).filter(v => typeof v === 'string').length })}</div>
            <div>{t('editor.arrayValues', { count: Object.values(value).filter(v => Array.isArray(v)).length })}</div>
            <div>{t('editor.objectValues', { count: Object.values(value).filter(v => typeof v === 'object' && v !== null && !Array.isArray(v)).length })}</div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">{t('editor.keys')}</h4>
          <div className="flex flex-wrap gap-1">
            {Object.keys(value).map(key => (
              <Badge key={key} variant="info" className="text-xs">
                {key}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <Section title={t('editor.title')}>
      {/* View Mode Selector */}
      <Tabs value={viewMode} onValueChange={(mode) => setViewMode(mode as ViewMode)} className="mb-6">
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
              <ul className="list-disc list-inside">
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
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

export default TemplateEditor;
