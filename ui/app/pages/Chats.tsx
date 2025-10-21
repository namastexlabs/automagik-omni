import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { ChatsTable } from '@/app/components/chats/ChatsTable'
import { ChatTypeFilter } from '@/app/components/chats/ChatTypeFilter'
import { ChatDetailsPanel } from '@/app/components/chats/ChatDetailsPanel'
import type { Chat } from '@/lib/main/omni-api-client'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'

export default function Chats() {
  const { omni } = useConveyor()
  const [instances, setInstances] = useState<Instance[]>([])
  const [selectedInstance, setSelectedInstance] = useState<string>('')
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatTypeFilter, setChatTypeFilter] = useState<string | undefined>(undefined)
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

  // Load chats when instance, pagination, or filter changes
  useEffect(() => {
    const loadChats = async () => {
      if (!selectedInstance) return

      setLoading(true)
      setError(null)
      try {
        const result = await omni.listChats(
          selectedInstance,
          pagination.page,
          pagination.pageSize,
          chatTypeFilter
        )
        setChats(result.chats)  // Changed from result.data
        setTotalCount(result.total_count)
        setHasMore(result.has_more)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load chats')
        setChats([])
      } finally {
        setLoading(false)
      }
    }

    loadChats()
  }, [selectedInstance, pagination, chatTypeFilter, omni])

  const handleFilterChange = (type: string | undefined) => {
    setChatTypeFilter(type)
    setPagination({ ...pagination, page: 1 }) // Reset to page 1 on filter change
  }

  const handlePageChange = (page: number) => {
    setPagination({ ...pagination, page })
  }

  const handlePageSizeChange = (pageSize: number) => {
    setPagination({ page: 1, pageSize })
  }

  const handleRowClick = (chat: Chat) => {
    setSelectedChat(chat)
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold">Chats</h1>
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
              <ChatTypeFilter
                selected={chatTypeFilter}
                onChange={handleFilterChange}
                disabled={loading || !selectedInstance}
              />
            </div>

            <ChatsTable
              chats={chats}
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

      <ChatDetailsPanel chat={selectedChat} onClose={() => setSelectedChat(null)} />
    </div>
  )
}
