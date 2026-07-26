document.querySelectorAll("[data-login-role]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector(".form-status");
    const data = Object.fromEntries(new FormData(form).entries());
    const remember = Boolean(data.remember);
    status.textContent = "Signing in...";
    try {
      const result = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: data.email, password: data.password, role: form.dataset.loginRole })
      });
      const store = remember ? localStorage : sessionStorage;
      store.setItem("token", result.access_token);
      store.setItem("role", result.role);
      store.setItem("name", result.full_name);
      location.href = "app.html";
    } catch (error) {
      status.textContent = error.message;
    }
  });
});
