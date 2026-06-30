/**
 * TypeScript type definitions for React component props and state
 */

import { ReactNode } from 'react';
import { DonationData, DonationListItem, ValidationResult, JsonSchema, HandlerLanguageInfo } from './api';

// UI Component Props
export interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'custom';
  className?: string;
}

export interface InputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  required?: boolean;
  type?: 'text' | 'password' | 'email' | 'number';
  className?: string;
}

export interface TextAreaProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  required?: boolean;
  rows?: number;
  className?: string;
}

export interface ToggleProps {
  label?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export interface SectionProps {
  title: string;
  children: ReactNode;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  className?: string;
  badge?: ReactNode;
  actions?: ReactNode;
}

// Layout Component Props
export interface LayoutProps {
  children: ReactNode;
}

export interface SidebarProps {
  collapsed: boolean;
  onToggle: (collapsed: boolean) => void;
}

export interface HeaderProps {
  connectionStatus?: 'connected' | 'disconnected' | 'connecting';
  systemInfo?: {
    version?: string;
    uptime?: string;
    handlersCount?: number;
    donationsCount?: number;
  };
}

// Editor Component Props
export interface ArrayOfStringsEditorProps {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

// UI-5: the v1.0 monolithic `Parameter` type + `ParameterListEditorProps` removed with the
// ParameterListEditor/ParameterSpecEditor components — structural params are now edited by ContractEditor
// against the generated contract types.

// UI-13: removed dead TokenPatternsEditorProps + SlotPatternsEditorProps (superseded by the UI-5
// card editors; never imported).

export interface ExamplesEditorProps {
  value: Array<string | { text: string; parameters: Record<string, any> }>;
  onChange: (value: Array<string | { text: string; parameters: Record<string, any> }>) => void;
  globalParams?: string[];
  disabled?: boolean;
}

// UI-13: removed dead HandlerListProps (the live HandlerList uses HandlerLanguageListProps).

export interface ApplyChangesBarProps {
  visible: boolean;
  selectedHandler?: string;
  hasUnsavedChanges: boolean;
  onSave: () => Promise<void>;
  onValidate: () => Promise<ValidationResult>;
  onCancel: () => void;
  loading?: boolean;
  lastSaved?: Date;
  
  // Optional NLU enhancement context
  nluContext?: {
    language?: string;
    donationData?: any;
    enableEnhancedValidation?: boolean;
  };
}

export interface MethodDonationEditorProps {
  value: DonationData;
  onChange: (value: DonationData) => void;
  globalParamNames: string[];
  schema?: JsonSchema;
  validationResult?: ValidationResult;
  disabled?: boolean;
  showRawJson?: boolean;
  onToggleRawJson?: () => void;
}

// Page Component Props and State
export interface DonationsPageState {
  donations: Record<string, DonationData>;
  originalDonations: Record<string, DonationData>;
  donationsList: DonationListItem[];
  schema: JsonSchema | null;
  selectedHandler: string | null;
  hasChanges: Record<string, boolean>;
  searchQuery: string;
  filterDomain: string;
  filterMethodCount: string;
  filterModified: boolean;
  bulkSelection: string[];
  showRawJson: boolean;
  loading: boolean;
  error: string | null;
  validationResults: Record<string, ValidationResult>;
  lastSaved: Date | null;
}

// UI-13: removed dead "for future use" types never imported anywhere — SearchFilters,
// BulkOperationResult, ConfigSection (+ ConfigField), MonitoringData.

// ============================================================
// LANGUAGE-AWARE COMPONENT PROPS (Phase 3)
// ============================================================

// Language-aware HandlerList component props (Phase 3)
export interface HandlerLanguageListProps {
  handlers: HandlerLanguageInfo[];
  selectedHandler: string | null;
  selectedLanguage: string | null;
  onSelect: (handlerName: string) => void;
  onLanguageSelect: (handlerName: string, language: string) => void;
  onCreateLanguage: (handlerName: string, language: string, copyFrom?: string) => void;
  onDeleteLanguage: (handlerName: string, language: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  filterLanguageCount: 'all' | 'single' | 'multiple';
  onFilterLanguageCountChange: (filter: 'all' | 'single' | 'multiple') => void;
  hasChanges?: Record<string, Record<string, boolean>>; // handler -> language -> hasChanges
  loading?: boolean;
  error?: string | null;
}
