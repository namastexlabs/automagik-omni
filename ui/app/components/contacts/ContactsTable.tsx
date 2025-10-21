import { useState, useEffect, useMemo } from 'react'
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
import type { Contact } from '@/lib/main/omni-api-client'
import type { AccessRule } from '@/lib/conveyor/schemas/omni-schema'
import { useConveyor } from '@/app/hooks/use-conveyor'

interface ContactsTableProps {
  contacts: Contact[]
  loading: boolean
  page: number
  pageSize: number
  totalCount: number
  hasMore: boolean
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  onRowClick: (contact: Contact) => void
}

export function ContactsTable({
  contacts,
  loading,
  page,
  pageSize,
  totalCount,
  hasMore,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: ContactsTableProps) {
  const { omni } = useConveyor()
  const [accessRules, setAccessRules] = useState<AccessRule[]>([])
  const [rulesLoading, setRulesLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Load access rules on mount and when contacts change
  useEffect(() => {
    const loadRules = async () => {
      try {
        setRulesLoading(true)
        const rules = await omni.listAccessRules()
        setAccessRules(rules)
      } catch (err) {
        console.error('Failed to load access rules:', err)
      } finally {
        setRulesLoading(false)
      }
    }

    if (contacts.length > 0) {
      loadRules()
    }
  }, [contacts.length, omni])

  // Clear messages after 3 seconds
  useEffect(() => {
    if (successMessage || errorMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null)
        setErrorMessage(null)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [successMessage, errorMessage])

  // Build a map for fast access rule lookups
  const accessRulesMap = useMemo(() => {
    const map = new Map<string, AccessRule>()

    accessRules.forEach((rule) => {
      // Support wildcard rules (prefix matching with *)
      if (rule.phone_number.endsWith('*')) {
        const prefix = rule.phone_number.slice(0, -1)
        contacts.forEach((contact) => {
          const phone = contact.channel_data?.phone || contact.channel_data?.jid || ''
          if (phone.startsWith(prefix)) {
            // Only set if no exact match already exists
            if (!map.has(phone)) {
              map.set(phone, rule)
            }
          }
        })
      } else {
        // Exact match
        map.set(rule.phone_number, rule)
      }
    })

    return map
  }, [accessRules, contacts])

  // Get access status for a contact
  const getAccessStatus = (contact: Contact): { status: 'blocked' | 'allowed' | 'no-rule'; rule?: AccessRule } => {
    const phone = contact.channel_data?.phone || contact.channel_data?.jid || ''
    if (!phone) return { status: 'no-rule' }

    const rule = accessRulesMap.get(phone)
    if (!rule) return { status: 'no-rule' }

    return {
      status: rule.rule_type === 'block' ? 'blocked' : 'allowed',
      rule,
    }
  }

  // Handle block action
  const handleBlock = async (contact: Contact) => {
    const phone = contact.channel_data?.phone || contact.channel_data?.jid || ''
    if (!phone) {
      setErrorMessage('Cannot block: No phone number found')
      return
    }

    try {
      setActionLoading(`block-${contact.id}`)
      setErrorMessage(null)

      await omni.createAccessRule({
        phone_number: phone,
        rule_type: 'block',
        instance_name: contact.instance_name || undefined,
      })

      // Reload rules
      const updatedRules = await omni.listAccessRules()
      setAccessRules(updatedRules)

      setSuccessMessage(`Blocked ${phone}`)
    } catch (err) {
      console.error('Failed to block contact:', err)
      setErrorMessage(err instanceof Error ? err.message : 'Failed to block contact')
    } finally {
      setActionLoading(null)
    }
  }

  // Handle allow action (delete blocking rule)
  const handleAllow = async (contact: Contact, rule: AccessRule) => {
    const phone = contact.channel_data?.phone || contact.channel_data?.jid || ''

    try {
      setActionLoading(`allow-${contact.id}`)
      setErrorMessage(null)

      await omni.deleteAccessRule(rule.id)

      // Reload rules
      const updatedRules = await omni.listAccessRules()
      setAccessRules(updatedRules)

      setSuccessMessage(`Allowed ${phone}`)
    } catch (err) {
      console.error('Failed to allow contact:', err)
      setErrorMessage(err instanceof Error ? err.message : 'Failed to allow contact')
    } finally {
      setActionLoading(null)
    }
  }

  const columns: ColumnDef<Contact>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          {row.original.avatar_url ? (
            <img
              src={row.original.avatar_url}
              alt={row.original.name || 'Contact'}
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-sm">
              {row.original.name?.charAt(0).toUpperCase() || '?'}
            </div>
          )}
          <span className="font-medium">{row.original.name || 'Unknown'}</span>
        </div>
      ),
    },
    {
      accessorKey: 'phone_number',
      header: 'Phone',
      cell: ({ row }) => (
        <span className="font-mono text-sm">
          {row.original.channel_data?.phone || row.original.channel_data?.jid || 'N/A'}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span className="text-sm text-zinc-400">{row.original.status || 'N/A'}</span>
      ),
    },
    {
      accessorKey: 'channel_type',
      header: 'Channel',
      cell: ({ row }) => <Badge variant="default">{row.original.channel_type}</Badge>,
    },
    {
      id: 'access',
      header: 'Access',
      cell: ({ row }) => {
        const contact = row.original
        const { status, rule } = getAccessStatus(contact)
        const isLoading = actionLoading === `block-${contact.id}` || actionLoading === `allow-${contact.id}`

        return (
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            {status === 'blocked' && (
              <>
                <Badge variant="destructive" className="text-xs">
                  Blocked
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => rule && handleAllow(contact, rule)}
                  disabled={isLoading || rulesLoading}
                >
                  {isLoading ? 'Processing...' : 'Allow'}
                </Button>
              </>
            )}
            {status === 'allowed' && (
              <>
                <Badge variant="default" className="text-xs bg-green-600">
                  Allowed
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBlock(contact)}
                  disabled={isLoading || rulesLoading}
                >
                  {isLoading ? 'Processing...' : 'Block'}
                </Button>
              </>
            )}
            {status === 'no-rule' && (
              <>
                <Badge variant="secondary" className="text-xs">
                  No Rule
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBlock(contact)}
                  disabled={isLoading || rulesLoading}
                >
                  {isLoading ? 'Processing...' : 'Block'}
                </Button>
              </>
            )}
          </div>
        )
      },
    },
  ]

  const table = useReactTable({
    data: contacts,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  if (loading && contacts.length === 0) {
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

  if (!loading && contacts.length === 0) {
    return (
      <div className="rounded-md border border-zinc-800 p-8 text-center">
        <p className="text-zinc-400">No contacts found</p>
      </div>
    )
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="space-y-4">
      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-900/50 border border-green-500 text-green-200 px-4 py-3 rounded">
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
          {errorMessage}
        </div>
      )}

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
