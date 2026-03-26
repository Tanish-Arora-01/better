import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Wallet,
  TrendingUp,
  Eye,
  EyeOff,
  RefreshCw,
  ArrowDown,
  Plus,
  Play,
  Loader2,
} from "lucide-react"

/**
 * Format paise → ₹ display string.
 * @param {number} paise
 */
const fmt = (paise) =>
  `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`

/**
 * @typedef {Object} Mandate
 * @property {string} id
 * @property {string} fund_name
 * @property {number} amount
 * @property {string} status  "ACTIVE" | "PAUSED" | "CANCELLED"
 */

/**
 * @typedef {Object} WalletCardProps
 * @property {Object} user               - { id, name, wallet_balance }
 * @property {Mandate[]} mandates        - list of SIP mandates
 * @property {Object} processing         - { [mandateId]: boolean }
 * @property {() => void} onRefresh
 * @property {(mandateId: string) => void} onProcessSIP
 * @property {() => void} onAddMandate
 * @property {boolean} refreshing
 */

/**
 * Shadcn-styled wallet dashboard card, powered by live SIP data.
 * @param {WalletCardProps} props
 */
export default function WalletCard({
  user,
  mandates,
  processing,
  onRefresh,
  onProcessSIP,
  onAddMandate,
  refreshing = false,
}) {
  const [balanceVisible, setBalanceVisible] = useState(true)

  const activeMandates = mandates.filter((m) => m.status === "ACTIVE")
  const totalCommitted = activeMandates.reduce((s, m) => s + m.amount, 0)
  const totalBalance = user.wallet_balance + totalCommitted

  const mask = "••••••"

  return (
    <div className="max-w-md mx-auto w-full">
      <Card className="p-6 bg-white border border-gray-200 shadow-xl rounded-3xl">
        <div className="space-y-6">

          {/* ── Account summary cards ───────────────────────────── */}
          <div className="space-y-3">
            <Card className="p-4 bg-gradient-to-r from-emerald-100 to-teal-100 border border-emerald-200/50 shadow-sm rounded-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-black/10 rounded-lg flex items-center justify-center">
                    <Wallet className="w-4 h-4 text-gray-700" />
                  </div>
                  <span className="font-medium text-gray-800">Wallet</span>
                </div>
                <span className="font-semibold text-gray-800">
                  {balanceVisible ? fmt(user.wallet_balance) : mask}
                </span>
              </div>
            </Card>

            <Card className="p-4 bg-gradient-to-r from-purple-100 to-indigo-100 border border-purple-200/50 shadow-sm rounded-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-black/10 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-gray-700" />
                  </div>
                  <span className="font-medium text-gray-800">
                    Active SIPs ({activeMandates.length})
                  </span>
                </div>
                <span className="font-semibold text-gray-800">
                  {balanceVisible ? fmt(totalCommitted) : mask}
                </span>
              </div>
            </Card>
          </div>

          {/* ── Total balance ──────────────────────────────────── */}
          <div className="space-y-4 py-6 px-4 border border-gray-100 rounded-2xl bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
                  <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                </div>
                <span className="text-gray-600 font-medium">Total Balance</span>
                <button
                  onClick={() => setBalanceVisible((v) => !v)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {balanceVisible ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <EyeOff className="w-4 h-4" />
                  )}
                </button>
              </div>
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="text-gray-400 hover:text-gray-600 transition-colors disabled:animate-spin"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-1">
              <div className="text-4xl font-bold text-gray-900">
                {balanceVisible ? fmt(totalBalance) : mask}
              </div>
              <div className="flex items-center gap-2 text-gray-500 text-sm">
                <span>
                  {user.name}{" "}
                  <span className="text-gray-400">
                    ({user.id.slice(0, 8)}…)
                  </span>
                </span>
              </div>
            </div>
          </div>

          {/* ── Action buttons ─────────────────────────────────── */}
          <div className="flex gap-3">
            <Button
              onClick={onAddMandate}
              className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl h-12 gap-2 border border-emerald-600"
            >
              <Plus className="w-4 h-4" />
              Add SIP
            </Button>
            <Button
              onClick={onRefresh}
              variant="secondary"
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-2xl h-12 gap-2 border border-gray-300"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
          </div>

          {/* ── Mandates list ──────────────────────────────────── */}
          <div className="space-y-1 pt-2">
            {mandates.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">
                No SIP mandates yet. Add one above ↑
              </p>
            ) : (
              mandates.map((m) => {
                const isActive = m.status === "ACTIVE"
                const isProcessing = processing[m.id]
                const statusColor = isActive
                  ? "text-emerald-600"
                  : m.status === "PAUSED"
                  ? "text-amber-500"
                  : "text-red-500"

                return (
                  <div
                    key={m.id}
                    className="flex items-center gap-4 p-3 border border-gray-100 rounded-2xl hover:bg-gray-50 transition-colors"
                  >
                    <div
                      className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${
                        isActive
                          ? "bg-emerald-50 border-emerald-200"
                          : "bg-gray-50 border-gray-200"
                      }`}
                    >
                      <TrendingUp
                        className={`w-6 h-6 ${
                          isActive ? "text-emerald-600" : "text-gray-400"
                        }`}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 truncate">
                        {m.fund_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {fmt(m.amount)}/instalment ·{" "}
                        <span className={`font-medium ${statusColor}`}>
                          {m.status}
                        </span>
                      </p>
                    </div>
                    {isActive && (
                      <Button
                        size="sm"
                        disabled={isProcessing}
                        onClick={() => onProcessSIP(m.id)}
                        className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl border border-emerald-600 gap-1.5"
                      >
                        {isProcessing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Play className="w-3.5 h-3.5" />
                        )}
                        {isProcessing ? "Processing…" : "Process"}
                      </Button>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
