/**
 * Configuration Widgets - Generic and specialized input widgets for TOML configuration
 * 
 * Provides auto-generated widgets based on Pydantic field metadata with specialized
 * widgets for complex configuration types like environment variables and provider selection.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Eye, EyeOff, Info } from 'lucide-react';
import { Alert, AlertDescription, Button, Checkbox, Input, Label, Slider, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import apiClient from '@/utils/apiClient';
import KeyValueEditor from './KeyValueEditor';
import type { ConfigFieldSchema } from '@/types/api';

// Shared token-styled class for native <select> controls (kept native because their
// option lists legitimately use empty-string "default/placeholder" values, which the
// radix Select forbids).
const nativeSelectClass =
  'w-full appearance-none rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50';

// ============================================================
// WIDGET INTERFACES
// ============================================================

// Use the imported type instead of defining locally
export type FieldSchema = ConfigFieldSchema;

export interface ConfigWidgetProps {
  name: string;
  value: any;
  schema: FieldSchema;
  onChange: (value: any) => void;
  disabled?: boolean;
  path?: string[]; // For nested configuration paths
}

// ============================================================
// BASIC WIDGETS
// ============================================================

export const BooleanWidget: React.FC<ConfigWidgetProps> = ({ 
  name, value, schema, onChange, disabled 
}) => {
  return (
    <div className="flex items-center space-x-3">
      <Checkbox
        id={name}
        checked={value ?? schema.default ?? false}
        onCheckedChange={(state) => onChange(state === true)}
        disabled={disabled}
      />
      <label htmlFor={name} className="flex-1">
        <span className="text-sm font-medium text-foreground">{name}</span>
        {schema.description && (
          <div className="flex items-center mt-1">
            <Info className="h-3 w-3 text-muted-foreground mr-1" />
            <span className="text-xs text-muted-foreground">{schema.description}</span>
          </div>
        )}
      </label>
    </div>
  );
};

export const StringWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        type="text"
        id={name}
        value={value ?? schema.default ?? ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={schema.default ? t('widgets.defaultPrefix', { value: schema.default }) : undefined}
      />
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const NumberWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  const isInteger = schema.type === 'integer';
  const step = isInteger ? 1 : 0.1;
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        type="number"
        id={name}
        value={value ?? schema.default ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          if (val === '') {
            onChange(null);
          } else {
            onChange(isInteger ? parseInt(val, 10) : parseFloat(val));
          }
        }}
        step={step}
        disabled={disabled}
        placeholder={schema.default ? t('widgets.defaultPrefix', { value: schema.default }) : undefined}
      />
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const ArrayWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  const arrayValue = Array.isArray(value) ? value : (schema.default || []);
  
  const addItem = () => {
    onChange([...arrayValue, '']);
  };
  
  const removeItem = (index: number) => {
    const newArray = arrayValue.filter((_: any, i: number) => i !== index);
    onChange(newArray);
  };
  
  const updateItem = (index: number, newValue: string) => {
    const newArray = [...arrayValue];
    newArray[index] = newValue;
    onChange(newArray);
  };
  
  return (
    <div className="space-y-2">
      <Label>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>

      <div className="space-y-2">
        {arrayValue.map((item: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <Input
              type="text"
              value={item}
              onChange={(e) => updateItem(index, e.target.value)}
              disabled={disabled}
              className="flex-1"
              placeholder={t('widgets.itemPlaceholder', { number: index + 1 })}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeItem(index)}
              disabled={disabled}
              className="text-destructive"
            >
              ×
            </Button>
          </div>
        ))}

        <Button
          type="button"
          variant="link"
          size="sm"
          onClick={addItem}
          disabled={disabled}
        >
          {t('widgets.addItem')}
        </Button>
      </div>

      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

// ============================================================
// SPECIALIZED WIDGETS
// ============================================================

export const EnvironmentVariableWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  const [showValue, setShowValue] = useState(false);
  const isEnvVar = typeof value === 'string' && value.startsWith('${') && value.endsWith('}');
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
        {isEnvVar && (
          <Badge variant="success" className="ml-2">
            {t('widgets.envVar.badge')}
          </Badge>
        )}
      </Label>
      <div className="relative">
        <Input
          type={showValue ? "text" : "password"}
          id={name}
          value={value ?? schema.default ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={t('widgets.envVar.placeholder')}
          className="pr-10"
        />
        <button
          type="button"
          onClick={() => setShowValue(!showValue)}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
        >
          {showValue ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
      <div className="text-xs text-muted-foreground">
        {t('widgets.envVar.hint')}
      </div>
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const ProviderSelectWidget: React.FC<ConfigWidgetProps & { 
  componentName?: string 
}> = ({ 
  name, value, schema, onChange, disabled, componentName, path
}) => {
  const { t } = useTranslation('configuration');
  const [providers, setProviders] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  
  // Determine component name from path if not provided
  const inferredComponent = componentName || (path && path[0]);
  
  useEffect(() => {
    if (inferredComponent) {
      void loadProviders();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [inferredComponent]);
  
  const loadProviders = async () => {
    if (!inferredComponent) return;
    
    setLoading(true);
    try {
      const providerData = await apiClient.getAvailableProviders(inferredComponent);
      setProviders(providerData);
    } catch (error) {
      console.warn(`Failed to load providers for ${inferredComponent}:`, error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="relative">
        <select
          id={name}
          value={value ?? schema.default ?? ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled || loading}
          className={nativeSelectClass}
        >
          <option value="">{t('widgets.provider.select')}</option>
          {Object.entries(providers).map(([key, provider]) => (
            <option key={key} value={key}>
              {provider.name || key} {provider.version && `(${provider.version})`}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>
      {loading && (
        <div className="text-xs text-muted-foreground">{t('widgets.provider.loading')}</div>
      )}
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const InputSelectWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  // Define available input sources
  const inputSources = [
    { value: 'microphone', label: t('widgets.input.microphone') },
    { value: 'web', label: t('widgets.input.web') },
    { value: 'cli', label: t('widgets.input.cli') }
  ];
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="relative">
        <select
          id={name}
          value={value ?? schema.default ?? ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          className={nativeSelectClass}
        >
          <option value="">{t('widgets.input.select')}</option>
          {inputSources.map((source) => (
            <option key={source.value} value={source.value}>
              {source.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const MicrophoneSelectWidget: React.FC<ConfigWidgetProps & { 
  onDeviceChange?: (deviceInfo: any) => void 
}> = ({ 
  name, value, schema, onChange, disabled, onDeviceChange
}) => {
  const { t } = useTranslation('configuration');
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void loadAudioDevices();
  }, []);
  
  const loadAudioDevices = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getAvailableAudioDevices();
      if (response.success) {
        setDevices(response.devices);
      } else {
        console.warn('Failed to load audio devices:', response.message);
        setDevices([]);
      }
    } catch (error) {
      console.warn('Failed to load audio devices:', error);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleDeviceChange = (deviceId: string) => {
    const numericId = deviceId === '' ? null : parseInt(deviceId, 10);
    onChange(numericId);
    
    // Notify parent about device info for auto-populating other fields
    if (onDeviceChange && deviceId !== '') {
      const selectedDevice = devices.find(d => d.id === numericId);
      if (selectedDevice) {
        onDeviceChange(selectedDevice);
      }
    }
  };
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="relative">
        <select
          id={name}
          value={value === null ? '' : value?.toString() || ''}
          onChange={(e) => handleDeviceChange(e.target.value)}
          disabled={disabled || loading}
          className={nativeSelectClass}
        >
          <option value="">{t('widgets.device.default')}</option>
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.name} {device.is_default ? t('widgets.device.systemDefault') : ''} - {device.channels}ch, {device.sample_rate}Hz
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>
      {loading && (
        <div className="text-xs text-muted-foreground">{t('widgets.device.loading')}</div>
      )}
      {!loading && devices.length === 0 && (
        <div className="text-xs text-destructive">{t('widgets.device.none')}</div>
      )}
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const AudioOutputSelectWidget: React.FC<ConfigWidgetProps & { 
  onDeviceChange?: (deviceInfo: any) => void 
}> = ({ 
  name, value, schema, onChange, disabled, onDeviceChange
}) => {
  const { t } = useTranslation('configuration');
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void loadAudioOutputDevices();
  }, []);
  
  const loadAudioOutputDevices = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getAvailableAudioOutputDevices();
      if (response.success) {
        setDevices(response.devices);
      } else {
        console.warn('Failed to load audio output devices:', response.message);
        setDevices([]);
      }
    } catch (error) {
      console.warn('Failed to load audio output devices:', error);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleDeviceChange = (deviceId: string) => {
    const numericId = deviceId === '' ? null : parseInt(deviceId, 10);
    onChange(numericId);
    
    // Notify parent about device info for auto-populating other fields
    if (onDeviceChange && deviceId !== '') {
      const selectedDevice = devices.find(d => d.id === numericId);
      if (selectedDevice) {
        onDeviceChange(selectedDevice);
      }
    }
  };
  
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="relative">
        <select
          id={name}
          value={value === null ? '' : value?.toString() || ''}
          onChange={(e) => handleDeviceChange(e.target.value)}
          disabled={disabled || loading}
          className={nativeSelectClass}
        >
          <option value="">{t('widgets.device.defaultOutput')}</option>
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.name} {device.is_default ? t('widgets.device.systemDefault') : ''} - {device.channels}ch, {device.sample_rate}Hz
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>
      {loading && (
        <div className="text-xs text-muted-foreground">{t('widgets.device.loadingOutput')}</div>
      )}
      {!loading && devices.length === 0 && (
        <div className="text-xs text-destructive">{t('widgets.device.noneOutput')}</div>
      )}
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const ReadOnlyWidget: React.FC<ConfigWidgetProps> = ({
  name, value, schema
}) => {
  const { t } = useTranslation('configuration');
  const displayValue = value ?? schema.default ?? t('widgets.readOnly.notSet');
  
  return (
    <div className="space-y-1">
      <Label>
        {name}
      </Label>
      <div className="w-full px-3 py-2 border border-input rounded-md bg-muted text-muted-foreground text-sm">
        {displayValue}
      </div>
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

export const RangeSliderWidget: React.FC<ConfigWidgetProps> = ({ 
  name, value, schema, onChange, disabled 
}) => {
  const min = schema.constraints?.ge ?? schema.constraints?.gt ?? 0;
  const max = schema.constraints?.le ?? schema.constraints?.lt ?? 1;
  const step = schema.type === 'integer' ? 1 : 0.01;
  const currentValue = value ?? schema.default ?? min;
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={name}>
          {name}
          {schema.required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <span className="text-sm text-muted-foreground">{currentValue}</span>
      </div>
      <Slider
        id={name}
        min={min}
        max={max}
        step={step}
        value={[currentValue]}
        onValueChange={([val]) => {
          onChange(schema.type === 'integer' ? Math.round(val) : val);
        }}
        disabled={disabled}
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{min}</span>
        <span>{max}</span>
      </div>
      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

/**
 * Editor for an array of structured objects, driven by `schema.items.properties`
 * (e.g. wake_words: WakeWordSpec[] — QUAL-20). Each entry is a row of one input per item
 * property. Generic: works for any array-of-objects schema.
 */
