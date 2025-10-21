import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { ContactsTable } from '@/app/components/contacts/ContactsTable'
import { ContactSearch } from '@/app/components/contacts/ContactSearch'
import { ContactDetailsPanel } from '@/app/components/contacts/ContactDetailsPanel'
import { Button } from '@/app/components/ui/button'
import type { Contact } from '@/lib/conveyor/schemas/omni-schema'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'

export default function Contacts() {
  const { omni } = useConveyor()
  const [instances, setInstances] = useState<Instance[]>([])
  const [selectedInstance, setSelectedInstance] = useState<string>('')
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [pagination, setPagination] = useState({ page: 1, pageSize: 50 })
  const [totalCount, setTotalCount] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  // Load instances on mount
  useEffect(() => {
    const loadInstances = async () => {
      try {
        const instancesList = await omni.listInstances()
        setInstances(instancesList)
        if (instancesList.length > 0 && !selectedInstance) {
          setSelectedInstance(instancesList[0].name)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load instances')
      }
    }
    loadInstances()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load contacts when instance or pagination changes
  useEffect(() => {
    const loadContacts = async () => {
      if (!selectedInstance) return

      setLoading(true)
      setError(null)
      try {
        const result = await omni.listContacts(
          selectedInstance,
          pagination.page,
          pagination.pageSize,
          searchQuery || undefined
        )
        setContacts(result.contacts)  // Changed from result.data
        setTotalCount(result.total_count)
        setHasMore(result.has_more)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load contacts')
        setContacts([])
      } finally {
        setLoading(false)
      }
    }

    loadContacts()
  }, [selectedInstance, pagination, searchQuery, omni])

  const handleSearch = (value: string) => {
    setSearchQuery(value)
    setPagination({ ...pagination, page: 1 }) // Reset to page 1 on search
  }

  const handlePageChange = (page: number) => {
    setPagination({ ...pagination, page })
  }

  const handlePageSizeChange = (pageSize: number) => {
    setPagination({ page: 1, pageSize })
  }

  const handleRowClick = (contact: Contact) => {
    setSelectedContact(contact)
  }

  const handleExportCSV = () => {
    if (contacts.length === 0) return

    const headers = ['Name', 'Phone Number', 'Status', 'Channel Type', 'ID']
    const rows = contacts.map((c) => [
      c.name || 'Unknown',
      c.channel_data?.phone_number || c.id,
      c.status || 'N/A',
      c.channel_type,
      c.id,
    ])

    const csv = [headers, ...rows].map((row) => row.map((v) => `"${v}"`).join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `contacts-${selectedInstance}-${new Date().toISOString()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold">Contacts</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-zinc-400">Instance:</span>
              <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select instance..." />
                </SelectTrigger>
                <SelectContent>
                  {instances.map((instance) => (
                    <SelectItem key={instance.id} value={instance.name}>
                      {instance.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {!selectedInstance && instances.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center">
            <p className="text-zinc-400">No instances available. Please create an instance first.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <ContactSearch
                value={searchQuery}
                onChange={handleSearch}
                disabled={loading || !selectedInstance}
              />
              <Button
                onClick={handleExportCSV}
                disabled={loading || contacts.length === 0}
                variant="outline"
              >
                Export CSV
              </Button>
            </div>

            <ContactsTable
              contacts={contacts}
              loading={loading}
              page={pagination.page}
              pageSize={pagination.pageSize}
              totalCount={totalCount}
              hasMore={hasMore}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
              onRowClick={handleRowClick}
            />
          </>
        )}
      </div>

      <ContactDetailsPanel contact={selectedContact} onClose={() => setSelectedContact(null)} />
    </div>
  )
}
