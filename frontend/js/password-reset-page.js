import { apiRequest } from "./api.js";

const $ = (id) => document.getElementById(id);
const token = new URLSearchParams(location.search).get("token");
const requestForm = $("reset-request-form");
const changeForm = $("reset-change-form");
const status = $("reset-message");
const title = $("reset-title");
const subtitle = $("reset-subtitle");

if (token) {
  requestForm.hidden = true;
  changeForm.hidden = false;
  title.textContent = "Create a new password";
  subtitle.textContent = "Choose a strong new password to recover your account.";
  // Prevent the token remaining in the browser history / Referer URL.
  history.replaceState(null, "", location.pathname);
}

function setFeedback(message, error = false) {
  status.textContent = message;
  status.classList.toggle("reset-error", error);
}

requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = requestForm.querySelector('button[type="submit"]');
  button.disabled = true;
  setFeedback("Submitting your request…");
  try {
    const response = await apiRequest("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: $("reset-email").value.trim() }),
    });
    setFeedback(response.message);
  } catch (err) {
    setFeedback(err.message || "Could not submit the request.", true);
  } finally {
    button.disabled = false;
  }
});

changeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = $("reset-new-password").value;
  if (password !== $("reset-confirm-password").value) {
    setFeedback("Passwords do not match.", true);
    return;
  }
  const button = changeForm.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const response = await apiRequest("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: password }),
    });
    changeForm.hidden = true;
    setFeedback(response.message);
  } catch (err) {
    setFeedback(err.message || "Could not reset your password.", true);
  } finally {
    button.disabled = false;
  }
});
