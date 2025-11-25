import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { ChartContainer, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';

interface StatusBreakdownData {
  completed: number;
  processing: number;
  failed: number;
}

interface StatusBreakdownChartProps {
  data: StatusBreakdownData;
  className?: string;
}

const chartConfig = {
  completed: {
    label: 'Completed',
    color: 'hsl(var(--chart-success))',
  },
  processing: {
    label: 'Processing',
    color: 'hsl(var(--chart-processing))',
  },
  failed: {
    label: 'Failed',
    color: 'hsl(var(--chart-failed))',
  },
} satisfies ChartConfig;

export function StatusBreakdownChart({ data, className }: StatusBreakdownChartProps) {
  const chartData = [
    { name: 'Completed', value: data.completed, fill: chartConfig.completed.color },
    { name: 'Processing', value: data.processing, fill: chartConfig.processing.color },
    { name: 'Failed', value: data.failed, fill: chartConfig.failed.color },
  ].filter(item => item.value > 0);

  const total = data.completed + data.processing + data.failed;

  if (total === 0) {
    return (
      <div className={`flex items-center justify-center h-[200px] text-muted-foreground ${className || ''}`}>
        No data available
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className={`h-[200px] ${className || ''}`}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltipContent />} />
        <Legend />
      </PieChart>
    </ChartContainer>
  );
}
