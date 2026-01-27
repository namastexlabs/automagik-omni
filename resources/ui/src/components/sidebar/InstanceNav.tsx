import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDown,
  ChevronRight,
  Activity,
  Settings,
  Webhook,
  Radio,
  Server,
  Loader2,
  Bot,
  Plus,
  ExternalLink,
  type LucideIcon,
} from 'lucide-react';
import { cn, api } from '@/lib';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { SettingsSheet } from '@/components/sheets/SettingsSheet';
import { WebhookSheet } from '@/components/sheets/WebhookSheet';
import { WebSocketSheet } from '@/components/sheets/WebSocketSheet';
import { RabbitMQSheet } from '@/components/sheets/RabbitMQSheet';
import { DiscordBotSettingsSheet } from '@/components/sheets/DiscordBotSettingsSheet';
import { DiscordIcon, WhatsAppIcon, SlackIcon } from '@/components/icons/BrandIcons';
import type { InstanceConfig } from '@/lib';

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error' | 'unknown';

/**
 * Normalize the connection status from various fields in InstanceConfig
 * Priority: connection_status field > channel-specific status fields
 */
function getInstanceConnectionStatus(instance: InstanceConfig): ConnectionStatus {
  // First, check the connection_status field from the API (most authoritative)
  if (instance.connection_status) {
    const status = instance.connection_status.toLowerCase();
    switch (status) {
      case 'connected':
      case 'open':
        return 'connected';
      case 'connecting':
        return 'connecting';
      case 'disconnected':
      case 'close':
      case 'closed':
        return 'disconnected';
      case 'error':
        return 'error';
      case 'unknown':
      default:
        // Fall through to channel-specific checks
        break;
    }
  }

  const channelType = instance.channel_type || 'whatsapp';

  if (channelType === 'discord') {
    // For Discord: token configured = "configured but not connected" (gray)
    // We can't know if it's actually connected without the service status
    // So show gray/unknown - user should check Discord service page
    return instance.has_discord_bot_token ? 'unknown' : 'disconnected';
  }

  // WhatsApp/Slack - check whatsapp_web_status, then fall back to evolution_status
  const state =
    instance.whatsapp_web_status?.state ||
    instance.whatsapp_web_status?.instance?.state ||
    instance.evolution_status?.state ||
    instance.evolution_status?.instance?.state;

  if (!state) {
    // Check for error in whatsapp_web_status
    if (instance.whatsapp_web_status?.error) {
      return 'error';
    }
    return 'unknown';
  }

  // Normalize state values
  switch (state.toLowerCase()) {
    case 'open':
    case 'connected':
      return 'connected';
    case 'connecting':
      return 'connecting';
    case 'close':
    case 'closed':
    case 'disconnected':
    case 'refused':
      return 'disconnected';
    case 'error':
      return 'error';
    default:
      return 'unknown';
  }
}

interface InstanceNavProps {
  isExpanded: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}

type SheetType = 'settings' | 'webhook' | 'websocket' | 'rabbitmq' | 'bot-settings' | null;

// Channel-specific sub-items for quick access (advanced settings not in main page)
interface SubItemConfig {
  id: string;
  label: string;
  icon: LucideIcon;
}

const CHANNEL_SUB_ITEMS: Record<'whatsapp' | 'discord' | 'slack', SubItemConfig[]> = {
  whatsapp: [
    { id: 'settings', label: 'WhatsApp Behavior', icon: Settings },
    { id: 'webhook', label: 'Webhook', icon: Webhook },
    { id: 'websocket', label: 'WebSocket', icon: Radio },
    { id: 'rabbitmq', label: 'RabbitMQ', icon: Server },
  ],
  discord: [
    { id: 'bot-settings', label: 'Bot Settings', icon: Bot },
  ],
  slack: [],
};

// Channel type icons and colors (using brand SVG icons)
const CHANNEL_ICON_CONFIG: Record<string, { color: string }> = {
  whatsapp: { color: 'text-[#25D366]' },
  discord: { color: 'text-[#5865F2]' },
  slack: { color: 'text-[#E01E5A]' },
};

