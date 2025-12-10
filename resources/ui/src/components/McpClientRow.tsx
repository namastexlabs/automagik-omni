import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Loader2, CheckCircle2, XCircle, Download } from 'lucide-react';
import { type ComponentType } from 'react';

export type McpConnectionMethod = 'http' | 'stdio';
export type McpInstallStatus = 'idle' | 'installing' | 'success' | 'error';

interface McpClientRowProps {
  client: {
    id: string;
    name: string;
    icon: ComponentType<{ className?: string }>;
    color: string;
    description: string;
  };
  method: McpConnectionMethod;
  onMethodChange: (method: McpConnectionMethod) => void;
  onInstall: () => void;
  status: McpInstallStatus;
  errorMessage?: string;
  disabled?: boolean;
}

export function McpClientRow({
  client,
  method,
  onMethodChange,
  onInstall,
  status,
  errorMessage,
  disabled,
}: McpClientRowProps) {
  const Icon = client.icon;
  const isInstalling = status === 'installing';
  const isSuccess = status === 'success';
  const isError = status === 'error';

  return (
    <div
      className={`rounded-lg border-2 p-4 transition-colors ${
        isSuccess
          ? 'border-green-500 bg-green-50'
          : isError
            ? 'border-red-500 bg-red-50'
            : 'border-gray-200 bg-gray-50'
      }`}
    >
      <div className="flex items-center justify-between">
        {/* Client Info */}
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: client.color }}
          >
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{client.name}</h3>
            <p className="text-xs text-gray-500">{client.description}</p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          {isInstalling && (
            <div className="flex items-center gap-1 text-sm">
              <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
              <span className="text-blue-600">Installing...</span>
            </div>
          )}
          {isSuccess && (
            <div className="flex items-center gap-1 text-sm">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span className="text-green-600">Installed</span>
            </div>
          )}
          {isError && (
            <div className="flex items-center gap-1 text-sm">
              <XCircle className="h-4 w-4 text-red-500" />
              <span className="text-red-600">Failed</span>
            </div>
          )}
        </div>
      </div>

      {/* Connection Method & Install Button */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
        <RadioGroup
          value={method}
          onValueChange={(value) => onMethodChange(value as McpConnectionMethod)}
          className="flex gap-6"
          disabled={isInstalling || disabled}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="stdio" id={`${client.id}-stdio`} />
            <Label htmlFor={`${client.id}-stdio`} className="text-sm cursor-pointer">
              Local (STDIO)
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="http" id={`${client.id}-http`} />
            <Label htmlFor={`${client.id}-http`} className="text-sm cursor-pointer">
              HTTP Server
            </Label>
          </div>
        </RadioGroup>

        <Button
          onClick={onInstall}
          disabled={isInstalling || isSuccess || disabled}
          variant={isSuccess ? 'outline' : 'default'}
          size="sm"
          className={isSuccess ? 'border-green-500 text-green-600' : ''}
        >
          {isInstalling ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Installing...
            </>
          ) : isSuccess ? (
            <>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Installed
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              Install
            </>
          )}
        </Button>
      </div>

      {/* Error Message */}
      {isError && errorMessage && (
        <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-700">{errorMessage}</div>
      )}
    </div>
  );
}
