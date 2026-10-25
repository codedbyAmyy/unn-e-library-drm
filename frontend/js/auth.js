import { apiRequest, getToken, saveToken, clearToken } from "./api.js";
export async function login(email, password) {
  const data = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!data?.access_token)
    throw new Error("Server did not return an access token.");
  saveToken(data.access_token);
  return data;
}
export function getCurrentUser() {
  return apiRequest("/auth/me");
}
export function logout() {
  clearToken();
  window.location.replace("./login.html");
}
export function requireLogin() {
  if (!getToken()) {
    window.location.replace("./login.html");
    return false;
  }
  return true;
}
