import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, AlertCircle } from 'lucide-react';
import { DashboardLayout } from '@/components/DashboardLayout';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { api } from '@/lib';

export default function Chats() {
  const [selectedInstance, setSelectedInstance] = useState<string>('');

  // Fetch available instances
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100 }),
  });

  // Auto-select first instance if none selected
  if (!selectedInstance && instances && instances.length > 0) {
    setSelectedInstance(instances[0].name);
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        {/* Header with Instance Selector */}
        <div className="flex items-center justify-between border-b border-border bg-card px-6 py-3">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Chats</h1>
          </div>

          {/* Instance Selector */}
          <Select value={selectedInstance} onValueChange={setSelectedInstance}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select instance" />
            </SelectTrigger>
            <SelectContent>
              {instances?.map((instance) => (
                <SelectItem key={instance.id} value={instance.name}>
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${instance.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                    {instance.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {!selectedInstance && instances && instances.length > 0 && (
            <div className="p-8">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>Please select an instance to view chats</AlertDescription>
              </Alert>
            </div>
          )}

          {instances && instances.length === 0 && (
            <div className="p-8">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>No instances available. Please create an instance first.</AlertDescription>
              </Alert>
            </div>
          )}

          {selectedInstance && <ChatLayout instanceName={selectedInstance} />}
        </div>
      </div>
    </DashboardLayout>
  );
}
