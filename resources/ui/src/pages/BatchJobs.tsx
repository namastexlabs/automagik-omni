import { useState, Fragment } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
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
import { api, BatchJob, formatDateTime } from '@/lib';
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
  ChevronDown,
  ChevronRight,
  AlertCircle,
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
  const [selectedInstance, setSelectedInstance] = useState<string>('__all__');
  const [daysBack, setDaysBack] = useState(30);
  const [limit, setLimit] = useState(100);
  const [language, setLanguage] = useState('pt');
  const [contentTypes, setContentTypes] = useState<string[]>(['audio']);
  const [forceReprocess, setForceReprocess] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

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

  // Fetch job details when expanded
  const { data: jobDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ['batchJobDetails', expandedJobId],
    queryFn: () => (expandedJobId ? api.batchJobs.getDetails(expandedJobId) : null),
    enabled: !!expandedJobId,
  });

  // Start reprocess mutation
  const startMutation = useMutation({
    mutationFn: () =>
      api.batchJobs.startReprocess({
        instance_name: selectedInstance === '__all__' ? undefined : selectedInstance,
        days_back: daysBack,
        limit: limit === 0 ? undefined : limit, // 0 means "all" - send undefined
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
  const completedJobs =
    jobs?.filter((j) => j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled') ?? [];

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
                          <SelectItem value="__all__">All instances</SelectItem>
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
                        <Select value={String(daysBack)} onValueChange={(v) => setDaysBack(parseInt(v))}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="7">7 days</SelectItem>
                            <SelectItem value="14">14 days</SelectItem>
                            <SelectItem value="30">30 days</SelectItem>
                            <SelectItem value="60">60 days</SelectItem>
                            <SelectItem value="90">90 days</SelectItem>
                            <SelectItem value="180">180 days</SelectItem>
                            <SelectItem value="365">1 year</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid gap-2">
                        <Label>Max Items</Label>
                        <Select value={String(limit)} onValueChange={(v) => setLimit(parseInt(v))}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="50">50</SelectItem>
                            <SelectItem value="100">100</SelectItem>
                            <SelectItem value="250">250</SelectItem>
                            <SelectItem value="500">500</SelectItem>
                            <SelectItem value="1000">1000</SelectItem>
                            <SelectItem value="0">All</SelectItem>
                          </SelectContent>
                        </Select>
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
                        <TableHead className="w-8"></TableHead>
                        <TableHead>Instance</TableHead>
                        <TableHead>Types</TableHead>
                        <TableHead>Period</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Found / Processed</TableHead>
                        <TableHead>Duration</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {completedJobs.map((job) => {
                        const params = job.request_params;
                        const types = params?.content_types || [];
                        const isExpanded = expandedJobId === job.job_id;
                        return (
                          <Fragment key={job.job_id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => setExpandedJobId(isExpanded ? null : job.job_id)}
                            >
                              <TableCell className="w-8">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                )}
                              </TableCell>
                              <TableCell className="text-sm">{job.instance_name || 'All'}</TableCell>
                              <TableCell>
                                <div className="flex gap-1">
                                  {types.includes('audio') && (
                                    <FileAudio className="h-4 w-4 text-blue-500" title="Audio" />
                                  )}
                                  {types.includes('image') && (
                                    <FileImage className="h-4 w-4 text-green-500" title="Image" />
                                  )}
                                  {types.includes('document') && (
                                    <FileText className="h-4 w-4 text-orange-500" title="Document" />
                                  )}
                                  {types.length === 0 && <span className="text-muted-foreground text-xs">-</span>}
                                </div>
                              </TableCell>
                              <TableCell className="text-sm">
                                {params?.days_back ? `${params.days_back}d` : '-'}
                              </TableCell>
                              <TableCell>{getStatusBadge(job.status)}</TableCell>
                              <TableCell>
                                <div className="text-sm space-y-0.5">
                                  <div className="flex items-center gap-1">
                                    <span className="text-muted-foreground">Found:</span>
                                    <span>{job.total_found || 0}</span>
                                  </div>
                                  {job.skipped_items > 0 && (
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                      <span>Skipped:</span>
                                      <span>{job.skipped_items}</span>
                                    </div>
                                  )}
                                  <div className="flex items-center gap-1">
                                    <span className="text-green-600">Processed:</span>
                                    <span className="text-green-600">{job.processed_items}</span>
                                    {job.failed_items > 0 && (
                                      <span className="text-destructive">({job.failed_items} failed)</span>
                                    )}
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell className="text-sm">
                                {formatDuration(job.started_at, job.completed_at)}
                              </TableCell>
                              <TableCell>
                                {job.total_cost_usd !== null && job.total_cost_usd > 0 ? (
                                  <span className="flex items-center gap-1 text-sm">
                                    <DollarSign className="h-3 w-3" />
                                    {formatCost(job.total_cost_usd)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground text-xs">-</span>
                                )}
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">
                                {job.created_at ? formatDateTime(job.created_at) : '-'}
                              </TableCell>
                            </TableRow>
                            {isExpanded && (
                              <TableRow className="bg-muted/30">
                                <TableCell colSpan={9} className="p-4">
                                  {isLoadingDetails ? (
                                    <div className="flex items-center justify-center py-4">
                                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                      <span className="ml-2 text-sm text-muted-foreground">Loading details...</span>
                                    </div>
                                  ) : jobDetails ? (
                                    <div className="space-y-4">
                                      {/* Processed Items */}
                                      {jobDetails.processed_items.length > 0 && (
                                        <div>
                                          <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                                            Processed Items ({jobDetails.processed_count})
                                          </h4>
                                          <div className="space-y-2 max-h-60 overflow-y-auto">
                                            {jobDetails.processed_items.map((item, idx) => (
                                              <div
                                                key={`${item.message_id}-${idx}`}
                                                className="bg-background rounded-md p-3 text-sm border"
                                              >
                                                <div className="flex items-start justify-between gap-4">
                                                  <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                      <Badge variant="outline" className="text-xs">
                                                        {item.content_type.replace('_', ' ')}
                                                      </Badge>
                                                      {item.processor_name && (
                                                        <span className="text-xs text-muted-foreground">
                                                          via {item.processor_name}
                                                        </span>
                                                      )}
                                                    </div>
                                                    {item.content_preview && (
                                                      <p className="text-xs text-muted-foreground line-clamp-2">
                                                        {item.content_preview}
                                                      </p>
                                                    )}
                                                  </div>
                                                  <div className="text-xs text-muted-foreground whitespace-nowrap">
                                                    {item.processed_at ? formatDateTime(item.processed_at) : ''}
                                                  </div>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Failed Items */}
                                      {jobDetails.failed_items.length > 0 && (
                                        <div>
                                          <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                                            <AlertCircle className="h-4 w-4 text-destructive" />
                                            Failed Items ({jobDetails.failed_count})
                                          </h4>
                                          <div className="space-y-2 max-h-40 overflow-y-auto">
                                            {jobDetails.failed_items.map((item, idx) => (
                                              <div
                                                key={`${item.message_id}-${idx}`}
                                                className="bg-destructive/10 rounded-md p-3 text-sm border border-destructive/20"
                                              >
                                                <div className="flex items-start justify-between gap-4">
                                                  <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                      <Badge variant="destructive" className="text-xs">
                                                        {item.content_type.replace('_', ' ')}
                                                      </Badge>
                                                      <span className="text-xs font-mono text-muted-foreground">
                                                        {item.message_id.substring(0, 12)}...
                                                      </span>
                                                    </div>
                                                    {item.error_message && (
                                                      <p className="text-xs text-destructive">{item.error_message}</p>
                                                    )}
                                                  </div>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* No items */}
                                      {jobDetails.processed_items.length === 0 &&
                                        jobDetails.failed_items.length === 0 && (
                                          <div className="text-center py-4 text-sm text-muted-foreground">
                                            No detailed item information available for this job.
                                          </div>
                                        )}
                                    </div>
                                  ) : (
                                    <div className="text-center py-4 text-sm text-muted-foreground">
                                      Failed to load job details.
                                    </div>
                                  )}
                                </TableCell>
                              </TableRow>
                            )}
                          </Fragment>
                        );
                      })}
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
