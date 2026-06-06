/**
 * Main type definitions export file
 */

// Re-export all types for easy importing
export * from './api';
export * from './components';
// Donation editor v1.1 types (UI-5): generated contract/phrasing bodies + envelopes.
export * from './donations';

// Common utility types
export type Maybe<T> = T | null | undefined;
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredKeys<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

// Event handler types
export type ChangeHandler<T> = (value: T) => void;
export type ClickHandler = () => void;
export type AsyncClickHandler = () => Promise<void>;

// Common API types
export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';
