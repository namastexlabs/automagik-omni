import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'
import { MessageSquare, CheckCircle2, Clock, XCircle } from 'lucide-react'

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
  // Determine success rate color based on thresholds
  const getSuccessRateColor = (rate: number) => {
    if (rate >= 90) return 'text-green-500'
    if (rate >= 70) return 'text-yellow-500'
    return 'text-red-500'
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      {/* Total Messages */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-zinc-400">Total Messages</CardTitle>
            <MessageSquare className="h-4 w-4 text-zinc-500" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-white">{totalMessages.toLocaleString()}</div>
        </CardContent>
      </Card>

      {/* Success Rate */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-zinc-400">Success Rate</CardTitle>
            <CheckCircle2 className={`h-4 w-4 ${getSuccessRateColor(successRate)}`} />
          </div>
        </CardHeader>
        <CardContent>
          <div className={`text-3xl font-bold ${getSuccessRateColor(successRate)}`}>
            {successRate.toFixed(1)}%
          </div>
        </CardContent>
      </Card>

      {/* Average Duration */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-zinc-400">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </div>
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
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-zinc-400">Failed Messages</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-red-500">{failedCount.toLocaleString()}</div>
        </CardContent>
      </Card>
    </div>
  )
}
