import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { Asterisk } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/app/components/ui/table'
import { Button } from '@/app/components/ui/button'
import { Skeleton } from '@/app/components/ui/skeleton'
import { RuleTypeBadge } from './RuleTypeBadge'
import { RuleScopePill } from './RuleScopePill'

export interface AccessRule {
  id: number
  phone_number: string
  rule_type: 'allow' | 'block'
  instance_name: string | null
  created_at?: string
  updated_at?: string
}

interface AccessRulesTableProps {
  rules: AccessRule[]
  onDelete: (rule: AccessRule) => void
}

export function AccessRulesTable({ rules, onDelete }: AccessRulesTableProps) {
  const loading = false // Remove unused loading param
  const [sorting, setSorting] = useState<SortingState>([])

  const columns: ColumnDef<AccessRule>[] = [
    {
      accessorKey: 'phone_number',
      header: 'Phone Number',
      cell: ({ row }) => {
        const phoneNumber = row.original.phone_number
        const isWildcard = phoneNumber === '*'
        const hasWildcard = phoneNumber.includes('*')

        return (
          <div className="flex items-center gap-2">
            {isWildcard ? (
              <>
                <Asterisk className="h-4 w-4 text-yellow-500" />
                <span className="font-mono text-sm font-medium text-yellow-500">All Numbers</span>
              </>
            ) : hasWildcard ? (
              <>
                <Asterisk className="h-4 w-4 text-blue-400" />
                <span className="font-mono text-sm font-medium">{phoneNumber}</span>
              </>
            ) : (
              <span className="font-mono text-sm font-medium">{phoneNumber}</span>
            )}
          </div>
        )
      },
    },
    {
      accessorKey: 'rule_type',
      header: 'Type',
      cell: ({ row }) => <RuleTypeBadge type={row.original.rule_type} />,
    },
    {
      accessorKey: 'instance_name',
      header: 'Scope',
      cell: ({ row }) => <RuleScopePill instanceName={row.original.instance_name} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Created At',
      cell: ({ row }) => {
        if (!row.original.created_at) return <span className="text-zinc-500 text-sm">N/A</span>
        const date = new Date(row.original.created_at)
        return (
          <span className="text-sm text-zinc-300">
            {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )
      },
    },
    {
      accessorKey: 'updated_at',
      header: 'Updated At',
      cell: ({ row }) => {
        if (!row.original.updated_at) return <span className="text-zinc-500 text-sm">N/A</span>
        const date = new Date(row.original.updated_at)
        return (
          <span className="text-sm text-zinc-300">
            {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onDelete(row.original)}
        >
          Delete
        </Button>
      ),
    },
  ]

  const table = useReactTable({
    data: rules,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
  })

  if (loading && rules.length === 0) {
    return (
      <div className="space-y-4">
        <div className="rounded-md border border-zinc-800">
          <div className="p-4">
            <Skeleton className="h-8 w-full mb-4" />
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full mb-2" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!loading && rules.length === 0) {
    return (
      <div className="rounded-md border border-zinc-800 p-12 text-center">
        <p className="text-zinc-400 text-lg mb-2">No access rules</p>
        <p className="text-zinc-500 text-sm">Click "Add Rule" to get started</p>
      </div>
    )
  }

  return (
    <div className="rounded-md border border-zinc-800">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className={header.column.getCanSort() ? 'cursor-pointer select-none' : ''}
                >
                  <div className="flex items-center gap-2">
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getCanSort() && (
                      <span className="text-zinc-500">
                        {{
                          asc: '↑',
                          desc: '↓',
                        }[header.column.getIsSorted() as string] ?? '↕'}
                      </span>
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
