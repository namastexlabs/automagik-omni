import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ForgeInspector as AutomagikForgeWebCompanion } from 'forge-inspector';
import { ThemeProvider } from './components/ThemeProvider';
import { OnboardingProvider, useOnboarding } from './contexts/OnboardingContext';
import { SetupGuard } from './components/SetupGuard';
import LoadingScreen from './components/LoadingScreen';
import { isAuthenticated, api } from './lib/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Instances from './pages/Instances';
import Contacts from './pages/Contacts';
import Chats from './pages/Chats';
import Settings from './pages/Settings';
import GlobalSettings from './pages/GlobalSettings';
import DatabaseSetup from './pages/onboarding/DatabaseSetup';
import ApiKey from './pages/onboarding/ApiKey';
import ChannelSetup from './pages/onboarding/ChannelSetup';
import McpSetup from './pages/onboarding/McpSetup';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

// Public Route Component (redirect to dashboard if already authenticated)
function PublicRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

// Root redirect with onboarding check
function RootRedirect() {
  const { requiresSetup, isLoading } = useOnboarding();
  const authenticated = isAuthenticated();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (requiresSetup) {
    return <Navigate to="/onboarding/setup" replace />;
  }

  if (!authenticated) {
    // Setup is complete, go to login page (not onboarding)
    return <Navigate to="/login" replace />;
  }

  return <Navigate to="/dashboard" replace />;
}

function App() {
  // Configure global auth error handler
  useEffect(() => {
    let isRedirecting = false;

    api.setAuthErrorHandler(() => {
      // Don't redirect if we are in the onboarding flow
      // This prevents stray 401s (e.g. from background polling) from resetting the wizard
      if (window.location.pathname.startsWith('/onboarding')) {
        console.warn('[App] Suppressed auth redirect during onboarding');
        return;
      }

      if (!isRedirecting) {
        isRedirecting = true;
        // Use replace to prevent back button returning to broken state
        window.location.replace('/login');
      }
    });
  }, []);

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <OnboardingProvider>
          <Toaster richColors position="top-right" />
          <AutomagikForgeWebCompanion />
          <BrowserRouter>
            <Routes>
              {/* Root redirect with onboarding check */}
              <Route path="/" element={<RootRedirect />} />

              {/* Onboarding routes (no auth required) */}
              <Route path="/onboarding/setup" element={<DatabaseSetup />} />
              <Route path="/onboarding/api-key" element={<ApiKey />} />
              <Route path="/onboarding/channels" element={<ChannelSetup />} />
              <Route path="/onboarding/mcp" element={<McpSetup />} />

              {/* Login route (legacy, wrapped with SetupGuard) */}
              <Route
                path="/login"
                element={
                  <SetupGuard>
                    <PublicRoute>
                      <Login />
                    </PublicRoute>
                  </SetupGuard>
                }
              />

              {/* Protected routes (wrapped with SetupGuard) */}
              <Route
                path="/dashboard"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />
              <Route
                path="/instances"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <Instances />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />
              <Route
                path="/contacts"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <Contacts />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />
              <Route
                path="/chats"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <Chats />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />
              <Route
                path="/settings"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <Settings />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />
              <Route
                path="/global-settings"
                element={
                  <SetupGuard>
                    <ProtectedRoute>
                      <GlobalSettings />
                    </ProtectedRoute>
                  </SetupGuard>
                }
              />

              {/* Catch-all redirect */}
              <Route path="*" element={<RootRedirect />} />
            </Routes>
          </BrowserRouter>
        </OnboardingProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
