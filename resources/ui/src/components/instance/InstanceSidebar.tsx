import { ScrollArea } from '@/components/ui/scroll-area';
import { ConnectionSection } from './ConnectionSection';
import { SettingsSection } from './SettingsSection';
import { WebhookSection } from './WebhookSection';
import { WebSocketSection } from './WebSocketSection';
import { RabbitMQSection } from './RabbitMQSection';
import type { InstanceConfig } from '@/lib/types';

interface InstanceSidebarProps {
  instance: InstanceConfig;
}

export function InstanceSidebar({ instance }: InstanceSidebarProps) {
  const instanceName = instance.whatsapp_instance || instance.name;

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Connection - always visible */}
        <ConnectionSection instanceName={instanceName} instance={instance} />

        {/* Settings - collapsible */}
        <SettingsSection instanceName={instanceName} />

        {/* Webhook - collapsible */}
        <WebhookSection instanceName={instanceName} />

        {/* WebSocket - collapsible */}
        <WebSocketSection instanceName={instanceName} />

        {/* RabbitMQ - collapsible */}
        <RabbitMQSection instanceName={instanceName} />
      </div>
    </ScrollArea>
  );
}
