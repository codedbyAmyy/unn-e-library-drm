import { apiRequest, clearToken, getToken } from "./api.js";
import { login, getCurrentUser } from "./auth.js";

const $ = (id) => document.getElementById(id);
const status = $("form-status");

const loginParams = new URLSearchParams(window.location.search);

if (loginParams.get('reason') === 'expired') {
  status.textContent =
    'Your session has expired. Please sign in again.';
}

const signIn = $("sign-in-tab"),
  register = $("register-tab");

function mode(name) {
  const isRegister = name === "register";
  $("login-form").hidden = isRegister;
  $("register-form").hidden = !isRegister;
  signIn.setAttribute("aria-selected", String(!isRegister));
  register.setAttribute("aria-selected", String(isRegister));
  $("form-title").textContent = isRegister
    ? "Create your UNN account"
    : "Welcome back";
  $("form-subtitle").textContent = isRegister
    ? "Register as a student or lecturer to access the library."
    : "Sign in to continue to your academic workspace.";
  status.textContent = "";
  location.hash = isRegister ? "register" : "login";
}
signIn.onclick = () => mode("login");
register.onclick = () => mode("register");
mode(location.hash === "#register" ? "register" : "login");
$("register-role").onchange = () => {
  const student = $("register-role").value === "student";
  $("student-fields").hidden = !student;
  $("lecturer-fields").hidden = student;
  $("register-matric").required = student;
  $("register-level").required = student;
  $("register-staff").required = !student;
};
$("register-role").onchange();
function setBusy(id, busy, text) {
  const btn = $(id);
  btn.disabled = busy;
  btn.textContent = busy ? "Please wait…" : text;
}
$("login-form").onsubmit = async (e) => {
  e.preventDefault();
  setBusy("login-submit", true, "Sign in →");
  status.textContent = "";
  try {
    await login($("login-email").value.trim(), $("login-password").value);
    await getCurrentUser();
    location.replace("./index.html");
  } catch (err) {
    clearToken();
    status.textContent = err.message;
  } finally {
    setBusy("login-submit", false, "Sign in →");
  }
};
$("register-form").onsubmit = async (e) => {
  e.preventDefault();
  status.textContent = "";
  if ($("register-password").value !== $("register-confirm").value) {
    status.textContent = "Passwords do not match.";
    return;
  }
  const student = $("register-role").value === "student";
  const payload = {
    full_name: $("register-name").value.trim(),
    email: $("register-email").value.trim(),
    password: $("register-password").value,
    role: student ? "student" : "lecturer",
    department_id: Number($("register-department").value),
  };
  if (student) {
    payload.matric_number = $("register-matric").value.trim();
    payload.academic_level = $("register-level").value;
  } else payload.staff_id = $("register-staff").value.trim();
  setBusy("register-submit", true, "Create account →");
  try {
    await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    status.textContent = "Account created. Please sign in.";
    mode("login");
    status.textContent =
      "Account created successfully. Sign in with your new credentials.";
    $("login-email").value = payload.email;
  } catch (err) {
    status.textContent = `Registration failed: ${err.message}`;
  } finally {
    setBusy("register-submit", false, "Create account →");
  }
};
if (getToken())
  getCurrentUser()
    .then(() => location.replace("./index.html"))
    .catch(() => clearToken());

// Show or hide passwords without changing their values or form submission.
for (const field of document.querySelectorAll('input[type="password"]')) {
  const wrap = document.createElement("div");
  wrap.className = "password-wrap";
  field.parentNode.insertBefore(wrap, field);
  wrap.append(field);
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "password-eye";
  toggle.textContent = "Show";
  toggle.setAttribute("aria-label", "Show password");
  toggle.addEventListener("click", () => {
    const show = field.type === "password";
    field.type = show ? "text" : "password";
    toggle.textContent = show ? "Hide" : "Show";
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
  wrap.append(toggle);
}
