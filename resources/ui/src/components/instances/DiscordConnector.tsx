import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { api } from '@/lib';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  Loader2,
} from 'lucide-react';

// Discord icon as SVG
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
  </svg>
);

interface DiscordConnectorProps {
  instanceName: string;
  onBack: () => void;
  onSuccess: () => void;
}

export function DiscordConnector({ instanceName, onBack, onSuccess }: DiscordConnectorProps) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const createMutation = useMutation({
    mutationFn: () => api.instances.create({
      name: instanceName,
      channel_type: 'discord',
      discord_bot_token: token,
    }),
    onSuccess: () => {
      setIsConnected(true);
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Discord bot "${instanceName}" connected`);

      // Auto-close after showing success
      setTimeout(() => {
        onSuccess();
      }, 2000);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to connect Discord bot');
    },
  });

  const handleConnect = () => {
    setError(null);

    if (!token.trim()) {
      setError('Please enter your bot token');
      return;
    }

    // Basic token validation (Discord tokens are typically 59+ chars)
    if (token.length < 50) {
      setError('This doesn\'t look like a valid Discord bot token');
      return;
    }

    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="h-14 w-14 rounded-2xl bg-[#5865F2] flex items-center justify-center mx-auto">
          <DiscordIcon className="h-6 w-6 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {isConnected ? 'Connected!' : 'Connect Discord Bot'}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {isConnected
              ? `"${instanceName}" is now connected`
              : 'Enter your Discord bot token to connect'}
          </p>
        </div>
      </div>

      {/* Success State */}
      {isConnected && (
        <div className="flex flex-col items-center space-y-4 py-8 animate-fade-in">
          <div className="h-20 w-20 rounded-full bg-[#5865F2] flex items-center justify-center">
            <CheckCircle2 className="h-12 w-12 text-white" />
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold text-[#5865F2] mb-2">Bot Connected!</p>
            <p className="text-sm text-muted-foreground">
              Your Discord bot is now ready to use
            </p>
          </div>
        </div>
      )}

      {/* Token Input */}
      {!isConnected && (
        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="bot-token" className="text-sm font-medium">
              Bot Token
            </Label>
            <Input
              id="bot-token"
              type="password"
              value={token}
              onChange={(e) => {
                setToken(e.target.value);
                setError(null);
              }}
              placeholder="Enter your Discord bot token"
              className="font-mono text-sm"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
            />
          </div>

          {/* Help section */}
          <Collapsible open={helpOpen} onOpenChange={setHelpOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between">
                <span className="text-sm text-muted-foreground">
                  How do I get a bot token?
                </span>
                <ChevronDown className={`h-4 w-4 transition-transform ${helpOpen ? 'rotate-180' : ''}`} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-3 pt-2">
              <div className="text-xs text-muted-foreground bg-muted p-4 rounded-lg space-y-2">
                <ol className="space-y-2 list-decimal list-inside">
                  <li>Go to the Discord Developer Portal</li>
                  <li>Click "New Application" and give it a name</li>
                  <li>Go to the "Bot" section in the left sidebar</li>
                  <li>Click "Add Bot" then "Reset Token"</li>
                  <li>Copy the token and paste it above</li>
                </ol>
                <a
                  href="https://discord.com/developers/applications"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline mt-2"
                >
                  Open Discord Developer Portal
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              onClick={onBack}
              className="flex-1"
              disabled={createMutation.isPending}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button
              onClick={handleConnect}
              className="flex-1 bg-[#5865F2] hover:bg-[#4752C4]"
              disabled={createMutation.isPending || !token.trim()}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                'Connect Bot'
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
