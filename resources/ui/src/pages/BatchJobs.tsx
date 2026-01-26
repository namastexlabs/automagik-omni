import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { api, BatchJob } from '@/lib';
import {
  Play,
  Square,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileAudio,
  FileImage,
  FileText,
  DollarSign,
  Layers,
  Ban,
} from 'lucide-react';

function formatDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt) return '-';
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const durationMs = end - start;
  if (durationMs < 1000) return `${durationMs}ms`;
  if (durationMs < 60000) return `${(durationMs / 1000).toFixed(1)}s`;
  return `${(durationMs / 60000).toFixed(1)}m`;
}

function formatCost(cost: number | null): string {
  if (cost === null) return '-';
  if (cost < 0.01) return `$${cost.toFixed(6)}`;
  return `$${cost.toFixed(4)}`;
}

function getStatusBadge(status: BatchJob['status']) {
  switch (status) {
    case 'pending':
      return (
        <Badge variant="outline" className="gap-1">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      );
    case 'processing':
      return (
        <Badge className="bg-blue-500 gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      );
    case 'completed':
      return (
        <Badge className="bg-green-500 gap-1">
          <CheckCircle2 className="h-3 w-3" />
          Completed
        </Badge>
      );
    case 'failed':
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    case 'cancelled':
      return (
        <Badge variant="secondary" className="gap-1">
          <Ban className="h-3 w-3" />
          Cancelled
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function BatchJobs() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [daysBack, setDaysBack] = useState(30);
  const [limit, setLimit] = useState(100);
  const [language, setLanguage] = useState('pt');
  const [contentTypes, setContentTypes] = useState<string[]>(['audio']);
  const [forceReprocess, setForceReprocess] = useState(false);

  // Fetch instances for dropdown
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list(),
  });

  // Fetch batch jobs
  const {
    data: jobs,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['batchJobs'],
    queryFn: () => api.batchJobs.list({ limit: 50 }),
    refetchInterval: (query) => {
      // Auto-refresh every 2 seconds if there are running jobs
      const data = query.state.data as BatchJob[] | undefined;
      const hasRunning = data?.some((job) => job.status === 'pending' || job.status === 'processing');
      return hasRunning ? 2000 : false;
    },
  });

  // Start reprocess mutation
  const startMutation = useMutation({
    mutationFn: () =>
      api.batchJobs.startReprocess({
        instance_name: selectedInstance || undefined,
        days_back: daysBack,
        limit,
        language,
        content_types: contentTypes,
        force: forceReprocess,
        async_mode: true,
      }),
    onSuccess: (data) => {
      toast.success(`Job started: ${data.job_id.substring(0, 8)}...`);
      queryClient.invalidateQueries({ queryKey: ['batchJobs'] });
      setIsCreateOpen(false);
    },
    onError: (error: Error) => {
      toast.error(`Failed to start job: ${error.message}`);
    },
  });

  // Cancel job mutation
  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => api.batchJobs.cancel(jobId),
    onSuccess: () => {
      toast.success('Job cancelled');
      queryClient.invalidateQueries({ queryKey: ['batchJobs'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to cancel job: ${error.message}`);
    },
  });

  const toggleContentType = (type: string) => {
    setContentTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  };

  const runningJobs = jobs?.filter((j) => j.status === 'pending' || j.status === 'processing') ?? [];
  const completedJobs = jobs?.filter((j) => j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled') ?? [];

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Media Processing"
          subtitle="Batch reprocess audio, images, and documents"
          icon={<Layers className="h-6 w-6 text-primary" />}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Play className="h-4 w-4 mr-2" />
                    New Job
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[500px]">
                  <DialogHeader>
                    <DialogTitle>Start Media Reprocessing</DialogTitle>
                    <DialogDescription>
                      Process historical messages to extract transcriptions, descriptions, and document content.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    {/* Instance */}
                    <div className="grid gap-2">
                      <Label>Instance (optional)</Label>
                      <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                        <SelectTrigger>
                          <SelectValue placeholder="All instances" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">All instances</SelectItem>
                          {instances?.map((inst) => (
                            <SelectItem key={inst.name} value={inst.name}>
                              {inst.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Content Types */}
                    <div className="grid gap-2">
                      <Label>Content Types</Label>
                      <div className="flex gap-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <Checkbox
                            checked={contentTypes.includes('audio')}
                            onCheckedChange={() => toggleContentType('audio')}
                          />
                          <FileAudio className="h-4 w-4 text-blue-500" />
                          Audio
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <Checkbox
                            checked={contentTypes.includes('image')}
                            onCheckedChange={() => toggleContentType('image')}
                          />
                          <FileImage className="h-4 w-4 text-green-500" />
                          Image
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <Checkbox
                            checked={contentTypes.includes('document')}
                            onCheckedChange={() => toggleContentType('document')}
                          />
                          <FileText className="h-4 w-4 text-orange-500" />
                          Document
                        </label>
                      </div>
                    </div>

                    {/* Days Back & Limit */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="grid gap-2">
                        <Label>Days Back</Label>
                        <Input
                          type="number"
                          value={daysBack}
                          onChange={(e) => setDaysBack(parseInt(e.target.value) || 30)}
                          min={1}
                          max={365}
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label>Max Items</Label>
                        <Input
                          type="number"
                          value={limit}
                          onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
                          min={1}
                          max={1000}
                        />
                      </div>
                    </div>

                    {/* Language */}
                    <div className="grid gap-2">
                      <Label>Language (for audio)</Label>
                      <Select value={language} onValueChange={setLanguage}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pt">Portuguese</SelectItem>
                          <SelectItem value="en">English</SelectItem>
                          <SelectItem value="es">Spanish</SelectItem>
                          <SelectItem value="auto">Auto-detect</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Force Reprocess */}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <Checkbox checked={forceReprocess} onCheckedChange={(c) => setForceReprocess(c === true)} />
                      <span className="text-sm">Force reprocess (include already processed items)</span>
                    </label>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={() => startMutation.mutate()}
                      disabled={startMutation.isPending || contentTypes.length === 0}
                    >
                      {startMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Start Job
                        </>
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          }
        />

        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 max-w-6xl">
            {/* Running Jobs */}
            {runningJobs.length > 0 && (
              <Card className="border-blue-500/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                    Running Jobs ({runningJobs.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {runningJobs.map((job) => (
                    <div key={job.job_id} className="p-4 bg-muted rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getStatusBadge(job.status)}
                          <span className="font-mono text-sm">{job.job_id.substring(0, 8)}...</span>
                          {job.instance_name && (
                            <Badge variant="outline" className="text-xs">
                              {job.instance_name}
                            </Badge>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => cancelMutation.mutate(job.job_id)}
                          disabled={cancelMutation.isPending}
                        >
                          <Square className="h-4 w-4 mr-1" />
                          Cancel
                        </Button>
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>
                            {job.processed_items} / {job.total_items} items
                          </span>
                          <span>{job.progress_percent.toFixed(1)}%</span>
                        </div>
                        <Progress value={job.progress_percent} className="h-2" />
                      </div>
                      {job.current_item && (
                        <div className="text-xs text-muted-foreground">
                          Processing: {job.current_item.substring(0, 20)}...
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Job History */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Job History</CardTitle>
                <CardDescription>Recent batch processing jobs</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : completedJobs.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No completed jobs yet. Start a new job to process media content.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Job ID</TableHead>
                        <TableHead>Instance</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Progress</TableHead>
                        <TableHead>Duration</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {completedJobs.map((job) => (
                        <TableRow key={job.job_id}>
                          <TableCell className="font-mono text-xs">{job.job_id.substring(0, 8)}...</TableCell>
                          <TableCell>{job.instance_name || 'All'}</TableCell>
                          <TableCell>{getStatusBadge(job.status)}</TableCell>
                          <TableCell>
                            <span className="text-sm">
                              {job.processed_items}/{job.total_items}
                              {job.failed_items > 0 && (
                                <span className="text-destructive ml-1">({job.failed_items} failed)</span>
                              )}
                            </span>
                          </TableCell>
                          <TableCell className="text-sm">{formatDuration(job.started_at, job.completed_at)}</TableCell>
                          <TableCell>
                            {job.total_cost_usd !== null && (
                              <span className="flex items-center gap-1 text-sm">
                                <DollarSign className="h-3 w-3" />
                                {formatCost(job.total_cost_usd)}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {job.created_at ? new Date(job.created_at).toLocaleString() : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
