import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../lib/api';

interface OnboardingState {
  requiresSetup: boolean;
  setupComplete: boolean;
  bootstrapMode: boolean; // True when services not yet started
  servicesRunning: boolean; // True when pgserve+Python are running
  currentStep: 'setup' | 'api-key' | 'complete';
  isLoading: boolean;
  error: string | null;
}

interface OnboardingContextValue extends OnboardingState {
  checkSetupStatus: () => Promise<void>;
  completeSetup: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

const OnboardingContext = createContext<OnboardingContextValue | undefined>(undefined);

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (context === undefined) {
    throw new Error('useOnboarding must be used within OnboardingProvider');
  }
  return context;
}

interface OnboardingProviderProps {
  children: ReactNode;
}

export function OnboardingProvider({ children }: OnboardingProviderProps) {
  const [state, setState] = useState<OnboardingState>({
    requiresSetup: true, // Assume setup needed until backend confirms otherwise
    setupComplete: false, // Assume not complete until verified
    bootstrapMode: false, // Will be set by Gateway check
    servicesRunning: false, // Will be set based on service availability
    currentStep: 'setup', // Start at setup step
    isLoading: true,
    error: null,
  });

  // Fetch setup status from backend on mount
  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // STEP 1: Check Gateway bootstrap status first (always available)
      // This tells us if services have been started yet
      const gatewayResponse = await fetch('/api/internal/setup/status');
      const gatewayStatus = await gatewayResponse.json();

      if (gatewayStatus.bootstrapMode) {
        // Bootstrap mode: services not started yet
        // Show wizard - user needs to configure and start services
        setState({
          requiresSetup: true,
          setupComplete: false,
          bootstrapMode: true,
          servicesRunning: false,
          currentStep: 'setup',
          isLoading: false,
          error: null,
        });
        return;
      }

      // STEP 2: Gateway says services are running - check Python API
      const response = await api.setup.status();

      setState({
        requiresSetup: response.requires_setup,
        setupComplete: !response.requires_setup,
        bootstrapMode: false,
        servicesRunning: true,
        currentStep: response.requires_setup ? 'setup' : 'complete',
        isLoading: false,
        error: null,
      });

      // Cache in localStorage for quick subsequent checks
      localStorage.setItem('omni_setup_complete', response.requires_setup ? 'false' : 'true');
    } catch (error) {
      console.error('Failed to check setup status:', error);
      // If Gateway check fails, something is very broken
      // If Python check fails but Gateway worked, we're in bootstrap mode
      setState((prev) => ({
        ...prev,
        requiresSetup: true,
        setupComplete: false,
        bootstrapMode: true, // Assume bootstrap if we can't reach services
        servicesRunning: false,
        currentStep: 'setup',
        isLoading: false,
        error: null, // Don't show error - wizard will handle bootstrap
      }));
    }
  };

  const completeSetup = async () => {
    try {
      // Step 1: Complete Python setup (saves to database)
      try {
        await api.setup.complete();
      } catch (setupErr) {
        console.warn('Failed to complete Python setup (continuing):', setupErr);
      }

      // Step 2: Complete Gateway setup (creates marker file for future restarts)
      try {
        await fetch('/api/internal/setup/complete', { method: 'POST' });
      } catch (gatewayErr) {
        console.warn('Failed to mark Gateway setup complete:', gatewayErr);
        // Don't throw - Python setup is the important one
      }

      // Update state to reflect completion
      setState({
        requiresSetup: false,
        setupComplete: true,
        bootstrapMode: false,
        servicesRunning: true,
        currentStep: 'complete',
        isLoading: false,
        error: null,
      });

      // Update cache
      localStorage.setItem('omni_setup_complete', 'true');
    } catch (error) {
      console.error('Failed to complete setup:', error);
      throw error;
    }
  };

  const refreshStatus = async () => {
    await checkSetupStatus();
  };

  const value: OnboardingContextValue = {
    ...state,
    checkSetupStatus,
    completeSetup,
    refreshStatus,
  };

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}
