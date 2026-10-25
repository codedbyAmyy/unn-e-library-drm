export const API_BASE = "http://127.0.0.1:8000";

const TOKEN_KEY = "unn_elibrary_token";

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function handleSessionExpired() {
  clearToken();

  // Prevent repeated redirects and redirect loops.
  if (window.location.pathname.endsWith('/login.html')) {
    return;
  }

  const returnTo =
    window.location.pathname +
    window.location.search +
    window.location.hash;

  const loginUrl = new URL('./login.html', window.location.href);
  loginUrl.searchParams.set('reason', 'expired');
  loginUrl.searchParams.set('next', returnTo);

  window.location.replace(loginUrl.href);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      "Cannot connect to the E-Library server. Check that FastAPI is running."
    );
  }

  if (response.status === 401 && token) {
    handleSessionExpired();
  }

  if (!response.ok) {
    let detail = "Something went wrong. Please try again.";

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        detail = data.detail;
      }
    } catch {
      // Keep the default error message.
    }

    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  return response.status === 204 ? null : response.json();
}