export function InstanceNav({ isExpanded, onToggle, onNavigate }: InstanceNavProps) {
  const navigate = useNavigate();
  const [expandedInstances, setExpandedInstances] = useState<Record<string, boolean>>({});
  const [activeSheet, setActiveSheet] = useState<{
    type: SheetType;
    instanceName: string;
    channelType: 'whatsapp' | 'discord' | 'slack';
  } | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { data: instances, isLoading } = useQuery<InstanceConfig[]>({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_live_status: true }),
    refetchInterval: 15000, // Refresh every 15 seconds to keep status current
  });

  const toggleInstance = (e: React.MouseEvent, instanceName: string) => {
    e.stopPropagation();
    setExpandedInstances((prev) => ({
      ...prev,
      [instanceName]: !prev[instanceName],
    }));
  };

  const navigateToInstance = (instanceName: string) => {
    navigate(`/instances/${instanceName}`);
    onNavigate?.();
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
      <div className="flex items-center">
        <button
          onClick={onToggle}
          className={cn(
            'group flex flex-1 items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
            'text-foreground hover:bg-accent hover:text-accent-foreground',
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
        <button
          onClick={(e) => {
            e.stopPropagation();
            setShowCreateDialog(true);
          }}
          className="p-2 mr-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-accent-foreground transition-colors"
          title="Create instance"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      {/* Instances List */}
      {isExpanded && (
        <div className="ml-4 space-y-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : instances && instances.length > 0 ? (
            instances.map((instance) => {
              const subItems = getSubItems(instance.channel_type || 'whatsapp');
              const hasSubItems = subItems.length > 0;

              return (
                <div key={instance.name}>
                  {/* Instance Name - click navigates to settings page */}
                  <div
                    className={cn(
                      'group flex w-full items-center space-x-2 rounded-lg px-3 py-2 text-sm transition-all duration-200',
                      'text-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer',
                    )}
                  >
                    {hasSubItems ? (
                      <button
                        onClick={(e) => toggleInstance(e, instance.name)}
                        className="hover:bg-muted rounded p-0.5"
                      >
                        {expandedInstances[instance.name] ? (
                          <ChevronDown className="h-3 w-3 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-3 w-3 text-muted-foreground" />
                        )}
                      </button>
                    ) : (
                      <div className="w-4" />
                    )}
                    <button
                      onClick={() => navigateToInstance(instance.name)}
                      className="flex flex-1 items-center space-x-2 text-left"
                    >
                      {getChannelIcon(instance.channel_type || 'whatsapp')}
                      <span className="flex-1 truncate">{instance.name}</span>
                      <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-50" />
                    </button>
                    <span
                      className={cn('h-2 w-2 rounded-full', {
                        'bg-green-500': getInstanceConnectionStatus(instance) === 'connected',
                        'bg-yellow-500 animate-pulse': getInstanceConnectionStatus(instance) === 'connecting',
                        'bg-red-500':
                          getInstanceConnectionStatus(instance) === 'disconnected' ||
                          getInstanceConnectionStatus(instance) === 'error',
                        'bg-gray-400': getInstanceConnectionStatus(instance) === 'unknown',
                      })}
                    />
                  </div>

                  {/* Sub-items - only advanced/integration sheets */}
                  {hasSubItems && expandedInstances[instance.name] && (
                    <div className="ml-5 space-y-0.5">
                      {subItems.map((item) => (
                        <button
                          key={item.id}
                          onClick={() =>
                            openSheet(item.id as SheetType, instance.name, instance.channel_type || 'whatsapp')
                          }
                          className={cn(
                            'flex w-full items-center space-x-2 rounded-lg px-3 py-1.5 text-xs transition-all duration-200',
                            'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                          )}
                        >
                          <item.icon className="h-3.5 w-3.5" />
                          <span>{item.label}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <p className="px-3 py-2 text-xs text-muted-foreground">No instances</p>
          )}
        </div>
      )}

      {/* Sheets - only advanced/integration settings */}
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

      {/* Create Instance Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Instance</DialogTitle>
            <DialogDescription>Choose the channel type for your new instance</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-4">
            <Link
              to="/services/whatsapp"
              onClick={() => {
                setShowCreateDialog(false);
                onNavigate?.();
              }}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border border-border hover:border-[#25D366] hover:bg-[#25D366]/5 transition-all"
            >
              <WhatsAppIcon className="h-10 w-10 text-[#25D366]" />
              <span className="font-medium">WhatsApp Web</span>
            </Link>
            <Link
              to="/services/discord"
              onClick={() => {
                setShowCreateDialog(false);
                onNavigate?.();
              }}
              className="flex flex-col items-center gap-3 p-6 rounded-lg border border-border hover:border-[#5865F2] hover:bg-[#5865F2]/5 transition-all"
            >
              <DiscordIcon className="h-10 w-10 text-[#5865F2]" />
              <span className="font-medium">Discord</span>
            </Link>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
