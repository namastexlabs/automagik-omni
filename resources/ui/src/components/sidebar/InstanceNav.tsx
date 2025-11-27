import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Activity, Wifi, Settings, Webhook, Radio, Server, Loader2 } from 'lucide-react';
import { cn, api } from '@/lib';
import { ConnectionSheet } from '@/components/sheets/ConnectionSheet';
import { SettingsSheet } from '@/components/sheets/SettingsSheet';
import { WebhookSheet } from '@/components/sheets/WebhookSheet';
import { WebSocketSheet } from '@/components/sheets/WebSocketSheet';
import { RabbitMQSheet } from '@/components/sheets/RabbitMQSheet';

interface InstanceNavProps {
  isExpanded: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}

type SheetType = 'connection' | 'settings' | 'webhook' | 'websocket' | 'rabbitmq' | null;

export function InstanceNav({ isExpanded, onToggle, onNavigate }: InstanceNavProps) {
  const [expandedInstances, setExpandedInstances] = useState<Record<string, boolean>>({});
  const [activeSheet, setActiveSheet] = useState<{ type: SheetType; instanceName: string } | null>(null);

  const { data: instances, isLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100 }),
  });

  const toggleInstance = (instanceName: string) => {
    setExpandedInstances(prev => ({
      ...prev,
      [instanceName]: !prev[instanceName]
    }));
  };

  const openSheet = (type: SheetType, instanceName: string) => {
    setActiveSheet({ type, instanceName });
  };

  const closeSheet = () => {
    setActiveSheet(null);
  };

  const subItems = [
    { id: 'connection', label: 'Connection', icon: Wifi },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'webhook', label: 'Webhook', icon: Webhook },
    { id: 'websocket', label: 'WebSocket', icon: Radio },
    { id: 'rabbitmq', label: 'RabbitMQ', icon: Server },
  ] as const;

  return (
    <>
      {/* Instances Header */}
      <button
        onClick={onToggle}
        className={cn(
          'group flex w-full items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
          'text-foreground hover:bg-accent hover:text-accent-foreground'
        )}
      >
        <Activity className="h-5 w-5 text-muted-foreground group-hover:text-accent-foreground" />
        <span className="flex-1 text-left">Instances</span>
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {/* Instances List */}
      {isExpanded && (
        <div className="ml-4 space-y-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : instances && instances.length > 0 ? (
            instances.map((instance: any) => (
              <div key={instance.name}>
                {/* Instance Name */}
                <button
                  onClick={() => toggleInstance(instance.name)}
                  className={cn(
                    'group flex w-full items-center space-x-2 rounded-lg px-3 py-2 text-sm transition-all duration-200',
                    'text-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  {expandedInstances[instance.name] ? (
                    <ChevronDown className="h-3 w-3 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-muted-foreground" />
                  )}
                  <span className="flex-1 text-left truncate">{instance.name}</span>
                  <span className={cn(
                    'h-2 w-2 rounded-full',
                    instance.is_active ? 'bg-green-500' : 'bg-gray-400'
                  )} />
                </button>

                {/* Sub-items */}
                {expandedInstances[instance.name] && (
                  <div className="ml-5 space-y-0.5">
                    {subItems.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => openSheet(item.id, instance.name)}
                        className={cn(
                          'flex w-full items-center space-x-2 rounded-lg px-3 py-1.5 text-xs transition-all duration-200',
                          'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                        )}
                      >
                        <item.icon className="h-3.5 w-3.5" />
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="px-3 py-2 text-xs text-muted-foreground">No instances</p>
          )}
        </div>
      )}

      {/* Sheets */}
      {activeSheet?.type === 'connection' && (
        <ConnectionSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
      {activeSheet?.type === 'settings' && (
        <SettingsSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
      {activeSheet?.type === 'webhook' && (
        <WebhookSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
      {activeSheet?.type === 'websocket' && (
        <WebSocketSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
      {activeSheet?.type === 'rabbitmq' && (
        <RabbitMQSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
    </>
  );
}
