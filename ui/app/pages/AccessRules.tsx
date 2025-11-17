import { useState, useEffect } from 'react'
import { Shield } from 'lucide-react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Button } from '@/app/components/ui/button'
import { AccessRulesTable, type AccessRule } from '@/app/components/access-rules/AccessRulesTable'
import { RuleFilters } from '@/app/components/access-rules/RuleFilters'
import { PhoneNumberTester } from '@/app/components/access-rules/PhoneNumberTester'
import { CreateRuleDialog } from '@/app/components/access-rules/CreateRuleDialog'
import { DeleteRuleDialog } from '@/app/components/access-rules/DeleteRuleDialog'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

export default function AccessRules() {
  const { omni } = useConveyor()
  const [rules, setRules] = useState<AccessRule[]>([])
  const [filteredRules, setFilteredRules] = useState<AccessRule[]>([])
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    instanceName: '',
    ruleType: '',
  })

  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedRule, setSelectedRule] = useState<AccessRule | null>(null)

  // Tester visibility
  const [showTester, setShowTester] = useState(false)

  // Load instances on mount
  useEffect(() => {
    const loadInstances = async () => {
      try {
        const instancesList = await omni.listInstances()
        setInstances(instancesList)
      } catch (err) {
        console.error('Failed to load instances:', err)
      }
    }
    loadInstances()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load rules
  const fetchRules = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await omni.listAccessRules()
      setRules(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load access rules')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRules()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Apply filters
  useEffect(() => {
    let filtered = [...rules]

    // Search filter (phone number)
    if (filters.search.trim()) {
      const searchLower = filters.search.toLowerCase().trim()
      filtered = filtered.filter((rule) =>
        rule.phone_number.toLowerCase().includes(searchLower)
      )
    }

    // Instance filter
    if (filters.instanceName) {
      filtered = filtered.filter((rule) => rule.instance_name === filters.instanceName)
    }

    // Rule type filter
    if (filters.ruleType) {
      filtered = filtered.filter((rule) => rule.rule_type === filters.ruleType)
    }

    setFilteredRules(filtered)
  }, [rules, filters])

  const handleDeleteClick = (rule: AccessRule) => {
    setSelectedRule(rule)
    setShowDeleteDialog(true)
  }

  const handleDeleted = () => {
    fetchRules()
    setSelectedRule(null)
  }

  const handleCreated = () => {
    fetchRules()
  }

  const handleFilterChange = (newFilters: {
    search: string
    instanceName: string
    ruleType: string
  }) => {
    setFilters(newFilters)
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Shield className="h-8 w-8 text-white" />
              <h1 className="text-4xl font-bold">Access Rules</h1>
            </div>
            <p className="text-zinc-400">
              Manage phone number access controls (allowlist/blocklist)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => setShowTester(!showTester)}
            >
              {showTester ? 'Hide' : 'Show'} Phone Tester
            </Button>
            <Button onClick={() => setShowCreateDialog(true)} disabled={loading}>
              + Add Rule
            </Button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Filters */}
        <RuleFilters
          instances={instances}
          onFilterChange={handleFilterChange}
          className="mb-6"
        />

        {/* Main content */}
        {loading && rules.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-zinc-400">Loading access rules...</div>
          </div>
        ) : (
          <>
            <AccessRulesTable
              rules={filteredRules}
              onDelete={handleDeleteClick}
            />

            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-zinc-400">
                {filteredRules.length === 0
                  ? 'No rules'
                  : `${filteredRules.length} rule${filteredRules.length === 1 ? '' : 's'}`}
                {filters.search || filters.instanceName || filters.ruleType
                  ? ` (filtered from ${rules.length} total)`
                  : ''}
              </div>
              <Button variant="outline" onClick={fetchRules} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh'}
              </Button>
            </div>
          </>
        )}

        {/* Phone Number Tester */}
        {showTester && (
          <div className="mt-8">
            <PhoneNumberTester
              rules={rules}
              instanceNames={instances.map(i => i.name)}
            />
          </div>
        )}

        {/* Dialogs */}
        <CreateRuleDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
          onCreated={handleCreated}
          instances={instances}
        />

        <DeleteRuleDialog
          rule={selectedRule}
          open={showDeleteDialog}
          onOpenChange={setShowDeleteDialog}
          onDeleted={handleDeleted}
        />
      </div>
    </div>
  )
}
