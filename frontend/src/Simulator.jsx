import React, { useState } from 'react';

const Simulator = () => {
  const [balance, setBalance] = useState(10000);
  const [transactions, setTransactions] = useState([]);
  const [activeStep, setActiveStep] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [alert, setAlert] = useState(null);

  const steps = [
    { id: 'frontend', label: '1. React Frontend (Generates Key)' },
    { id: 'api', label: '2. Flask API (/process-sip)' },
    { id: 'idempotency', label: '3. Idempotency Check (DB Query)' },
    { id: 'lock', label: '4. DB Row Lock (with_for_update)' },
    { id: 'fsm', label: '5. Check Balance & Deduct (FSM)' },
    { id: 'commit', label: '6. DB Commit / Save' },
  ];

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const runSimulation = async (type) => {
    if (isAnimating) return;
    setIsAnimating(true);
    setAlert(null);

    setActiveStep('frontend');
    await sleep(800);
    setActiveStep('api');
    await sleep(800);

    setActiveStep('idempotency');
    await sleep(1000);

    if (type === 'double_click') {
      setAlert({ type: 'warning', msg: 'Duplicate Key Found! Returning 200 OK. No money deducted.' });
      
      // THE FIX: Grab the ID of the last transaction to prove it's the exact same request
      const duplicateId = transactions.length > 0 ? transactions[0].id : crypto.randomUUID().slice(0,8);
      
      setTransactions([{ id: duplicateId, status: 'BLOCKED (Duplicate)', amount: 0 }, ...transactions]);
      setActiveStep(null);
      setIsAnimating(false);
      return;
    }

    setActiveStep('lock');
    await sleep(800);

    setActiveStep('fsm');
    await sleep(1000);

    if (type === 'empty_wallet' || balance < 500) {
      setAlert({ type: 'error', msg: 'Insufficient Funds! Rolling back transaction.' });
      setTransactions([{ id: crypto.randomUUID().slice(0, 8), status: 'FAILED', amount: 0 }, ...transactions]);
      setActiveStep(null);
      setIsAnimating(false);
      return;
    }

    setBalance((prev) => prev - 500);
    setActiveStep('commit');
    await sleep(800);

    setAlert({ type: 'success', msg: 'Transaction Completed Successfully!' });
    setTransactions([{ id: crypto.randomUUID().slice(0, 8), status: 'COMPLETED', amount: 500 }, ...transactions]);

    await sleep(1000);
    setActiveStep(null);
    setIsAnimating(false);
  };

  return (
    <div className="flex flex-col md:flex-row gap-8 p-8 bg-gray-50 text-gray-900 min-h-screen font-sans">
      {/* Left Panel: Client App */}
      <div className="flex-1 space-y-6">
        <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 text-gray-800">Client App</h2>

        <div className="p-6 bg-white rounded-2xl shadow-sm border border-gray-200">
          <p className="text-gray-500 uppercase tracking-wider text-xs font-medium">Wallet Balance</p>
          <p className="text-4xl font-mono mt-2 text-gray-900">₹{balance.toLocaleString()}</p>
        </div>

        <div className="space-y-3">
          <button
            disabled={isAnimating}
            onClick={() => runSimulation('normal')}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-white disabled:opacity-50 py-3 rounded-xl font-semibold transition shadow-sm border border-emerald-600"
          >
            Process Normal Payment (₹500)
          </button>
          <button
            disabled={isAnimating}
            onClick={() => runSimulation('double_click')}
            className="w-full bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50 py-3 rounded-xl font-semibold transition shadow-sm border border-amber-600"
          >
            Simulate Double Click (Network Lag)
          </button>
          <button
            disabled={isAnimating}
            onClick={() => { setBalance(0); runSimulation('empty_wallet'); }}
            className="w-full bg-red-500 hover:bg-red-600 text-white disabled:opacity-50 py-3 rounded-xl font-semibold transition shadow-sm border border-red-600"
          >
            Simulate Empty Wallet (₹0)
          </button>
        </div>

        {/* Transaction Log */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-3 text-gray-800">Transaction Log</h3>
          <div className="space-y-2">
            {transactions.map((txn, idx) => (
              <div key={idx} className="p-3 bg-white border border-gray-200 rounded-xl flex justify-between font-mono text-sm shadow-sm">
                <span className="text-gray-700">{txn.id}</span>
                <span className={
                  txn.status === 'COMPLETED' ? 'text-emerald-600 font-semibold' :
                  txn.status === 'FAILED' ? 'text-red-500 font-semibold' : 'text-amber-500 font-semibold'
                }>{txn.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel: Backend Engine */}
      <div className="flex-1 bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
        <h2 className="text-2xl font-bold border-b border-gray-200 pb-2 mb-6 text-gray-800">Backend Engine</h2>

        {alert && (
          <div className={`p-4 mb-6 rounded-xl font-semibold text-sm ${
            alert.type === 'warning' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
            alert.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
            'bg-emerald-50 text-emerald-800 border border-emerald-200'
          }`}>
            {alert.msg}
          </div>
        )}

        <div className="space-y-4 relative">
          {/* Connector Line */}
          <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-gray-200 z-0"></div>

          {steps.map((step) => (
            <div
              key={step.id}
              className={`relative z-10 flex items-center p-4 rounded-xl border transition-all duration-300 ${
                activeStep === step.id
                  ? 'bg-emerald-50 border-emerald-300 scale-[1.02] shadow-md shadow-emerald-100'
                  : 'bg-gray-50 border-gray-200 opacity-70'
              }`}
            >
              <div className={`w-4 h-4 rounded-full mr-4 ${
                activeStep === step.id ? 'bg-emerald-500' : 'bg-gray-300'
              }`}></div>
              <span className="font-mono text-sm text-gray-700">{step.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Simulator;
