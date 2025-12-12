import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { McpClientRow, type McpConnectionMethod, type McpInstallStatus } from '@/components/McpClientRow';
import { MCP_CLIENTS, type McpClientId } from '@/components/icons/McpClientIcons';
import { McpStartupModal } from '@/components/McpStartupModal';
import { api } from '@/lib/api';
import { Plug, Wifi, WifiOff, Loader2, CheckCircle2, AlertCircle, Copy, Check } from 'lucide-react';

const MCP_PORT = 28882;

type ClientInstallState = Record<
  McpClientId,
  {
    method: McpConnectionMethod;
    status: McpInstallStatus;
    errorMessage?: string;
  }
>;

export default function Mcp() {
  const [httpServerRunning, setHttpServerRunning] = useState(false);
  const [httpServerLoading, setHttpServerLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string>('');
  const [showStartupModal, setShowStartupModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // Check MCP server status on load
  const { data: gatewayStatus } = useQuery({
    queryKey: ['gateway-status'],
    queryFn: () => api.gateway.getStatus(),
    refetchInterval: 5000,
  });

  // Check if MCP is running via gateway status
  useEffect(() => {
    const checkMcpStatus = async () => {
      try {
        const mcpProcess = gatewayStatus?.processes?.mcp;
        if (mcpProcess?.healthy) {
          const response = await fetch('/mcp/health', {
            method: 'GET',
            signal: AbortSignal.timeout(3000),
          });
          if (response.ok) {
            const data = await response.json();
            if (data.status === 'healthy') {
              setHttpServerRunning(true);
            }
          }
        } else {
          setHttpServerRunning(false);
        }
      } catch {
        setHttpServerRunning(false);
      }
    };

    checkMcpStatus();
  }, [gatewayStatus]);

  // Fetch public URL
  useEffect(() => {
    const fetchUrl = async () => {
      try {
        const { url } = await api.setup.getPublicUrl();
        setServerUrl(`${url}:${MCP_PORT}/mcp`);
      } catch {
        setServerUrl(`http://localhost:${MCP_PORT}/mcp`);
      }
    };
    fetchUrl();
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
      // Stop server with verification
      setHttpServerLoading(true);
      try {
        await api.mcp.stopServer();

        // Verify the server actually stopped
        let stopped = false;
        for (let i = 0; i < 20; i++) {
          try {
            const response = await fetch('/mcp/health', {
              method: 'GET',
              signal: AbortSignal.timeout(1000),
            });
            if (!response.ok) {
              stopped = true;
              break;
            }
            const data = await response.json();
            if (data.status !== 'healthy') {
              stopped = true;
              break;
            }
          } catch {
            stopped = true;
            break;
          }
          await new Promise((r) => setTimeout(r, 500));
        }

        if (stopped) {
          setHttpServerRunning(false);
        } else {
          setError('MCP server did not stop after 10 seconds. Try again.');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to stop HTTP server');
      } finally {
        setHttpServerLoading(false);
      }
    } else {
      // Start server via modal
      setShowStartupModal(true);
    }
  };

  const handleMcpStartupSuccess = () => {
    setShowStartupModal(false);
    setHttpServerRunning(true);
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(serverUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasAnyInstalling = Object.values(clientStates).some((s) => s.status === 'installing');
  const installedCount = Object.values(clientStates).filter((s) => s.status === 'success').length;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="MCP Configuration"
          subtitle="Connect AI tools to Automagik Omni via Model Context Protocol"
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* HTTP Server Card */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                      {httpServerRunning ? (
                        <Wifi className="h-6 w-6 text-green-500" />
                      ) : (
                        <WifiOff className="h-6 w-6 text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      <CardTitle>Remote MCP Server</CardTitle>
                      <CardDescription>Enable HTTP mode for remote AI tool connections</CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {httpServerRunning ? (
                      <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Running
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Stopped
                      </Badge>
                    )}
                    {httpServerLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                    <Switch
                      checked={httpServerRunning}
                      onCheckedChange={handleToggleHttpServer}
                      disabled={httpServerLoading}
                    />
                  </div>
                </div>
              </CardHeader>
              {httpServerRunning && (
                <CardContent className="border-t">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-sm font-medium">Server URL</Label>
                      <p className="text-sm text-muted-foreground font-mono mt-1">{serverUrl || 'Loading...'}</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleCopyUrl}>
                      {copied ? (
                        <>
                          <Check className="h-4 w-4 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-1" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              )}
            </Card>

            {/* AI Clients Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">AI Coding Assistants</h2>
                  <p className="text-sm text-muted-foreground">Install the MCP server to your preferred AI tools</p>
                </div>
                {installedCount > 0 && <Badge variant="secondary">{installedCount} installed</Badge>}
              </div>

              <div className="space-y-4">
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
            </div>

            {/* Info Section */}
            <Card className="border-border bg-muted/50">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Plug className="h-5 w-5 text-primary" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="font-medium">Connection Methods</h3>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <p>
                        <strong>Local (STDIO):</strong> Each AI tool manages its own local process. Best for single-user
                        setups.
                      </p>
                      <p>
                        <strong>HTTP Server:</strong> Centralized server that multiple tools can connect to. Required
                        for remote access or shared deployments.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* MCP Startup Modal */}
      <McpStartupModal
        open={showStartupModal}
        onOpenChange={(open) => {
          setShowStartupModal(open);
        }}
        onSuccess={handleMcpStartupSuccess}
      />
    </DashboardLayout>
  );
}
