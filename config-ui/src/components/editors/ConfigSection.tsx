/**
 * ConfigSection Component - Collapsible configuration section editor
 * 
 * Implements three-level accordion structure:
 * Level 1: Major sections (collapsed by default)
 * Level 2: Subsections (provider groups, collapsed by default)  
 * Level 3: Key-value pairs (auto-generated from schema)
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, Save, TestTube, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { Alert, AlertDescription, Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import { ConfigWidget } from './ConfigWidgets';
import MicrophoneConfigSection from './MicrophoneConfigSection';
import TestConfigButton, { type ComponentName, type ComponentConfigType, type ComponentConfigureResponse } from '@/components/ui/TestConfigButton';
import ConfigurationStatus from '@/components/ui/ConfigurationStatus';
import WorkflowStatusIndicator, { type WorkflowStateType } from '@/components/ui/WorkflowStatusIndicator';
import WorkflowActionButtons from '@/components/ui/WorkflowActionButtons';
import type { FieldSchema } from './ConfigWidgets';

interface ConfigurationTestState {
  status: 'idle' | 'testing' | 'applied' | 'error';
  message: string;
  testResult?: ComponentConfigureResponse;
  timestamp?: Date;
}

// Phase 4.3: Workflow status interface
interface WorkflowStatus {
  hasChanges: boolean;
  isTested: boolean;
  isPersisted: boolean;
  hasConflicts: boolean;
  canTest: boolean;
  canPersist: boolean;
  testStatus: 'idle' | 'testing' | 'applied' | 'error';
}

interface ConfigSectionProps {
  name: string;
  title?: string;
  data: any;
  schema?: Record<string, FieldSchema>;
  hasChanges?: boolean;
  onChange: (data: any) => void;
  onValidate?: () => Promise<{ valid: boolean; errors?: any[] }>;
  onApply?: () => Promise<any>;
  onTestConfig?: (component: ComponentName, config: ComponentConfigType) => Promise<ComponentConfigureResponse>;
  testState?: ConfigurationTestState;
  disabled?: boolean;
  level?: 1 | 2; // Level 1 = major section, Level 2 = subsection
  componentName?: string; // Original component name for provider lookups
  // UI-16 (E7): the backend-declared live-testable component name for this section
  // (drives the Test/Workflow chrome); null/absent = not a component section.
  testableComponent?: ComponentName | null;
  // Phase 4.3: Enhanced workflow props
  workflowStatus?: WorkflowStatus;
  workflowStateType?: WorkflowStateType;
  onPersistTested?: (component: ComponentName) => Promise<void>;
  onRollbackToPersisted?: (component: ComponentName) => void;
  onRollbackToTested?: (component: ComponentName) => void;
}

export const ConfigSection: React.FC<ConfigSectionProps> = ({
  name,
  title,
  data,
  schema,
  hasChanges = false,
  onChange,
  onValidate,
  onApply,
  onTestConfig,
  testState,
  disabled = false,
  level = 1,
  componentName,
  testableComponent = null,
  // Phase 4.3: Enhanced workflow props
  workflowStatus,
  workflowStateType = 'pristine',
  onPersistTested,
  onRollbackToPersisted,
  onRollbackToTested
}) => {
  const { t } = useTranslation('configuration');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors?: any[] } | null>(null);
  
  const displayTitle = title || name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ');
  
  // Auto-expand if there are validation errors
  useEffect(() => {
    if (validationResult && !validationResult.valid) {
      setIsExpanded(true);
    }
  }, [validationResult]);

  // UI-16 (E7): a section is a live-testable component section iff the backend
  // declared it (`component_sections` on the sections endpoint, passed down as
  // `testableComponent`) — no hardcoded roster, no name-remap table here.
  const isComponentSection = level === 1 && !!testableComponent;

  const getComponentNameForTesting = (): ComponentName | null => {
    return isComponentSection ? (testableComponent ?? null) : null;
  };

  
  const handleValidate = async () => {
    if (!onValidate) return;
    
    setIsValidating(true);
    try {
      const result = await onValidate();
      setValidationResult(result);
    } catch (error) {
      setValidationResult({ 
        valid: false, 
        errors: [{ message: error instanceof Error ? error.message : 'Validation failed' }] 
      });
    } finally {
      setIsValidating(false);
    }
  };
  
  const handleApply = async () => {
    if (!onApply) return;
    
    setIsSaving(true);
    try {
      await onApply();
      setValidationResult(null); // Clear validation state after successful save
    } catch (error) {
      console.error('Apply failed:', error);
    } finally {
      setIsSaving(false);
    }
  };
  
  const updateField = (fieldName: string, value: any) => {
    const newData = { ...data, [fieldName]: value };
    onChange(newData);
    
    // Trigger real-time validation for component sections after a short delay
    if (isComponentSection && onValidate) {
      // Clear any existing timeout to debounce validation calls
      // eslint-disable-next-line @typescript-eslint/no-misused-promises -- fire-and-forget debounced validation
      const timeoutId = setTimeout(async () => {
        try {
          const result = await onValidate();
          setValidationResult(result);
        } catch (error) {
          // Silently handle validation errors for real-time feedback
          console.debug('Real-time validation failed:', error);
        }
      }, 500); // 500ms debounce
      
      // Store timeout ID for cleanup if needed
      return () => clearTimeout(timeoutId);
    }
  };
  
  const renderField = (fieldName: string, fieldSchema: FieldSchema) => {
    return (
      <div key={fieldName} className="p-4 border-l-2 border-border">
        <ConfigWidget
          name={fieldName}
          value={data?.[fieldName]}
          schema={fieldSchema}
          onChange={(value) => updateField(fieldName, value)}
          disabled={disabled}
          path={[name, fieldName]}
          componentName={componentName || name}
        />
      </div>
    );
  };
  
  const renderSubsections = () => {
    if (!data || typeof data !== 'object') return null;
    
    // Detect microphone configuration section
    if (name.includes('microphone') && data.device_id !== undefined) {
      return (
        <MicrophoneConfigSection
          data={data}
          schema={schema}
          onChange={onChange}
          disabled={disabled}
        />
      );
    }
    
    // Detect provider subsections
    if (data.providers && typeof data.providers === 'object') {
      return (
        <div className="space-y-2">
          {/* General settings (non-provider fields) */}
          {schema && (
            <ConfigSection
              name={`${name}_general`}
              title={t('section.generalSettings')}
              data={Object.fromEntries(
                Object.entries(data).filter(([key]) => key !== 'providers')
              )}
              schema={Object.fromEntries(
                Object.entries(schema).filter(([key]) => key !== 'providers')
              )}
              onChange={(generalData) => {
                onChange({ ...data, ...generalData });
              }}
              level={2}
              disabled={disabled}
              componentName={componentName || name}
            />
          )}
          
          {/* Provider subsections */}
          {Object.entries(data.providers).map(([providerName, providerData]) => {
            // Get provider schema from the schema.providers.properties if available
            const providerSchema = schema?.providers?.properties?.[providerName]?.properties;
            
            return (
              <ConfigSection
                key={providerName}
                name={`${name}_${providerName}`}
                title={t('section.providerTitle', { name: providerName.charAt(0).toUpperCase() + providerName.slice(1) })}
                data={providerData}
                schema={providerSchema}
                onChange={(newProviderData) => {
                  const newProviders = { ...data.providers, [providerName]: newProviderData };
                  onChange({ ...data, providers: newProviders });
                }}
                level={2}
                disabled={disabled}
                componentName={componentName || name}
              />
            );
          })}
        </div>
      );
    }
    
    // For non-provider sections, check for nested objects and render appropriately
    if (schema) {
      // Separate nested objects from simple fields
      const nestedObjects: Array<[string, FieldSchema]> = [];
      const simpleFields: Array<[string, FieldSchema]> = [];
      
      Object.entries(schema).forEach(([fieldName, fieldSchema]) => {
        if (fieldSchema.type === 'object' && fieldSchema.properties) {
          nestedObjects.push([fieldName, fieldSchema]);
        } else {
          simpleFields.push([fieldName, fieldSchema]);
        }
      });
      
      return (
        <div className="space-y-4">
          {/* Render simple fields first */}
          {simpleFields.map(([fieldName, fieldSchema]) => 
            renderField(fieldName, fieldSchema)
          )}
          
          {/* Render nested objects as collapsible subsections */}
          {nestedObjects.map(([fieldName, fieldSchema]) => (
            <ConfigSection
              key={fieldName}
              name={`${name}_${fieldName}`}
              title={fieldSchema.description || fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              data={data?.[fieldName]}
              schema={fieldSchema.properties}
              onChange={(nestedData) => {
                onChange({ ...data, [fieldName]: nestedData });
              }}
              level={2}
              disabled={disabled}
              componentName={componentName || name}
            />
          ))}
        </div>
      );
    }
    
    // Fallback: render generic object fields
    return (
      <div className="space-y-4">
        {Object.entries(data).map(([fieldName, value]) => {
          const genericSchema: FieldSchema = {
            type: typeof value === 'boolean' ? 'boolean' : 
                  typeof value === 'number' ? 'number' : 'string',
            description: '',
            required: false
          };
          return renderField(fieldName, genericSchema);
        })}
      </div>
    );
  };
  
  const getStatusIndicator = () => {
    if (isSaving || isValidating) {
      return <Loader className="h-4 w-4 text-primary animate-spin" />;
    }

    if (validationResult) {
      return validationResult.valid ? (
        <CheckCircle className="h-4 w-4 text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]" />
      ) : (
        <AlertCircle className="h-4 w-4 text-destructive" />
      );
    }

    if (hasChanges) {
      return <div className="h-2 w-2 rounded-full bg-[hsl(var(--lv-status-edited)_45%_60%)] dark:bg-[hsl(var(--lv-status-edited)_45%_45%)]" />;
    }

    return null;
  };

  const getCardClass = () => {
    const baseClass = "bg-card border rounded-lg transition-colors duration-200";

    if (level === 1) {
      return `${baseClass} border-border`;
    } else {
      return `${baseClass} border-border`;
    }
  };

  const getHeaderClass = () => {
    const baseClass = "flex items-center justify-between p-4 cursor-pointer transition-colors duration-200";

    if (level === 1) {
      return `${baseClass} hover:bg-muted/60`;
    } else {
      return `${baseClass} hover:bg-muted/40`;
    }
  };
  
  return (
    <div className={getCardClass()}>
      {/* Section Header */}
      <div className={getHeaderClass()} onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center space-x-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <div>
            <h3 className={`font-medium ${level === 1 ? 'text-lg text-foreground' : 'text-base text-foreground'}`}>
              {displayTitle}
            </h3>
            {level === 1 && schema && (
              <p className="text-sm text-muted-foreground mt-1">
                {t('section.settingsCount', { count: Object.keys(schema).length })}
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {getStatusIndicator()}
          
          {/* Phase 4.3: Workflow Status Indicator for Component Sections */}
          {isComponentSection && workflowStatus && isExpanded && (
            <WorkflowStatusIndicator
              status={workflowStatus}
              stateType={workflowStateType}
              size="sm"
              showDetails={false}
            />
          )}
          
          {/* Test Configuration Button for Component Sections */}
          {isComponentSection && onTestConfig && isExpanded && (
            <TestConfigButton
              component={getComponentNameForTesting()!}
              config={data}
              onTest={onTestConfig}
              loading={testState?.status === 'testing'}
              disabled={disabled || !hasChanges} // Only enable when there are changes
              hasChanges={hasChanges} // Pass changes state for better UX
              size="sm"
              variant="outline"
              showPreview={true}
            />
          )}

          {/* Phase 4.3: Workflow Action Buttons for Component Sections */}
          {isComponentSection && workflowStatus && onPersistTested && onRollbackToPersisted && onRollbackToTested && isExpanded && (
            <WorkflowActionButtons
              component={getComponentNameForTesting()!}
              status={workflowStatus}
              onPersistTested={onPersistTested}
              onRollbackToPersisted={onRollbackToPersisted}
              onRollbackToTested={onRollbackToTested}
              size="sm"
            />
          )}
          
          {hasChanges && isExpanded && level === 1 && (
            <div className="flex items-center space-x-2">
              {onValidate && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleValidate();
                      }}
                      disabled={isValidating || disabled}
                      className="h-7 w-7"
                      aria-label={t('section.validateSection')}
                    >
                      <TestTube />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{t('section.validateSection')}</TooltipContent>
                </Tooltip>
              )}

              {onApply && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleApply();
                      }}
                      disabled={isSaving || disabled}
                      className="h-7 w-7 text-primary"
                      aria-label={t('section.applyChanges')}
                    >
                      <Save />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{t('section.applyChanges')}</TooltipContent>
                </Tooltip>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Validation Errors */}
      {isExpanded && validationResult && !validationResult.valid && (
        <div className="px-4 pb-2">
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>
              <span className="font-medium">{t('section.validationErrors')}</span>
              <ul className="mt-2 space-y-1">
                {validationResult.errors?.map((error, index) => (
                  <li key={index}>• {error.message || error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Configuration Test Status */}
      {isExpanded && isComponentSection && testState && testState.status !== 'idle' && (
        <div className="px-4 pb-2">
          <ConfigurationStatus
            status={testState.status === 'testing' ? 'testing' : 
                   testState.status === 'applied' ? 'applied' : 'error'}
            message={testState.message}
            testResult={testState.testResult}
          />
        </div>
      )}
      
      {/* Section Content */}
      {isExpanded && (
        <div className="border-t border-border">
          <div className="p-4">
            {renderSubsections()}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigSection;
