import { useState, useEffect, useCallback } from 'react';
import {
  createUser,
  getUser,
  createMandate,
  listMandates,
  processSIP,
} from './api';

/* ── Tiny helpers ──────────────────────────────────────────────── */

/** Format paise → ₹ display */
const fmt = (paise) => `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

const FUND_OPTIONS = ['Nifty Bank Index', 'Nifty FMCG', 'Nifty IT', 'Nifty 50'];

/* ── Toast Component ───────────────────────────────────────────── */

function Toast({ toast, onClose }) {
  if (!toast) return null;
  const bg = toast.type === 'success'
    ? 'bg-success/15 border-success/40 text-success'
    : 'bg-danger/15 border-danger/40 text-danger';

  return (
    <div className={`fixed top-6 right-6 z-50 max-w-sm border rounded-xl px-5 py-4
                     shadow-2xl backdrop-blur-md animate-[slideIn_0.3s_ease-out] ${bg}`}>
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5">{toast.type === 'success' ? '✓' : '✕'}</span>
        <div className="flex-1">
          <p className="font-semibold text-sm">{toast.title}</p>
          <p className="text-xs mt-1 opacity-80">{toast.message}</p>
        </div>
        <button onClick={onClose} className="opacity-60 hover:opacity-100 text-lg leading-none">×</button>
      </div>
    </div>
  );
}

/* ── Dashboard ─────────────────────────────────────────────────── */

export default function Dashboard() {
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [mandates, setMandates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState({});  // mandateId → boolean
  const [toast, setToast] = useState(null);

  // New-mandate form
  const [newFund, setNewFund] = useState(FUND_OPTIONS[0]);
  const [newAmount, setNewAmount] = useState('');
  const [creating, setCreating] = useState(false);

  /* ── Show toast helper ──────────────────────────────────────── */
  const showToast = useCallback((type, title, message) => {
    setToast({ type, title, message });
    setTimeout(() => setToast(null), 4000);
  }, []);

  /* ── Bootstrap: create or load user ─────────────────────────── */
  useEffect(() => {
    const stored = localStorage.getItem('sip_user_id');
    if (stored) {
      setUserId(stored);
    } else {
      createUser('Demo User').then((u) => {
        localStorage.setItem('sip_user_id', u.id);
        setUserId(u.id);
      });
    }
  }, []);

  /* ── Refresh data ───────────────────────────────────────────── */
  const refresh = useCallback(async () => {
    if (!userId) return;
    const [u, m] = await Promise.all([getUser(userId), listMandates(userId)]);
    setUser(u);
    setMandates(m);
    setLoading(false);
  }, [userId]);

  useEffect(() => { refresh(); }, [refresh]);

  /* ── Create mandate ─────────────────────────────────────────── */
  const handleCreateMandate = async (e) => {
    e.preventDefault();
    const amt = parseInt(newAmount, 10);
    if (!amt || amt <= 0) {
      showToast('error', 'Invalid Amount', 'Amount must be a positive integer.');
      return;
    }
    setCreating(true);
    const { data, ok } = await createMandate(userId, newFund, amt);
    setCreating(false);
    if (ok) {
      showToast('success', 'Mandate Created', `${newFund} — ${fmt(amt)} per instalment`);
      setNewAmount('');
      refresh();
    } else {
      showToast('error', 'Creation Failed', data.error || JSON.stringify(data.details));
    }
  };

  /* ── Process SIP ────────────────────────────────────────────── */
  const handleProcessSIP = async (mandateId) => {
    setProcessing((p) => ({ ...p, [mandateId]: true }));
    const { data, status, ok } = await processSIP(mandateId);
    setProcessing((p) => ({ ...p, [mandateId]: false }));

    if (ok) {
      showToast(
        'success',
        'Instalment Processed',
        `Deducted ${fmt(data.amount)} — Txn ${data.id.slice(0, 8)}…`,
      );
    } else {
      showToast(
        'error',
        status === 400 ? 'Insufficient Balance' : 'Processing Failed',
        data.error || 'Unknown error',
      );
    }
    refresh();
  };

  /* ── Render ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-10 w-10 rounded-full border-4 border-accent/30 border-t-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 md:p-10 max-w-5xl mx-auto">
      <Toast toast={toast} onClose={() => setToast(null)} />

      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-primary">
          SIP Billing Engine
        </h1>
        <p className="text-text-secondary mt-1 text-sm">Idempotent • ACID-safe • Real-time</p>
      </header>

      {/* ── Wallet Card ─────────────────────────────────────────── */}
      <section className="mb-8 rounded-2xl bg-surface-card
                          border border-border p-6 shadow-sm shadow-slate-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-xl bg-accent/15 flex items-center justify-center">
            <svg className="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3" />
            </svg>
          </div>
          <div>
            <p className="text-text-muted text-xs uppercase tracking-widest">Wallet Balance</p>
            <p className="text-2xl font-bold text-text-primary">{fmt(user.wallet_balance)}</p>
          </div>
        </div>
        <p className="text-xs text-text-muted">User: {user.name} <span className="opacity-50">({user.id.slice(0, 8)}…)</span></p>
      </section>

      {/* ── New Mandate Form ────────────────────────────────────── */}
      <section className="mb-8 rounded-2xl bg-surface-card border border-border p-6">
        <h2 className="text-lg font-semibold mb-4 text-text-primary">Create SIP Mandate</h2>
        <form onSubmit={handleCreateMandate} className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Fund</label>
            <select
              value={newFund}
              onChange={(e) => setNewFund(e.target.value)}
              className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm
                         text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/50"
            >
              {FUND_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div className="w-40">
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Amount (paise)</label>
            <input
              type="number"
              min="1"
              value={newAmount}
              onChange={(e) => setNewAmount(e.target.value)}
              placeholder="5000"
              className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm
                         text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/50"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="rounded-lg bg-accent hover:bg-accent-hover px-5 py-2 text-sm font-semibold
                       text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {creating ? 'Creating…' : 'Add Mandate'}
          </button>
        </form>
      </section>

      {/* ── Mandates List ───────────────────────────────────────── */}
      <section className="rounded-2xl bg-surface-card border border-border p-6">
        <h2 className="text-lg font-semibold mb-4 text-text-primary">Active SIP Mandates</h2>

        {mandates.length === 0 ? (
          <p className="text-text-muted text-sm text-center py-8">
            No mandates yet. Create one above ↑
          </p>
        ) : (
          <div className="space-y-3">
            {mandates.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between gap-4 rounded-xl bg-surface
                           border border-border px-5 py-4 hover:border-accent/40 hover:shadow-sm transition-all"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-text-primary truncate">{m.fund_name}</p>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {fmt(m.amount)} per instalment ·{' '}
                    <span className={
                      m.status === 'ACTIVE' ? 'text-success font-medium' :
                      m.status === 'PAUSED' ? 'text-warning font-medium' :
                      'text-danger font-medium'
                    }>
                      {m.status}
                    </span>
                  </p>
                </div>

                {m.status === 'ACTIVE' && (
                  <button
                    onClick={() => handleProcessSIP(m.id)}
                    disabled={processing[m.id]}
                    className="shrink-0 rounded-lg bg-accent/10 border border-accent/20 text-accent hover:bg-accent hover:text-white
                               px-4 py-2 text-sm font-semibold transition-colors shadow-sm
                               disabled:opacity-50 disabled:cursor-not-allowed hover:disabled:bg-accent/10 hover:disabled:text-accent"
                  >
                    {processing[m.id] ? (
                      <span className="flex items-center gap-2">
                        <span className="h-3.5 w-3.5 rounded-full border-2 border-current
                                         border-t-transparent animate-spin" />
                        Processing…
                      </span>
                    ) : (
                      'Process Instalment'
                    )}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
