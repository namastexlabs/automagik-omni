import { useState } from 'react';
import { Wrench, Check } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { getApiKey } from '@/lib';

export function McpConfigCopy() {
  const [copied, setCopied] = useState(false);

  const getMcpConfig = () => {
    const apiKey = getApiKey();

    // Construct the API URL - default to localhost:8882 for development
    // In production, this would typically be the same origin but could be different
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8882';

    return {
      mcpServers: {
        omni: {
          command: 'uvx',
          args: ['--from', 'automagik-omni', 'mcp-server-omni'],
          env: {
            OMNI_URL: apiUrl,
            OMNI_API_KEY: apiKey || '', // Empty string handled by validation in handleCopy
          },
        },
      },
    };
  };

  const handleCopy = async () => {
    try {
      const apiKey = getApiKey();

      // Don't copy placeholder - require actual API key
      if (!apiKey) {
        toast.error('API key not available', {
          description: 'Please complete setup or check your authentication',
        });
        return;
      }

      const config = getMcpConfig();
      const configJson = JSON.stringify(config, null, 2);

      await navigator.clipboard.writeText(configJson);

      setCopied(true);
      toast.success('MCP config copied to clipboard!', {
        description: 'Paste this into your Claude Code or Cursor settings',
      });

      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy config', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={handleCopy}
      className="h-9 w-9"
      aria-label="Copy MCP Config"
      title="Copy MCP configuration for Claude Code / Cursor"
    >
      {copied ? <Check className="h-4 w-4 text-success" /> : <Wrench className="h-4 w-4" />}
    </Button>
  );
}
