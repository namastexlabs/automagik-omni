import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'

interface SuccessRateChartProps {
  data: Array<{ name: string; value: number }>
}

const COLORS = {
  Success: '#22c55e', // green
  Failed: '#ef4444',  // red
}

export function SuccessRateChart({ data }: SuccessRateChartProps) {
  // Calculate total for percentage display
  const total = data.reduce((sum, entry) => sum + entry.value, 0)

  // Filter out entries with 0 value to avoid rendering empty slices
  const filteredData = data.filter(entry => entry.value > 0)

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">Success vs Failed</CardTitle>
      </CardHeader>
      <CardContent>
        {filteredData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={filteredData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value} (${((value / total) * 100).toFixed(1)}%)`}
                outerRadius={90}
                innerRadius={60}
                fill="#8884d8"
                dataKey="value"
                paddingAngle={2}
              >
                {filteredData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[entry.name as keyof typeof COLORS] || '#6b7280'}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#18181b',
                  border: '1px solid #3f3f46',
                  borderRadius: '0.5rem',
                  color: '#fff',
                }}
                formatter={(value: number) => [value, 'Messages']}
              />
              <Legend
                wrapperStyle={{ color: '#fff' }}
                iconType="circle"
              />
            </PieChart>
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
