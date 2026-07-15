/**
 * WorkflowStatusIndicator Component - Shows the current state in the Test → Validate → Persist workflow
 *
 * Provides visual indicators for configuration workflow states in Phase 4.3
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, TestTube, Save, AlertTriangle, Clock, FileText } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { StatusChip, Icon, cn, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';

// The local state enum IS the kit's StatusVariant set (the council took these
// workflow states as the canonical status vocabulary — stylebook §2).
export type WorkflowStateType = 'pristine' | 'edited' | 'tested' | 'persisted' | 'conflict';

interface WorkflowStatus {
  hasChanges: boolean;
  isTested: boolean;
  isPersisted: boolean;
  hasConflicts: boolean;
  canTest: boolean;
  canPersist: boolean;
  testStatus: 'idle' | 'testing' | 'applied' | 'error';
}

interface WorkflowStatusIndicatorProps {
  status: WorkflowStatus;
  stateType: WorkflowStateType;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
}

const stateIcon: Record<WorkflowStateType, LucideIcon> = {
  pristine: FileText,
  edited: Clock,
  tested: TestTube,
  persisted: CheckCircle,
  conflict: AlertTriangle,
};

export const WorkflowStatusIndicator: React.FC<WorkflowStatusIndicatorProps> = ({
  status,
  stateType,
  className = '',
  showDetails = false
}) => {
  const { t } = useTranslation('common');

  const getWorkflowSteps = () => {
    const steps = [
      {
        id: 'edit',
        name: t('workflow.steps.edit'),
        completed: status.hasChanges,
        active: status.hasChanges && !status.isTested,
        icon: Clock
      },
      {
        id: 'test',
        name: t('workflow.steps.test'),
        completed: status.isTested,
        active: status.isTested && !status.isPersisted,
        icon: TestTube
      },
      {
        id: 'persist',
        name: t('workflow.steps.persist'),
        completed: status.isPersisted && status.isTested,
        active: false,
        icon: Save
      }
    ];

    return steps;
  };

  const chip = (
    <StatusChip variant={stateType} className={showDetails ? undefined : className}>
      <Icon icon={stateIcon[stateType]} className="mr-1" />
      {t(`workflow.states.${stateType}.label`)}
    </StatusChip>
  );

  if (!showDetails) return chip;

  return (
    <div className={cn('inline-flex flex-col gap-1', className)}>
      {chip}
      <span className="text-xs text-muted-foreground">
        {t(`workflow.states.${stateType}.description`)}
      </span>
      {/* Workflow progress steps */}
      <div className="flex items-center gap-1">
        {getWorkflowSteps().map((step, index) => (
          <div key={step.id} className="flex items-center">
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={cn(
                    'flex h-4 w-4 items-center justify-center rounded-full border',
                    step.completed
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : step.active
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-muted text-muted-foreground'
                  )}
                  aria-label={t('workflow.stepTitle', {
                    step: step.name,
                    status: step.completed
                      ? t('workflow.stepStatus.completed')
                      : step.active
                      ? t('workflow.stepStatus.active')
                      : t('workflow.stepStatus.pending')
                  })}
                >
                  <step.icon className="h-3 w-3" />
                </span>
              </TooltipTrigger>
              <TooltipContent>
                {t('workflow.stepTitle', {
                  step: step.name,
                  status: step.completed
                    ? t('workflow.stepStatus.completed')
                    : step.active
                    ? t('workflow.stepStatus.active')
                    : t('workflow.stepStatus.pending')
                })}
              </TooltipContent>
            </Tooltip>
            {index < getWorkflowSteps().length - 1 && (
              <span className={cn('mx-0.5 h-0.5 w-2', step.completed ? 'bg-primary/40' : 'bg-border')} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowStatusIndicator;
