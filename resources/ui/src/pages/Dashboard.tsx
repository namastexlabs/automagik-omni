import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { InstanceDialog } from '@/components/InstanceDialog';
import { QRCodeDialog } from '@/components/QRCodeDialog';
import { TimeRangeSelector } from '@/components/dashboard/TimeRangeSelector';
import { OverviewTab } from '@/components/dashboard/tabs/OverviewTab';
import { MessagesTab } from '@/components/dashboard/tabs/MessagesTab';
import { InstancesTab } from '@/components/dashboard/tabs/InstancesTab';
import { SystemTab } from '@/components/dashboard/tabs/SystemTab';
import { ManageTab } from '@/components/dashboard/tabs/ManageTab';
import { LogsTab } from '@/components/dashboard/tabs/LogsTab';
import {
  MessageSquare,
  Plus,
  LayoutDashboard,
  Server,
  Cpu,
  Settings,
  ScrollText,
} from 'lucide-react';
import type { InstanceConfig } from '@/lib';

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingInstance, setEditingInstance] = useState<InstanceConfig | null>(null);
  const [qrInstance, setQrInstance] = useState<string | null>(null);

  const currentTab = searchParams.get('tab') || 'overview';

  const handleTabChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('tab', value);
    setSearchParams(newParams);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Dashboard"
          actions={
            <div className="flex items-center gap-3">
              <TimeRangeSelector />
              <Button
                className="gradient-primary elevation-md hover:elevation-lg transition-all hover-lift"
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Instance
              </Button>
            </div>
          }
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-6 space-y-6 animate-fade-in">
            <Tabs value={currentTab} onValueChange={handleTabChange} className="w-full">
              <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:inline-grid">
                <TabsTrigger value="overview" className="flex items-center gap-2">
                  <LayoutDashboard className="h-4 w-4" />
                  <span className="hidden sm:inline">Overview</span>
                </TabsTrigger>
                <TabsTrigger value="messages" className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  <span className="hidden sm:inline">Messages</span>
                </TabsTrigger>
                <TabsTrigger value="instances" className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  <span className="hidden sm:inline">Instances</span>
                </TabsTrigger>
                <TabsTrigger value="system" className="flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  <span className="hidden sm:inline">System</span>
                </TabsTrigger>
                <TabsTrigger value="logs" className="flex items-center gap-2">
                  <ScrollText className="h-4 w-4" />
                  <span className="hidden sm:inline">Logs</span>
                </TabsTrigger>
                <TabsTrigger value="manage" className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  <span className="hidden sm:inline">Manage</span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-6">
                <OverviewTab />
              </TabsContent>

              <TabsContent value="messages" className="mt-6">
                <MessagesTab />
              </TabsContent>

              <TabsContent value="instances" className="mt-6">
                <InstancesTab />
              </TabsContent>

              <TabsContent value="system" className="mt-6">
                <SystemTab />
              </TabsContent>

              <TabsContent value="logs" className="mt-6">
                <LogsTab />
              </TabsContent>

              <TabsContent value="manage" className="mt-6">
                <ManageTab />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>

      {/* Create/Edit Instance Dialog */}
      <InstanceDialog
        open={createDialogOpen || editingInstance !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCreateDialogOpen(false);
            setEditingInstance(null);
          }
        }}
        instance={editingInstance}
        onInstanceCreated={(instanceName, channelType) => {
          if (channelType === 'whatsapp') {
            setQrInstance(instanceName);
          }
        }}
      />

      {/* QR Code Dialog */}
      {qrInstance && (
        <QRCodeDialog
          open={qrInstance !== null}
          onOpenChange={(open) => !open && setQrInstance(null)}
          instanceName={qrInstance}
        />
      )}
    </DashboardLayout>
  );
}
