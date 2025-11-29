import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../lib/api';

interface OnboardingState {
  requiresSetup: boolean;
  setupComplete: boolean;
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
    requiresSetup: true,      // Assume setup needed until backend confirms otherwise
    setupComplete: false,     // Assume not complete until verified
    currentStep: 'setup',     // Start at setup step
    isLoading: true,
    error: null,
  });

  // Fetch setup status from backend on mount
  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await api.setup.status();

      setState({
        requiresSetup: response.requires_setup,
        setupComplete: !response.requires_setup,
        currentStep: response.requires_setup ? 'setup' : 'complete',
        isLoading: false,
        error: null,
      });

      // Cache in localStorage for quick subsequent checks
      localStorage.setItem(
        'omni_setup_complete',
        response.requires_setup ? 'false' : 'true'
      );
    } catch (error) {
      console.error('Failed to check setup status:', error);
      setState(prev => ({
        ...prev,
        requiresSetup: true,    // Fail-safe: assume setup needed when backend unreachable
        setupComplete: false,
        currentStep: 'setup',
        isLoading: false,
        error: 'Failed to check setup status. Please check if the backend is running.',
      }));
    }
  };

  const completeSetup = async () => {
    try {
      await api.setup.complete();

      // Update state to reflect completion
      setState({
        requiresSetup: false,
        setupComplete: true,
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

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}
