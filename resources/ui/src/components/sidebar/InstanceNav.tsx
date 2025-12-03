import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Activity, Wifi, Settings, Webhook, Radio, Server, Loader2, Bot, type LucideIcon } from 'lucide-react';
import { cn, api } from '@/lib';
import { ConnectionSheet } from '@/components/sheets/ConnectionSheet';
import { SettingsSheet } from '@/components/sheets/SettingsSheet';
import { WebhookSheet } from '@/components/sheets/WebhookSheet';
import { WebSocketSheet } from '@/components/sheets/WebSocketSheet';
import { RabbitMQSheet } from '@/components/sheets/RabbitMQSheet';
import { DiscordBotSettingsSheet } from '@/components/sheets/DiscordBotSettingsSheet';
import { DiscordIcon, WhatsAppIcon, SlackIcon } from '@/components/icons/BrandIcons';

interface InstanceNavProps {
  isExpanded: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}

type SheetType = 'connection' | 'settings' | 'webhook' | 'websocket' | 'rabbitmq' | 'bot-settings' | null;

// Channel-specific sub-items configuration
interface SubItemConfig {
  id: string;
  label: string;
  icon: LucideIcon;
}

const CHANNEL_SUB_ITEMS: Record<'whatsapp' | 'discord' | 'slack', SubItemConfig[]> = {
  whatsapp: [
    { id: 'connection', label: 'Connection', icon: Wifi },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'webhook', label: 'Webhook', icon: Webhook },
    { id: 'websocket', label: 'WebSocket', icon: Radio },
    { id: 'rabbitmq', label: 'RabbitMQ', icon: Server },
  ],
  discord: [
    { id: 'connection', label: 'Connection', icon: Wifi },
    { id: 'bot-settings', label: 'Bot Settings', icon: Bot },
  ],
  slack: [
    { id: 'connection', label: 'Connection', icon: Wifi },
  ],
};

// Channel type icons and colors (using brand SVG icons)
const CHANNEL_ICON_CONFIG: Record<string, { color: string }> = {
  whatsapp: { color: 'text-[#25D366]' },
  discord: { color: 'text-[#5865F2]' },
  slack: { color: 'text-[#E01E5A]' },
};

export function InstanceNav({ isExpanded, onToggle, onNavigate }: InstanceNavProps) {
  const [expandedInstances, setExpandedInstances] = useState<Record<string, boolean>>({});
  const [activeSheet, setActiveSheet] = useState<{
    type: SheetType;
    instanceName: string;
    channelType: 'whatsapp' | 'discord' | 'slack';
  } | null>(null);

  const { data: instances, isLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_live_status: true }),
    refetchInterval: 30000, // Refresh every 30 seconds to keep status current
  });

  const toggleInstance = (instanceName: string) => {
    setExpandedInstances(prev => ({
      ...prev,
      [instanceName]: !prev[instanceName]
    }));
  };

  const openSheet = (type: SheetType, instanceName: string, channelType: 'whatsapp' | 'discord' | 'slack') => {
    setActiveSheet({ type, instanceName, channelType });
  };

  const closeSheet = () => {
    setActiveSheet(null);
  };

  // Get sub-items for a specific channel type
  const getSubItems = (channelType: string): SubItemConfig[] => {
    const type = channelType as keyof typeof CHANNEL_SUB_ITEMS;
    return CHANNEL_SUB_ITEMS[type] || CHANNEL_SUB_ITEMS.whatsapp;
  };

  // Get channel icon component (brand SVG icons)
  const getChannelIcon = (channelType: string) => {
    const config = CHANNEL_ICON_CONFIG[channelType] || CHANNEL_ICON_CONFIG.whatsapp;
    const iconClass = cn('h-3.5 w-3.5', config.color);

    switch (channelType) {
      case 'discord':
        return <DiscordIcon className={iconClass} />;
      case 'slack':
        return <SlackIcon className={iconClass} />;
      case 'whatsapp':
      default:
        return <WhatsAppIcon className={iconClass} />;
    }
  };

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
                  {getChannelIcon(instance.channel_type || 'whatsapp')}
                  <span className="flex-1 text-left truncate">{instance.name}</span>
                  <span className={cn(
                    'h-2 w-2 rounded-full',
                    instance.connection_status === 'connected' ? 'bg-green-500' :
                    instance.connection_status === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                    instance.connection_status === 'disconnected' || instance.connection_status === 'error' ? 'bg-red-500' :
                    'bg-gray-400'
                  )} />
                </button>

                {/* Sub-items - channel-aware */}
                {expandedInstances[instance.name] && (
                  <div className="ml-5 space-y-0.5">
                    {getSubItems(instance.channel_type || 'whatsapp').map((item) => (
                      <button
                        key={item.id}
                        onClick={() => openSheet(item.id as SheetType, instance.name, instance.channel_type || 'whatsapp')}
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
          channelType={activeSheet.channelType}
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
      {activeSheet?.type === 'bot-settings' && (
        <DiscordBotSettingsSheet
          instanceName={activeSheet.instanceName}
          open={true}
          onOpenChange={(open) => !open && closeSheet()}
        />
      )}
    </>
  );
}
