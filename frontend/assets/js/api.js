const API_BASE = localStorage.getItem("apiBase") || "http://localhost:8000/api";

function session() {
  return {
    token: localStorage.getItem("token") || sessionStorage.getItem("token"),
    role: localStorage.getItem("role") || sessionStorage.getItem("role"),
    name: localStorage.getItem("name") || sessionStorage.getItem("name")
  };
}

async function api(path, options = {}) {
  const current = session();
  const headers = options.headers || {};
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (current.token) headers.Authorization = `Bearer ${current.token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {}
    throw new Error(message);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.blob();
}
