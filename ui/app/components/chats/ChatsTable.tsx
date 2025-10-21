import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/app/components/ui/table'
import { Badge } from '@/app/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import { Button } from '@/app/components/ui/button'
import { Skeleton } from '@/app/components/ui/skeleton'
import type { Chat } from '@/lib/conveyor/schemas/omni-schema'

interface ChatsTableProps {
  chats: Chat[]
  loading: boolean
  page: number
  pageSize: number
  totalCount: number
  hasMore: boolean
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  onRowClick: (chat: Chat) => void
}

const chatTypeIcons: Record<string, string> = {
  direct: '💬',
  group: '👥',
  channel: '📢',
  thread: '🧵',
}

export function ChatsTable({
  chats,
  loading,
  page,
  pageSize,
  totalCount,
  hasMore,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: ChatsTableProps) {
  const columns: ColumnDef<Chat>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-sm">
            {chatTypeIcons[row.original.chat_type || 'direct'] || '💬'}
          </div>
          <span className="font-medium">{row.original.name || 'Unknown'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'chat_type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge variant="default" className="capitalize">
          {row.original.chat_type}
        </Badge>
      ),
    },
    {
      accessorKey: 'last_message_text',
      header: 'Last Message',
      cell: ({ row }) => {
        // Try multiple sources for last message text
        let lastMessage =
          row.original.last_message_text ||
          row.original.channel_data?.raw_data?.lastMessage?.message ||
          row.original.channel_data?.raw_data?.lastMessage?.text ||
          row.original.channel_data?.last_message_text

        // Handle complex message objects (WhatsApp protocol messages)
        if (lastMessage && typeof lastMessage === 'object') {
          // Extract text from various WhatsApp message types
          lastMessage =
            lastMessage.conversation ||
            lastMessage.extendedTextMessage?.text ||
            lastMessage.imageMessage?.caption ||
            lastMessage.videoMessage?.caption ||
            lastMessage.documentMessage?.caption ||
            '[Media]'
        }

        // Ensure we only render strings
        const displayMessage = typeof lastMessage === 'string' ? lastMessage : 'No messages'

        return (
          <span className="text-sm text-zinc-400 truncate max-w-xs block">
            {displayMessage}
          </span>
        )
      },
    },
    {
      accessorKey: 'unread_count',
      header: 'Unread',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {(row.original.unread_count || 0) > 0 ? (
            <Badge variant="destructive" className="rounded-full">
              {row.original.unread_count}
            </Badge>
          ) : (
            <span className="text-zinc-500">—</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'last_message_at',
      header: 'Updated',
      cell: ({ row }) => (
        <span className="text-sm text-zinc-400">
          {row.original.last_message_at
            ? new Date(row.original.last_message_at).toLocaleDateString()
            : 'N/A'}
        </span>
      ),
    },
  ]

  const table = useReactTable({
    data: chats,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  if (loading && chats.length === 0) {
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

  if (!loading && chats.length === 0) {
    return (
      <div className="rounded-md border border-zinc-800 p-8 text-center">
        <p className="text-zinc-400">No chats found</p>
      </div>
    )
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-zinc-800">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                onClick={() => onRowClick(row.original)}
                className="cursor-pointer"
              >
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

      {/* Pagination Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400">Rows per page:</span>
          <Select value={pageSize.toString()} onValueChange={(v) => onPageSizeChange(Number(v))}>
            <SelectTrigger className="w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="25">25</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-400">
            Page {page} of {totalPages} ({totalCount} total)
          </span>
          <div className="flex gap-2">
            <Button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1 || loading}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            <Button
              onClick={() => onPageChange(page + 1)}
              disabled={!hasMore || loading}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
