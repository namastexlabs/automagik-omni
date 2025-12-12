import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { api } from '@/lib';
import { MessageCircle, ArrowRight, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

// Discord icon as SVG
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
  </svg>
);

type ServiceStatus = 'up' | 'down' | 'degraded' | 'unknown';

function getStatusBadge(status: ServiceStatus) {
  switch (status) {
    case 'up':
      return (
        <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Running
        </Badge>
      );
    case 'down':
      return (
        <Badge variant="destructive" className="bg-red-500/10 text-red-500 border-red-500/20">
          <XCircle className="h-3 w-3 mr-1" />
          Stopped
        </Badge>
      );
    case 'degraded':
      return (
        <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
          <AlertCircle className="h-3 w-3 mr-1" />
          Degraded
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary">
          <AlertCircle className="h-3 w-3 mr-1" />
          Unknown
        </Badge>
      );
  }
}

export default function Services() {
  // Fetch health status for services
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 10000,
  });

  // Fetch instances to count them
  const { data: instances, isLoading: instancesLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100 }),
  });

  const evolutionStatus: ServiceStatus = healthData?.services?.evolution?.status || 'unknown';
  const whatsappInstances = instances?.filter((i) => i.channel_type === 'whatsapp') || [];
  const discordInstances = instances?.filter((i) => i.channel_type === 'discord') || [];

  const isLoading = healthLoading || instancesLoading;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader title="Services" subtitle="Manage your messaging channel services" />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {isLoading ? (
              <div className="grid gap-6 md:grid-cols-2">
                {[1, 2].map((i) => (
                  <Card key={i} className="border-border elevation-md">
                    <CardHeader>
                      <Skeleton className="h-12 w-12 rounded-xl mb-4" />
                      <Skeleton className="h-6 w-32 mb-2" />
                      <Skeleton className="h-4 w-48" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-10 w-full" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                {/* WhatsApp Service Card */}
                <Card className="border-border elevation-md hover:elevation-lg transition-all">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="h-12 w-12 rounded-xl bg-[#25D366] flex items-center justify-center">
                        <MessageCircle className="h-6 w-6 text-white" />
                      </div>
                      {getStatusBadge(evolutionStatus)}
                    </div>
                    <CardTitle className="mt-4">WhatsApp</CardTitle>
                    <CardDescription>Connect WhatsApp accounts via Evolution API</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Connected Instances</span>
                      <span className="font-medium">{whatsappInstances.length}</span>
                    </div>
                    <Button asChild className="w-full" variant="outline">
                      <Link to="/services/whatsapp">
                        Manage WhatsApp
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Link>
                    </Button>
                  </CardContent>
                </Card>

                {/* Discord Service Card */}
                <Card className="border-border elevation-md hover:elevation-lg transition-all">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="h-12 w-12 rounded-xl bg-[#5865F2] flex items-center justify-center">
                        <DiscordIcon className="h-6 w-6 text-white" />
                      </div>
                      {discordInstances.length > 0 ? getStatusBadge('up') : getStatusBadge('down')}
                    </div>
                    <CardTitle className="mt-4">Discord</CardTitle>
                    <CardDescription>Connect Discord bots to your server</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Connected Bots</span>
                      <span className="font-medium">{discordInstances.length}</span>
                    </div>
                    <Button asChild className="w-full" variant="outline">
                      <Link to="/services/discord">
                        Manage Discord
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Link>
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
