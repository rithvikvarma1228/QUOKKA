/* auth.js — shared helpers for all auth pages */

/* ── HTTP helpers ─────────────────────────────── */
async function postJson(url, data) {
  try {
    const res  = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {}),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch {
    return { ok: false, status: 0, json: { success: false, message: 'Network error. Please try again.' } };
  }
}

async function putJson(url, data) {
  try {
    const res  = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {}),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch {
    return { ok: false, status: 0, json: { success: false, message: 'Network error. Please try again.' } };
  }
}

/* ── Alert helpers ────────────────────────────── */
function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'alert error';
  el.textContent = msg;
}

function showSuccess(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'alert success';
  el.textContent = msg;
}

function clearAlert(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'alert';
  el.textContent = '';
}

/* ── Password visibility toggle ──────────────── */
function togglePw(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon  = document.getElementById(iconId);
  if (!input) return;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  if (icon) icon.className = show ? 'ph ph-eye-slash' : 'ph ph-eye';
}

/* ── Password strength ────────────────────────── */
function strengthScore(pw) {
  if (!pw || pw.length < 8) return 0;
  let s = 1;
  if (/\d/.test(pw)) s++;
  if (/[!@#$%^&*()_+\-=\[\]{}|;':",.<>?]/.test(pw)) s++;
  if (pw.length >= 12) s++;
  return Math.min(s, 3);
}

const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Strong'];
const STRENGTH_COLORS = ['', '#f87171', '#fbbf24', '#86efac'];

function updateStrength(pw, fillId, textId) {
  const fill = document.getElementById(fillId);
  const text = document.getElementById(textId);
  if (!fill) return;
  const s = strengthScore(pw);
  const pct = s === 0 ? '0%' : ['0%', '33%', '66%', '100%'][s];
  fill.style.width      = pct;
  fill.style.background = STRENGTH_COLORS[s] || 'transparent';
  if (text) {
    text.textContent  = s ? 'Strength: ' + STRENGTH_LABELS[s] : '';
    text.style.color  = STRENGTH_COLORS[s] || '';
  }
}

/* ── OTP input wiring ─────────────────────────── */
function setupOTP(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const inputs = [...container.querySelectorAll('input[data-otp]')];

  inputs.forEach((el, i) => {
    el.addEventListener('input', () => {
      el.value = el.value.replace(/\D/g, '').slice(-1);
      if (el.value && i < inputs.length - 1) inputs[i + 1].focus();
    });
    el.addEventListener('keydown', e => {
      if (e.key === 'Backspace' && !el.value && i > 0) {
        inputs[i - 1].value = '';
        inputs[i - 1].focus();
      }
    });
    el.addEventListener('paste', e => {
      e.preventDefault();
      const digits = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, inputs.length);
      digits.split('').forEach((d, j) => { if (inputs[j]) inputs[j].value = d; });
      inputs[Math.min(digits.length, inputs.length - 1)].focus();
    });
  });
}

function getOTP(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return '';
  return [...container.querySelectorAll('input[data-otp]')].map(el => el.value).join('');
}

/* ── Resend countdown ─────────────────────────── */
function startCountdown(btnId, secs = 60) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = true;
  let t = secs;
  btn.textContent = `Resend in ${t}s`;
  const iv = setInterval(() => {
    t--;
    if (t <= 0) {
      clearInterval(iv);
      btn.disabled = false;
      btn.textContent = 'Resend OTP';
    } else {
      btn.textContent = `Resend in ${t}s`;
    }
  }, 1000);
}

/* ── Button loading state ─────────────────────── */
function setLoading(btnId, spinnerId, loading) {
  const btn     = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  if (btn)     btn.disabled = loading;
  if (spinner) spinner.style.display = loading ? 'inline-block' : 'none';
}
