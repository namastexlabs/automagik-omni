import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { PlatformSelector, type Platform } from './PlatformSelector';
import { ConnectionNamer } from './ConnectionNamer';
import { WhatsAppConnector } from './WhatsAppConnector';
import { DiscordConnector } from './DiscordConnector';

type WizardStep = 'platform' | 'name' | 'connect';

interface WizardState {
  step: WizardStep;
  platform: Platform | null;
  name: string;
}

interface ConnectionWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (instanceName: string, channelType: string) => void;
}

export function ConnectionWizard({ open, onOpenChange, onSuccess }: ConnectionWizardProps) {
  const [state, setState] = useState<WizardState>({
    step: 'platform',
    platform: null,
    name: '',
  });

  // Reset state when dialog closes
  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      // Reset state after close animation
      setTimeout(() => {
        setState({
          step: 'platform',
          platform: null,
          name: '',
        });
      }, 200);
    }
    onOpenChange(isOpen);
  };

  const handlePlatformSelect = (platform: Platform) => {
    setState((prev) => ({
      ...prev,
      platform,
      step: 'name',
    }));
  };

  const handleNameBack = () => {
    setState((prev) => ({
      ...prev,
      step: 'platform',
      platform: null,
      name: '',
    }));
  };

  const handleNameNext = (name: string) => {
    setState((prev) => ({
      ...prev,
      name,
      step: 'connect',
    }));
  };

  const handleConnectBack = () => {
    setState((prev) => ({
      ...prev,
      step: 'name',
    }));
  };

  const handleConnectSuccess = () => {
    if (onSuccess && state.platform) {
      onSuccess(state.name, state.platform);
    }
    handleOpenChange(false);
  };

  // Calculate step number for progress indicator
  const stepNumber = state.step === 'platform' ? 1 : state.step === 'name' ? 2 : 3;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Add Connection</DialogTitle>
            <span className="text-xs text-muted-foreground font-medium">Step {stepNumber} of 3</span>
          </div>
          <DialogDescription>
            {state.step === 'platform' && 'Connect your messaging platform to Omni'}
            {state.step === 'name' && 'Give your connection a name'}
            {state.step === 'connect' &&
              (state.platform === 'whatsapp' ? 'Scan the QR code to connect' : 'Enter your bot credentials')}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex gap-2 py-2">
          {[1, 2, 3].map((num) => (
            <div
              key={num}
              className={`h-1 flex-1 rounded-full transition-colors ${num <= stepNumber ? 'bg-primary' : 'bg-muted'}`}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="py-4">
          {state.step === 'platform' && <PlatformSelector onSelect={handlePlatformSelect} />}

          {state.step === 'name' && state.platform && (
            <ConnectionNamer
              platform={state.platform}
              initialName={state.name}
              onBack={handleNameBack}
              onNext={handleNameNext}
            />
          )}

          {state.step === 'connect' && state.platform === 'whatsapp' && (
            <WhatsAppConnector instanceName={state.name} onBack={handleConnectBack} onSuccess={handleConnectSuccess} />
          )}

          {state.step === 'connect' && state.platform === 'discord' && (
            <DiscordConnector instanceName={state.name} onBack={handleConnectBack} onSuccess={handleConnectSuccess} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Re-export types for convenience
export type { Platform } from './PlatformSelector';
