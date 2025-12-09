import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { ChartContainer, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';

interface MessageTypesChartProps {
  data: Record<string, number>;
  className?: string;
  horizontal?: boolean;
}

const typeColors: Record<string, string> = {
  text: 'hsl(var(--chart-text))',
  image: 'hsl(var(--chart-image))',
  audio: 'hsl(var(--chart-audio))',
  reaction: 'hsl(var(--chart-reaction))',
  document: 'hsl(var(--chart-document))',
  sticker: 'hsl(var(--chart-sticker))',
  video: 'hsl(var(--chart-2))',
  unknown: 'hsl(var(--muted-foreground))',
};

const chartConfig = {
  count: {
    label: 'Count',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

export function MessageTypesChart({ data, className, horizontal = true }: MessageTypesChartProps) {
  const chartData = Object.entries(data)
    .map(([type, count]) => ({
      type: type.charAt(0).toUpperCase() + type.slice(1),
      count,
      fill: typeColors[type] || typeColors.unknown,
    }))
    .sort((a, b) => b.count - a.count);

  if (chartData.length === 0) {
    return (
      <div className={`flex items-center justify-center h-[200px] text-muted-foreground ${className || ''}`}>
        No data available
      </div>
    );
  }

  if (horizontal) {
    return (
      <ChartContainer config={chartConfig} className={`h-[200px] ${className || ''}`}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="type"
            width={70}
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltipContent />} />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={20}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer config={chartConfig} className={`h-[200px] ${className || ''}`}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
        <XAxis
          dataKey="type"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis hide />
        <Tooltip content={<ChartTooltipContent />} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={30}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}