export const ArrayOfObjectsEditor: React.FC<ConfigWidgetProps> = ({
  name, value, schema, onChange, disabled
}) => {
  const { t } = useTranslation('configuration');
  const itemProps = schema.items?.properties || {};
  const propNames = Object.keys(itemProps);
  const arrayValue: Record<string, any>[] = Array.isArray(value) ? value : (schema.default || []);

  const blankItem = (): Record<string, any> => {
    const item: Record<string, any> = {};
    for (const [p, ps] of Object.entries(itemProps)) {
      item[p] = ps.default ?? (ps.type === 'number' || ps.type === 'integer' ? 0 : ps.type === 'boolean' ? false : '');
    }
    return item;
  };

  const addItem = () => onChange([...arrayValue, blankItem()]);
  const removeItem = (index: number) => onChange(arrayValue.filter((_, i) => i !== index));
  const updateField = (index: number, prop: string, fieldValue: any) => {
    onChange(arrayValue.map((row, i) => (i === index ? { ...row, [prop]: fieldValue } : row)));
  };

  return (
    <div className="space-y-2">
      <Label>
        {name}
        {schema.required && <span className="text-destructive ml-1">*</span>}
      </Label>

      <div className="space-y-3">
        {arrayValue.map((row, index) => (
          <div key={index} className="border border-border rounded-md p-3 space-y-2 bg-muted">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">#{index + 1}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeItem(index)}
                disabled={disabled}
                className="h-6 px-2 text-destructive"
              >
                ×
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {propNames.map((prop) => {
                const ps = itemProps[prop];
                const isNumber = ps.type === 'number' || ps.type === 'integer';
                const field = (
                  <Input
                    type={isNumber ? 'number' : 'text'}
                    value={row?.[prop] ?? ''}
                    onChange={(e) => updateField(index, prop, isNumber ? Number(e.target.value) : e.target.value)}
                    disabled={disabled}
                    className="h-8 px-2"
                  />
                );
                return (
                  <div key={prop} className="flex flex-col">
                    <label className="text-xs text-muted-foreground">{prop}</label>
                    {ps.description ? (
                      <Tooltip>
                        <TooltipTrigger asChild>{field}</TooltipTrigger>
                        <TooltipContent>{ps.description}</TooltipContent>
                      </Tooltip>
                    ) : (
                      field
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        <Button
          type="button"
          variant="link"
          size="sm"
          onClick={addItem}
          disabled={disabled}
        >
          {t('widgets.addItem')}
        </Button>
      </div>

      {schema.description && (
        <div className="flex items-center">
          <Info className="h-3 w-3 text-muted-foreground mr-1" />
          <span className="text-xs text-muted-foreground">{schema.description}</span>
        </div>
      )}
    </div>
  );
};

// ============================================================
// WIDGET FACTORY
// ============================================================

export const ConfigWidget: React.FC<ConfigWidgetProps & {
  componentName?: string
}> = (props) => {
  const { t } = useTranslation('configuration');
  const { name, value, schema, componentName } = props;
  
  // A value that IS an env reference renders as the env-var widget regardless of
  // schema (the reference may be set on any string field at runtime).
  if (typeof value === 'string' && value.startsWith('${')) {
    return <EnvironmentVariableWidget {...props} />;
  }

  // UI-16 (E9): specialized widgets are SCHEMA-DRIVEN — the backend declares
  // `widget` on the field (json_schema_extra); the old name/path heuristics are gone.
  switch (schema.widget) {
    case 'env_var':
      return <EnvironmentVariableWidget {...props} />;
    case 'provider_select':
      return <ProviderSelectWidget {...props} componentName={componentName} />;
    case 'input_select':
      return <InputSelectWidget {...props} />;
    case 'microphone_select':
      return <MicrophoneSelectWidget {...props} />;
    case 'audio_output_select':
      return <AudioOutputSelectWidget {...props} />;
    case 'readonly':
      return <ReadOnlyWidget {...props} />;
  }
  
  if (schema.constraints && (schema.constraints.ge !== undefined || schema.constraints.le !== undefined) && schema.type === 'number') {
    return <RangeSliderWidget {...props} />;
  }
  
  // Default widget based on type
  switch (schema.type) {
    case 'boolean':
      return <BooleanWidget {...props} />;
    case 'integer':
    case 'number':
      return <NumberWidget {...props} />;
    case 'array':
      // Arrays of structured objects (e.g. wake_words: WakeWordSpec[]) get a per-field editor;
      // plain arrays (string lists) keep the simple ArrayWidget. QUAL-20.
      if (schema.items?.type === 'object' && schema.items.properties) {
        return <ArrayOfObjectsEditor {...props} />;
      }
      return <ArrayWidget {...props} />;
    case 'object':
      // Free-form maps (Dict[str, X]) carry no fixed `properties`; render an editable
      // key/value table so domain_priorities and similar dict fields are usable.
      if (!schema.properties) {
        return (
          <div className="space-y-1">
            <KeyValueEditor
              label={name}
              object={(value as Record<string, any>) ?? {}}
              onChange={props.onChange}
              disabled={props.disabled}
            />
            {schema.description && (
              <div className="flex items-center">
                <span className="text-xs text-muted-foreground">{schema.description}</span>
              </div>
            )}
          </div>
        );
      }
      // Fixed-shape objects carry `properties` and should be routed to a collapsible
      // ConfigSection upstream; reaching here means a real routing bug, so keep the warning.
      return (
        <div className="space-y-1">
          <Label>
            {name}
            {schema.required && <span className="text-destructive ml-1">*</span>}
          </Label>
          <Alert variant="accent">
            <Info />
            <AlertDescription>{t('widgets.objectFieldWarning')}</AlertDescription>
          </Alert>
          {schema.description && (
            <div className="flex items-center">
              <span className="text-xs text-muted-foreground">{schema.description}</span>
            </div>
          )}
        </div>
      );
    case 'string':
    default:
      return <StringWidget {...props} />;
  }
};

export default ConfigWidget;
