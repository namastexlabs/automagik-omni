import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'

interface AnalyticsCardsProps {
  totalMessages: number
  successRate: number
  averageDuration: number
  failedCount: number
}

export function AnalyticsCards({
  totalMessages,
  successRate,
  averageDuration,
  failedCount,
}: AnalyticsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      {/* Total Messages */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-400">Total Messages</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-white">{totalMessages.toLocaleString()}</div>
        </CardContent>
      </Card>

      {/* Success Rate */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-400">Success Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-green-500">{successRate.toFixed(1)}%</div>
        </CardContent>
      </Card>

      {/* Average Duration */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-400">Avg Response Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-blue-500">
            {averageDuration > 1000
              ? `${(averageDuration / 1000).toFixed(1)}s`
              : `${averageDuration.toFixed(0)}ms`}
          </div>
        </CardContent>
      </Card>

      {/* Failed Messages */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-zinc-400">Failed Messages</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-red-500">{failedCount.toLocaleString()}</div>
        </CardContent>
      </Card>
    </div>
  )
}
