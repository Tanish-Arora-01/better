import { useState, useEffect, useCallback } from "react";
import WalletCard from "@/components/ui/wallet-card-2";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import Simulator from "./Simulator";
import {
  createUser,
  getUser,
  createMandate,
  listMandates,
  processSIP,
} from "./api";

const FUND_OPTIONS = ["Nifty Bank Index", "Nifty FMCG", "Nifty IT", "Nifty 50"];
const fmt = (paise) =>
  `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

/* ── Toast ──────────────────────────────────────────────────────── */
function Toast({ toast, onClose }) {
  if (!toast) return null;
  const colors =
    toast.type === "success"
      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
      : "bg-red-50 border-red-200 text-red-800";
  return (
    <div
      className={`fixed top-6 right-6 z-50 max-w-sm border rounded-xl px-5 py-4 shadow-lg ${colors}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5">
          {toast.type === "success" ? "✓" : "✕"}
        </span>
        <div className="flex-1">
          <p className="font-semibold text-sm">{toast.title}</p>
          <p className="text-xs mt-1 opacity-80">{toast.message}</p>
        </div>
        <button
          onClick={onClose}
          className="opacity-60 hover:opacity-100 text-lg leading-none"
        >
          ×
        </button>
      </div>
    </div>
  );
}

/* ── Add Mandate Modal ──────────────────────────────────────────── */
function AddMandateModal({ open, onClose, onSubmit, creating }) {
  const [fund, setFund] = useState(FUND_OPTIONS[0]);
  const [amount, setAmount] = useState("");

  if (!open) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const amt = parseInt(amount, 10);
    if (!amt || amt <= 0) return;
    onSubmit(fund, amt);
    setAmount("");
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <Card className="w-full max-w-sm mx-4 p-6 bg-white rounded-2xl shadow-2xl border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Create SIP Mandate
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">
              Fund
            </label>
            <select
              value={fund}
              onChange={(e) => setFund(e.target.value)}
              className="w-full rounded-xl bg-gray-50 border border-gray-200 px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-200"
            >
              {FUND_OPTIONS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">
              Amount (paise)
            </label>
            <input
              type="number"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="5000"
              className="w-full rounded-xl bg-gray-50 border border-gray-200 px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-200"
            />
          </div>
          <Button
            type="submit"
            disabled={creating}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl h-11 border border-emerald-600"
          >
            {creating ? "Creating…" : "Add Mandate"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

/* ── Tab Bar ────────────────────────────────────────────────────── */
function TabBar({ activeTab, onTabChange }) {
  const tabs = [
    { id: "app", label: "Live Application" },
    { id: "simulator", label: "Architecture Visualizer" },
  ];
  return (
    <div className="fixed top-0 left-0 right-0 z-30 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-5xl mx-auto flex">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 py-3.5 text-sm font-semibold tracking-wide transition-all duration-200 ${
              activeTab === tab.id
                ? "text-gray-900 border-b-2 border-emerald-500 bg-gray-50"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Main App ───────────────────────────────────────────────────── */
export default function App() {
  const [activeTab, setActiveTab] = useState("app");
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [mandates, setMandates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [processing, setProcessing] = useState({});
  const [toast, setToast] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  /* ── Toast helper ──────────────────────────────────────────── */
  const showToast = useCallback((type, title, message) => {
    setToast({ type, title, message });
    setTimeout(() => setToast(null), 4000);
  }, []);

  /* ── Bootstrap ─────────────────────────────────────────────── */
  useEffect(() => {
    const stored = localStorage.getItem("sip_user_id");
    if (stored) {
      setUserId(stored);
    } else {
      createUser("Demo User").then((u) => {
        localStorage.setItem("sip_user_id", u.id);
        setUserId(u.id);
      });
    }
  }, []);

  /* ── Refresh ───────────────────────────────────────────────── */
  const refresh = useCallback(async () => {
    if (!userId) return;
    setRefreshing(true);
    const [u, m] = await Promise.all([getUser(userId), listMandates(userId)]);
    setUser(u);
    setMandates(m);
    setLoading(false);
    setRefreshing(false);
  }, [userId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  /* ── Create mandate ────────────────────────────────────────── */
  const handleCreateMandate = async (fund, amount) => {
    setCreating(true);
    const { data, ok } = await createMandate(userId, fund, amount);
    setCreating(false);
    if (ok) {
      showToast(
        "success",
        "Mandate Created",
        `${fund} — ${fmt(amount)} per instalment`
      );
      setModalOpen(false);
      refresh();
    } else {
      showToast(
        "error",
        "Creation Failed",
        data.error || JSON.stringify(data.details)
      );
    }
  };

  /* ── Process SIP (crypto.randomUUID() for idempotency) ───── */
  const handleProcessSIP = async (mandateId) => {
    setProcessing((p) => ({ ...p, [mandateId]: true }));
    const { data, status, ok } = await processSIP(mandateId);
    setProcessing((p) => ({ ...p, [mandateId]: false }));

    if (ok) {
      showToast(
        "success",
        "Instalment Processed",
        `Deducted ${fmt(data.amount)} — Txn ${data.id.slice(0, 8)}…`
      );
    } else {
      showToast(
        "error",
        status === 400 ? "Insufficient Balance" : "Processing Failed",
        data.error || "Unknown error"
      );
    }
    refresh();
  };

  /* ── Render ────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-gray-50">
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <Toast toast={toast} onClose={() => setToast(null)} />

      <div className="pt-[52px]">
        {activeTab === "app" ? (
          loading ? (
            <div className="min-h-screen flex items-center justify-center">
              <div className="h-10 w-10 rounded-full border-4 border-emerald-200 border-t-emerald-500 animate-spin" />
            </div>
          ) : (
            <>
              <AddMandateModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                onSubmit={handleCreateMandate}
                creating={creating}
              />
              <div className="w-full min-h-[calc(100vh-52px)] flex items-center justify-center p-4 relative">
                <WalletCard
                  user={user}
                  mandates={mandates}
                  processing={processing}
                  refreshing={refreshing}
                  onRefresh={refresh}
                  onProcessSIP={handleProcessSIP}
                  onAddMandate={() => setModalOpen(true)}
                />
                <div
                  className="absolute w-full h-full -z-10"
                  style={{
                    backgroundImage:
                      "url('data:image/svg+xml,%3Csvg width=\"4\" height=\"4\" viewBox=\"0 0 6 6\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Ccircle cx=\"3\" cy=\"3\" r=\"1\" fill=\"%23ccc\" fill-opacity=\"0.3\" /%3E%3C/svg%3E')",
                  }}
                ></div>
              </div>
            </>
          )
        ) : (
          <Simulator />
        )}
      </div>
    </div>
  );
}
