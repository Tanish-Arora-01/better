/**
 * API service for the SIP Billing Engine.
 * All calls go through the Vite proxy (/api → http://localhost:5000/api).
 */

const BASE = '/api';

/**
 * Create a new user.
 * @param {string} name
 * @returns {Promise<object>} User object
 */
export async function createUser(name) {
  const res = await fetch(`${BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  return res.json();
}

/**
 * Fetch user details (balance).
 * @param {string} userId
 * @returns {Promise<object>} User object
 */
export async function getUser(userId) {
  const res = await fetch(`${BASE}/users/${userId}`);
  return res.json();
}

/**
 * Create a new SIP mandate.
 * @param {string} userId
 * @param {string} fundName
 * @param {number} amount
 * @returns {Promise<object>} Mandate object
 */
export async function createMandate(userId, fundName, amount) {
  const res = await fetch(`${BASE}/mandates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, fund_name: fundName, amount }),
  });
  return { data: await res.json(), ok: res.ok };
}

/**
 * List all mandates for a user.
 * @param {string} userId
 * @returns {Promise<object[]>} Array of mandate objects
 */
export async function listMandates(userId) {
  const res = await fetch(`${BASE}/mandates/${userId}`);
  return res.json();
}

/**
 * Process a SIP instalment with a fresh Idempotency-Key.
 * @param {string} mandateId
 * @returns {Promise<{data: object, status: number}>}
 */
export async function processSIP(mandateId) {
  const idempotencyKey = crypto.randomUUID();
  const res = await fetch(`${BASE}/process-sip`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ mandate_id: mandateId }),
  });
  return { data: await res.json(), status: res.status, ok: res.ok };
}
