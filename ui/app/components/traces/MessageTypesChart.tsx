import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'

interface MessageTypesChartProps {
  data: Array<{ type: string; count: number }>
}

// Color mapping for different message types
const MESSAGE_TYPE_COLORS: Record<string, string> = {
  text: '#3b82f6', // blue
  media: '#22c55e', // green
  image: '#22c55e', // green
  audio: '#a855f7', // purple
  video: '#f97316', // orange
  document: '#06b6d4', // cyan
  sticker: '#ec4899', // pink
  contact: '#8b5cf6', // violet
  reaction: '#eab308', // yellow
  unknown: '#6b7280', // gray
}

export function MessageTypesChart({ data }: MessageTypesChartProps) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">
          Message Types Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="type"
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#18181b',
                  border: '1px solid #3f3f46',
                  borderRadius: '0.5rem',
                }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: number) => [value, 'Messages']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={MESSAGE_TYPE_COLORS[entry.type] || '#6b7280'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[300px] flex items-center justify-center text-zinc-500">
            No data available
          </div>
        )}
      </CardContent>
    </Card>
  )
}
