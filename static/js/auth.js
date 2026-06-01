async function postJson(url, data) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch (e) {
    return {
      ok: false,
      status: 0,
      json: { success: false, message: "Network error. Please try again." },
    };
  }
}

async function putJson(url, data) {
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch (e) {
    return {
      ok: false,
      status: 0,
      json: { success: false, message: "Network error. Please try again." },
    };
  }
}

function togglePasswordVisibility(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (!input) return;
  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  if (icon) {
    icon.className = isPassword ? "ph ph-eye-slash" : "ph ph-eye";
  }
}

function checkPasswordStrength(password) {
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*]/.test(password);
  if (!password || password.length < 8) {
    return { score: 1, label: "Weak", color: "#ef4444" };
  }
  if (password.length >= 8 && hasNumber && hasSpecial) {
    return { score: 3, label: "Strong", color: "#22c55e" };
  }
  if (password.length >= 8 && hasNumber) {
    return { score: 2, label: "Medium", color: "#f59e0b" };
  }
  return { score: 1, label: "Weak", color: "#ef4444" };
}

function updateStrengthBar(password, barId, labelId) {
  const bar = document.getElementById(barId);
  const label = document.getElementById(labelId);
  if (!bar || !label) return;
  const s = checkPasswordStrength(password || "");
  label.textContent = s.label;
  label.style.color = s.color;

  const widths = { 1: "33%", 2: "66%", 3: "100%" };
  bar.style.width = widths[s.score] || "0%";
  bar.style.background = s.color;
}

function setupOTPInputs(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  const inputs = Array.from(container.querySelectorAll("input[data-otp]"));
  if (inputs.length === 0) return;

  const focusIndex = (i) => inputs[Math.max(0, Math.min(inputs.length - 1, i))].focus();

  inputs.forEach((input, idx) => {
    input.addEventListener("input", (e) => {
      const v = (e.target.value || "").replace(/\D/g, "");
      e.target.value = v.slice(-1);
      if (v && idx < inputs.length - 1) focusIndex(idx + 1);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !input.value && idx > 0) {
        inputs[idx - 1].value = "";
        focusIndex(idx - 1);
      }
    });

    input.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, inputs.length);
      if (!pasted) return;
      pasted.split("").forEach((ch, i) => {
        if (inputs[i]) inputs[i].value = ch;
      });
      focusIndex(Math.min(pasted.length, inputs.length - 1));
    });
  });
}

function startResendCountdown(buttonId, seconds = 60) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  btn.disabled = true;
  let remaining = seconds;
  const originalText = btn.dataset.originalText || btn.textContent;
  btn.dataset.originalText = originalText;

  btn.textContent = `Resend in ${remaining}s`;
  const timer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(timer);
      btn.disabled = false;
      btn.textContent = "Resend OTP";
      return;
    }
    btn.textContent = `Resend in ${remaining}s`;
  }, 1000);
}

function showError(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.style.display = "block";
}

function hideError(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.style.display = "none";
  el.textContent = "";
}

function showSuccess(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.style.display = "block";
}

