/**
 * ApplyChangesBar Component - Save workflow controls
 * 
 * Provides validation and save controls for unsaved changes across all pages,
 * with visual feedback and error handling.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Save,
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Eye,
  X,
  AlertTriangle
} from 'lucide-react';
import {
  ActionBar,
  Alert,
  AlertDescription,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertTitle,
  Button,
} from 'locveil-ui-kit';
import type { ApplyChangesBarProps, ValidationResult } from '@/types';
import { useValidationWorkflow } from '@/hooks';
import { ValidationIndicator, BlockingConflictsDialog } from '@/components/analysis';

/** A pending save-confirmation (UI-21: kit AlertDialog replaces window.confirm). */
interface ConfirmRequest {
  message: string;
  resolve: (proceed: boolean) => void;
}

const ApplyChangesBar: React.FC<ApplyChangesBarProps> = ({
  visible,
  selectedHandler,
  hasUnsavedChanges,
  onSave,
  onValidate,
  onCancel,
  loading = false,
  lastSaved,
  nluContext
}) => {
  const { t } = useTranslation('common');
  const [isApplying, setIsApplying] = useState(false);
  const [showBlockingDialog, setShowBlockingDialog] = useState(false);
  const [confirmRequest, setConfirmRequest] = useState<ConfirmRequest | null>(null);

  // Promise-shaped confirm over the kit AlertDialog — same control flow the old
  // blocking window.confirm gave the save handler.
  const askConfirm = (message: string): Promise<boolean> =>
    new Promise<boolean>((resolve) => setConfirmRequest({ message, resolve }));

  const settleConfirm = (proceed: boolean): void => {
    confirmRequest?.resolve(proceed);
    setConfirmRequest(null);
  };
  const [legacyValidationResult, setLegacyValidationResult] = useState<ValidationResult | null>(null);
  const [isValidatingLegacy, setIsValidatingLegacy] = useState(false);
  
  // Determine if we should use enhanced NLU validation
  const useEnhancedValidation = Boolean(
    nluContext?.enableEnhancedValidation && 
    selectedHandler && 
    nluContext?.language && 
    nluContext?.donationData
  );
  
  // Enhanced validation workflow (only for NLU context)
  const {
    validationResult: nluValidationResult,
    isValidating: isValidatingNLU,
    validateForSaving,
    canSave: canSaveNLU,
    hasBlockingConflicts,
    hasWarnings,
    blockingConflicts,
    warningConflicts,
    clearValidation: clearNLUValidation
  } = useValidationWorkflow({
    onValidationComplete: (result) => {
      console.log('NLU validation completed:', result);
    },
    onValidationError: (error) => {
      console.error('NLU validation error:', error);
    }
  });
  
  // Determine which validation state to use
  const validationResult = useEnhancedValidation ? nluValidationResult : legacyValidationResult;
  const isValidating = useEnhancedValidation ? isValidatingNLU : isValidatingLegacy;
  const canSave = useEnhancedValidation ? canSaveNLU : (legacyValidationResult?.valid !== false);

  // Handle validation (dual mode)
  const handleValidate = async (): Promise<void> => {
    if (!selectedHandler) return;

    if (useEnhancedValidation && nluContext?.language && nluContext?.donationData) {
      // Use enhanced NLU validation
      try {
        await validateForSaving(selectedHandler, nluContext.language, nluContext.donationData);
      } catch (error) {
        console.error('Enhanced validation failed:', error);
      }
    } else {
      // Use legacy validation
      if (!onValidate) return;
      
      setIsValidatingLegacy(true);
      try {
        const result = await onValidate();
        setLegacyValidationResult(result);
      } catch (error) {
        console.error('Legacy validation failed:', error);
        setLegacyValidationResult({
          valid: false,
          errors: [error instanceof Error ? error.message : t('validation.failed')],
          warnings: []
        });
      } finally {
        setIsValidatingLegacy(false);
      }
    }
  };

  // Type guard functions
  const isNLUValidationResult = (result: any): result is import('@/types/api').NLUValidationResult => {
    return result && typeof result === 'object' && 'has_blocking_conflicts' in result;
  };

  const isLegacyValidationResult = (result: any): result is import('@/types/api').ValidationResult => {
    return result && typeof result === 'object' && 'valid' in result;
  };


  // Handle apply/save (dual mode)
  const handleApply = async (): Promise<void> => {
    if (!onSave) return;

    if (useEnhancedValidation) {
      // Enhanced NLU validation workflow
      if (!validationResult) {
        await handleValidate();
        return; // Let user review validation results first
      }

      // BUG-10: blocking conflicts already disable the Apply button (canSaveNLU requires
      // !hasBlockingConflicts), so this handler can't run with blockers — the dialog is opened from
      // the dedicated "Review blocking conflicts" trigger below instead of this unreachable branch.

      // Show warning dialog for warnings
      if (hasWarnings && warningConflicts.length > 0) {
        const proceed = await askConfirm(t('applyBar.confirmWarningsReview'));
        if (!proceed) return;
      }
    } else {
      // Legacy validation workflow
      if (isLegacyValidationResult(validationResult) && !validationResult.valid) {
        const proceed = await askConfirm(t('applyBar.confirmErrors'));
        if (!proceed) return;
      }

      if (isLegacyValidationResult(validationResult) && validationResult.warnings && validationResult.warnings.length > 0) {
        const proceed = await askConfirm(t('applyBar.confirmWarnings'));
        if (!proceed) return;
      }
    }

    setIsApplying(true);
    try {
      await onSave();
      
      // Clear validation state on successful save
      if (useEnhancedValidation) {
        clearNLUValidation();
      } else {
        setLegacyValidationResult(null);
      }
    } catch (error) {
      console.error('Failed to apply changes:', error);
    } finally {
      setIsApplying(false);
    }
  };

  // Handle discard (dual mode)
  const handleDiscard = (): void => {
    if (onCancel) {
      onCancel();
    }
    
    // Clear validation state
    if (useEnhancedValidation) {
      clearNLUValidation();
    } else {
      setLegacyValidationResult(null);
    }
  };

  if (!visible) return null;

  // Determine validation state based on mode
  const hasValidationErrors = useEnhancedValidation 
    ? hasBlockingConflicts 
    : (legacyValidationResult && !legacyValidationResult.valid);
  const hasValidationWarnings = useEnhancedValidation 
    ? hasWarnings 
    : (legacyValidationResult && legacyValidationResult.warnings && legacyValidationResult.warnings.length > 0);
  const canApply = !isApplying && !loading && canSave;

  // UI-22: the bar renders through the kit ActionBar bus — the shell's ActionBarHost
  // (workbench-v1.1 bottom slot) owns the border/surface shell; no fixed positioning.
  return (
    <ActionBar>
      <div className="w-full py-2">
      <div className="flex items-center justify-between">
        {/* Left side - Status */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]" />
            <span className="text-sm text-muted-foreground">
              {hasUnsavedChanges ? (
                selectedHandler ? (
                  <>{t('applyBar.unsavedChangesIn')} <strong>{selectedHandler}</strong></>
                ) : (
                  <>{t('applyBar.unsavedConfigChanges')}</>
                )
              ) : (
                <>{t('applyBar.noPendingChanges')}</>
              )}
            </span>
          </div>

          {lastSaved && (
            <span className="text-xs text-muted-foreground">
              {t('applyBar.lastSaved', { time: lastSaved.toLocaleTimeString() })}
            </span>
          )}
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center space-x-3">
          {/* BUG-10: blocking conflicts disable Apply — this makes the (otherwise unreachable)
              BlockingConflictsDialog reachable so the user can review the blockers. */}
          {useEnhancedValidation && hasBlockingConflicts && (
            <Button
              variant="outline"
              onClick={() => setShowBlockingDialog(true)}
              className="text-destructive hover:text-destructive"
            >
              <AlertTriangle />
              {t('applyBar.reviewBlockingConflicts', { count: blockingConflicts.length })}
            </Button>
          )}

          {/* Validation Button */}
          <Button
            variant="outline"
            onClick={() => void handleValidate()}
            disabled={isValidating || loading}
          >
            {isValidating ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Eye />
            )}
            {isValidating ? t('validation.validating') : t('applyBar.validate')}
          </Button>

          {/* Discard Button */}
          <Button
            variant="outline"
            onClick={handleDiscard}
            disabled={loading || isApplying}
          >
            <X />
            {t('actions.cancel')}
          </Button>

          {/* Apply Button */}
          <Button
            variant={hasValidationErrors ? 'destructive' : 'default'}
            onClick={() => void handleApply()}
            disabled={!canApply}
          >
            {isApplying ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Save />
            )}
            {isApplying ? t('status.saving') : t('applyBar.saveChanges')}
          </Button>
        </div>
      </div>

      {/* Conditional Validation Results */}
      {validationResult && (
        <div className="mt-4">
          {useEnhancedValidation ? (
            // Enhanced NLU validation display
            <ValidationIndicator 
              result={isNLUValidationResult(validationResult) ? validationResult : null} 
              isValidating={isValidating}
            />
          ) : (
            // Legacy validation display
            <div className="space-y-2">
              {/* Errors */}
              {legacyValidationResult?.errors && legacyValidationResult.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle />
                  <div>
                    <AlertTitle>{t('applyBar.validationErrors')}</AlertTitle>
                    <AlertDescription>
                      <ul className="space-y-1">
                        {legacyValidationResult.errors.map((error, index) => (
                          <li key={index} className="list-disc list-inside">
                            {error}
                          </li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </div>
                </Alert>
              )}

              {/* Warnings */}
              {hasValidationWarnings && (
                <Alert>
                  <AlertTriangle className="text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]" />
                  <div>
                    <AlertTitle>{t('applyBar.validationWarnings')}</AlertTitle>
                    <AlertDescription>
                      <ul className="space-y-1">
                        {legacyValidationResult?.warnings?.map((warning, index) => (
                          <li key={index} className="list-disc list-inside">
                            {warning}
                          </li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </div>
                </Alert>
              )}

              {/* Success */}
              {legacyValidationResult?.valid && (!legacyValidationResult.warnings || legacyValidationResult.warnings.length === 0) && (
                <Alert>
                  <CheckCircle2 className="text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]" />
                  <div>
                    <AlertTitle>{t('applyBar.validationSuccessful')}</AlertTitle>
                    <AlertDescription>{t('applyBar.noErrorsReady')}</AlertDescription>
                  </div>
                </Alert>
              )}
            </div>
          )}
        </div>
      )}

      {/* Enhanced NLU Features - Only show when in NLU context */}
      {useEnhancedValidation && showBlockingDialog && (
        // BUG-10: read-only review for now (no `onResolve` → the dialog renders no Resolve buttons,
        // rather than wiring up a stub that did nothing). Real resolution is tracked as UI-15.
        <BlockingConflictsDialog
          conflicts={blockingConflicts}
          onClose={() => setShowBlockingDialog(false)}
        />
      )}

      {/* UI-21: save-confirmation over the kit AlertDialog (was window.confirm ×3) */}
      <AlertDialog
        open={!!confirmRequest}
        onOpenChange={(open) => {
          if (!open) settleConfirm(false);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('applyBar.confirmTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{confirmRequest?.message}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => settleConfirm(false)}>
              {t('actions.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => settleConfirm(true)}>
              {t('applyBar.saveAnyway')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      </div>
    </ActionBar>
  );
};

export default ApplyChangesBar;
