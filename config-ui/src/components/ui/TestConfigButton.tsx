/**
 * TestConfigButton Component - Button for testing configuration via /configure endpoints
 *
 * Handles live configuration testing for all 8 voice assistant components
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { TestTube, Loader } from 'lucide-react';
import { Button, cn, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import type {
  TTSConfig, ASRConfig, AudioConfig, LLMConfig, NLUConfig,
  VoiceTriggerConfig, TextProcessorConfig, IntentSystemConfig,
  TTSConfigureResponse, ASRConfigureResponse, AudioConfigureResponse,
  LLMConfigureResponse, NLUConfigureResponse, VoiceTriggerConfigureResponse,
  TextProcessorConfigureResponse, IntentSystemConfigureResponse
} from '@/types/api';

// Union types for all config types and responses
export type ComponentConfigType =
  | TTSConfig
  | ASRConfig
  | AudioConfig
  | LLMConfig
  | NLUConfig
  | VoiceTriggerConfig
  | TextProcessorConfig
  | IntentSystemConfig;

export type ComponentConfigureResponse =
  | TTSConfigureResponse
  | ASRConfigureResponse
  | AudioConfigureResponse
  | LLMConfigureResponse
  | NLUConfigureResponse
  | VoiceTriggerConfigureResponse
  | TextProcessorConfigureResponse
  | IntentSystemConfigureResponse;

export type ComponentName =
  | 'tts'
  | 'asr'
  | 'audio'
  | 'llm'
  | 'nlu'
  | 'voice_trigger'
  | 'text_processing'
  | 'intent_system';

interface TestConfigButtonProps {
  component: ComponentName;
  config: ComponentConfigType;
  onTest: (component: ComponentName, config: ComponentConfigType) => Promise<ComponentConfigureResponse>;
  loading?: boolean;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'outline';
  showPreview?: boolean; // Show preview of what will be applied
  hasChanges?: boolean; // Whether there are changes to test
}

const kitVariant = { primary: 'default', secondary: 'secondary', outline: 'outline' } as const;
const kitSize = { sm: 'sm', md: 'default', lg: 'lg' } as const;

export const TestConfigButton: React.FC<TestConfigButtonProps> = ({
  component,
  config,
  onTest,
  loading = false,
  disabled = false,
  className = '',
  size = 'md',
  variant = 'outline',
  showPreview = false,
  hasChanges = true
}) => {
  const { t } = useTranslation('common');
  const handleClick = async () => {
    if (disabled || loading) return;

    try {
      await onTest(component, config);
    } catch (error) {
      console.error(`Failed to test ${component} configuration:`, error);
    }
  };

  const getComponentDisplayName = () => {
    const names: Record<ComponentName, string> = {
      tts: 'TTS',
      asr: 'ASR',
      audio: 'Audio',
      llm: 'LLM',
      nlu: 'NLU',
      voice_trigger: 'Voice Trigger',
      text_processing: 'Text Processing',
      intent_system: 'Intent System'
    };
    return names[component];
  };

  const getPreviewText = () => {
    if (!showPreview || !config) return '';

    const preview: string[] = [];

    // Add key configuration details based on component type
    if ('enabled' in config) {
      preview.push(t('workflow.preview.enabled', { value: String(config.enabled) }));
    }
    if ('default_provider' in config && config.default_provider) {
      preview.push(t('workflow.preview.provider', { value: config.default_provider }));
    }
    if ('fallback_providers' in config && config.fallback_providers && config.fallback_providers.length > 0) {
      preview.push(t('workflow.preview.fallbacks', { value: config.fallback_providers.join(', ') }));
    }

    return preview.length > 0 ? `\n\n${t('workflow.preview.willApply')}\n${preview.join('\n')}` : '';
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={kitVariant[variant]}
          size={kitSize[size]}
          onClick={() => void handleClick()}
          disabled={disabled || loading}
          className={className}
        >
          {loading ? <Loader className={cn('animate-spin')} /> : <TestTube />}
          {loading ? t('workflow.testing') : disabled && !hasChanges ? t('workflow.noChanges') : t('workflow.testConfig')}
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <span className="whitespace-pre-line">
          {
            disabled && !hasChanges
              ? t('workflow.noChangesToTest', { component: getComponentDisplayName() })
              : t('workflow.testConfigTitle', { component: getComponentDisplayName(), preview: getPreviewText() })
          }
        </span>
      </TooltipContent>
    </Tooltip>
  );
};

export default TestConfigButton;
