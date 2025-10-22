import { useState } from 'react'
import { Card } from '@/app/components/ui/card'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import { Button } from '@/app/components/ui/button'
import type { AccessRule } from './AccessRulesTable'

interface PhoneNumberTesterProps {
  rules: AccessRule[]
  instanceNames: string[]
}

interface TestResult {
  allowed: boolean
  matchedRule?: AccessRule
  reason: string
}

export function PhoneNumberTester({ rules, instanceNames }: PhoneNumberTesterProps) {
  const [phoneNumber, setPhoneNumber] = useState('')
  const [selectedInstance, setSelectedInstance] = useState<string>('')
  const [result, setResult] = useState<TestResult | null>(null)
  const [testing, setTesting] = useState(false)

  const testPhoneAccess = () => {
    setTesting(true)

    // Simulate a brief delay for better UX
    setTimeout(() => {
      // Filter rules by instance scope
      const applicableRules = rules.filter((rule) => {
        // Global rules always apply
        if (!rule.instance_name) return true
        // Instance-specific rules only apply if instance matches
        if (selectedInstance && rule.instance_name === selectedInstance) return true
        return false
      })

      // Check for exact match first
      const exactMatch = applicableRules.find((rule) => rule.phone_number === phoneNumber)
      if (exactMatch) {
        setResult({
          allowed: exactMatch.rule_type === 'allow',
          matchedRule: exactMatch,
          reason: `Exact match: ${exactMatch.rule_type} rule #${exactMatch.id}`,
        })
        setTesting(false)
        return
      }

      // Check for wildcard matches
      const wildcardMatch = applicableRules.find((rule) => {
        if (!rule.phone_number.endsWith('*')) return false
        const prefix = rule.phone_number.slice(0, -1)
        return phoneNumber.startsWith(prefix)
      })

      if (wildcardMatch) {
        setResult({
          allowed: wildcardMatch.rule_type === 'allow',
          matchedRule: wildcardMatch,
          reason: `Wildcard match: ${wildcardMatch.rule_type} rule #${wildcardMatch.id}`,
        })
        setTesting(false)
        return
      }

      // No match found - default behavior (typically allow)
      setResult({
        allowed: true,
        reason: 'No matching rule - default allow',
      })
      setTesting(false)
    }, 300)
  }

  const handleTest = () => {
    if (!phoneNumber.trim()) return
    testPhoneAccess()
  }

  return (
    <Card className="p-6 bg-zinc-800 border-zinc-600">
      <h3 className="text-xl font-bold mb-6 text-white">📱 Test Phone Number Access</h3>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="test-phone" className="text-white text-sm font-medium">
            Phone Number
          </Label>
          <Input
            id="test-phone"
            placeholder="+1234567890"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="bg-zinc-900 border-zinc-600 text-white placeholder:text-zinc-500"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="test-instance" className="text-white text-sm font-medium">
            Instance (Optional)
          </Label>
          <Select value={selectedInstance} onValueChange={setSelectedInstance}>
            <SelectTrigger className="bg-zinc-900 border-zinc-600 text-white">
              <SelectValue placeholder="Any instance" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Any instance</SelectItem>
              {instanceNames.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button onClick={handleTest} disabled={!phoneNumber.trim() || testing} className="w-full bg-blue-600 hover:bg-blue-700">
          {testing ? 'Testing...' : 'Test Access'}
        </Button>

        {result && (
          <div
            className={`p-4 rounded-md border ${
              result.allowed
                ? 'bg-green-900/20 border-green-500/50 text-green-300'
                : 'bg-red-900/20 border-red-500/50 text-red-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{result.allowed ? '✅' : '🔴'}</span>
              <span className="font-semibold text-lg">
                {result.allowed ? 'Allowed' : 'Blocked'}
              </span>
            </div>
            <p className="text-sm">{result.reason}</p>
            {result.matchedRule && (
              <div className="mt-2 pt-2 border-t border-current/20">
                <p className="text-xs opacity-75">
                  Rule: {result.matchedRule.phone_number}
                  {result.matchedRule.instance_name && ` (${result.matchedRule.instance_name})`}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
