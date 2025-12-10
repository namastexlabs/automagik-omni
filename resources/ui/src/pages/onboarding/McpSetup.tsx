import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import OnboardingLayout from '@/components/OnboardingLayout';
import { McpClientRow, type McpConnectionMethod, type McpInstallStatus } from '@/components/McpClientRow';
import { MCP_CLIENTS, type McpClientId } from '@/components/icons/McpClientIcons';
import { McpStartupModal } from '@/components/McpStartupModal';
import { useOnboarding } from '@/contexts/OnboardingContext';
import { api } from '@/lib/api';
import { Loader2, CheckCircle2, Wifi, WifiOff } from 'lucide-react';

const MCP_PORT = 28882;

type ClientInstallState = Record<McpClientId, {
  method: McpConnectionMethod;
  status: McpInstallStatus;
  errorMessage?: string;
}>;

export default function McpSetup() {
  const navigate = useNavigate();
  const { completeSetup } = useOnboarding();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [httpServerRunning, setHttpServerRunning] = useState(false);
  const [httpServerLoading, setHttpServerLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string>('');
  const [showStartupModal, setShowStartupModal] = useState(false);

  // Fetch the public URL on mount
  useEffect(() => {
    api.setup.getPublicUrl().then(({ url }) => {
      setServerUrl(`${url}:${MCP_PORT}/mcp`);
    }).catch(() => {
      // Fallback if API not available
      setServerUrl(`http://localhost:${MCP_PORT}/mcp`);
    });
  }, []);

  // Initialize state for each client
  const [clientStates, setClientStates] = useState<ClientInstallState>(() => {
    const initial: Partial<ClientInstallState> = {};
    for (const client of MCP_CLIENTS) {
      initial[client.id] = {
        method: 'stdio',
        status: 'idle',
      };
    }
    return initial as ClientInstallState;
  });

  const handleMethodChange = (clientId: McpClientId, method: McpConnectionMethod) => {
    setClientStates((prev) => ({
      ...prev,
      [clientId]: {
        ...prev[clientId],
        method,
      },
    }));
  };

  const handleInstall = async (clientId: McpClientId) => {
    const clientState = clientStates[clientId];

    // If HTTP mode is selected but server isn't running, show error
    if (clientState.method === 'http' && !httpServerRunning) {
      setClientStates((prev) => ({
        ...prev,
        [clientId]: {
          ...prev[clientId],
          status: 'error',
          errorMessage: 'Start the HTTP server first before installing in HTTP mode.',
        },
      }));
      return;
    }

    // Set installing status
    setClientStates((prev) => ({
      ...prev,
      [clientId]: {
        ...prev[clientId],
        status: 'installing',
        errorMessage: undefined,
      },
    }));

    try {
      const result = await api.mcp.install(clientId, clientState.method);

      if (result.success) {
        setClientStates((prev) => ({
          ...prev,
          [clientId]: {
            ...prev[clientId],
            status: 'success',
          },
        }));
      } else {
        setClientStates((prev) => ({
          ...prev,
          [clientId]: {
            ...prev[clientId],
            status: 'error',
            errorMessage: result.error || 'Installation failed',
          },
        }));
      }
    } catch (err) {
      setClientStates((prev) => ({
        ...prev,
        [clientId]: {
          ...prev[clientId],
          status: 'error',
          errorMessage: err instanceof Error ? err.message : 'Installation failed',
        },
      }));
    }
  };

  const handleToggleHttpServer = async () => {
    setError(null);

    if (httpServerRunning) {
      // Stop server directly
      setHttpServerLoading(true);
      try {
        await api.mcp.stopServer();
        setHttpServerRunning(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to stop HTTP server');
      } finally {
        setHttpServerLoading(false);
      }
    } else {
      // Start server via modal (shows progress and logs)
      setShowStartupModal(true);
    }
  };

  const handleMcpStartupSuccess = () => {
    setShowStartupModal(false);
    setHttpServerRunning(true);
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      await api.setup.complete();
      await completeSetup();
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to complete setup:', err);
      setError(err instanceof Error ? err.message : 'Failed to complete setup');
      setIsSubmitting(false);
    }
  };

  const hasAnyInstalled = Object.values(clientStates).some((s) => s.status === 'success');
  const hasAnyInstalling = Object.values(clientStates).some((s) => s.status === 'installing');

  return (
    <OnboardingLayout currentStep={4} totalSteps={4} title="MCP Configuration">
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect Your AI Tools</h2>
          <p className="text-gray-600">
            Install Automagik Omni MCP server to your favorite AI coding assistants.
            Select your preferred connection method and click Install.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Remote MCP Server Toggle - must be enabled first for HTTP connections */}
        <div className="mb-8 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {httpServerRunning ? (
                <Wifi className="h-5 w-5 text-green-500" />
              ) : (
                <WifiOff className="h-5 w-5 text-gray-400" />
              )}
              <div>
                <Label htmlFor="http-server" className="text-sm font-medium text-gray-900">
                  Remote MCP Server
                </Label>
                <p className="text-xs text-gray-500">
                  Enable HTTP mode for remote AI tool connections. Required before selecting HTTP for any client.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {httpServerLoading && <Loader2 className="h-4 w-4 animate-spin text-gray-500" />}
              <Switch
                id="http-server"
                checked={httpServerRunning}
                onCheckedChange={handleToggleHttpServer}
                disabled={httpServerLoading}
              />
            </div>
          </div>
          {httpServerRunning && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                <span className="font-medium">Server URL:</span>{' '}
                <code className="bg-gray-100 px-1 py-0.5 rounded">{serverUrl || 'Loading...'}</code>
              </p>
            </div>
          )}
        </div>

        {/* Client List */}
        <div className="space-y-4 mb-8">
          {MCP_CLIENTS.map((client) => (
            <McpClientRow
              key={client.id}
              client={client}
              method={clientStates[client.id].method}
              onMethodChange={(method) => handleMethodChange(client.id, method)}
              onInstall={() => handleInstall(client.id)}
              status={clientStates[client.id].status}
              errorMessage={clientStates[client.id].errorMessage}
              disabled={hasAnyInstalling && clientStates[client.id].status !== 'installing'}
            />
          ))}
        </div>

        {/* Complete Setup Button */}
        <Button
          onClick={handleComplete}
          disabled={isSubmitting || hasAnyInstalling}
          className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Completing Setup...
            </>
          ) : (
            <>
              <CheckCircle2 className="mr-2 h-5 w-5" />
              Complete Setup
            </>
          )}
        </Button>

        {!hasAnyInstalled && (
          <p className="mt-4 text-xs text-gray-500 text-center">
            You can skip MCP setup and configure it later from Settings.
          </p>
        )}
      </div>

      {/* MCP Startup Modal */}
      <McpStartupModal
        open={showStartupModal}
        onOpenChange={(open) => {
          setShowStartupModal(open);
          // If user closes modal without success, ensure toggle is off
          if (!open && !httpServerRunning) {
            // Toggle stays off, no action needed
          }
        }}
        onSuccess={handleMcpStartupSuccess}
      />
    </OnboardingLayout>
  );
}
