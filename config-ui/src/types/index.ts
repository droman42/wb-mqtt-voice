/**
 * Main type definitions export file
 */

// Re-export all types for easy importing
export * from './api';
export * from './components';
// Donation editor v1.1 types (UI-5): generated contract/phrasing bodies + envelopes.
export * from './donations';

// Common types (UI-13: removed 8 never-imported utility aliases — Maybe/Optional/RequiredKeys/
// ChangeHandler/ClickHandler/AsyncClickHandler/ApiMethod/LoadingState).
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';
