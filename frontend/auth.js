const form = document.getElementById("auth-form");
const toggle = document.getElementById("toggle-form");
const title = document.getElementById("form-title");
const submitBtn = document.getElementById("submit-btn");
const registerFields = document.getElementById("register-fields");
const errorMessage = document.getElementById("error-message");

let isRegister = false;

toggle.addEventListener("click", (e) => {
  e.preventDefault();
  isRegister = !isRegister;
  if (isRegister) {
    title.textContent = "Register";
    submitBtn.textContent = "Register";
    registerFields.style.display = "block";
    toggle.textContent = "Already have an account? Login here";
  } else {
    title.textContent = "Login";
    submitBtn.textContent = "Login";
    registerFields.style.display = "none";
    toggle.textContent = "Don't have an account? Register here";
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  let payload = { username, password };

  if (isRegister) {
    payload.ingame_username = document.getElementById("ingame_username").value;
    payload.company_code = document.getElementById("company_code").value;
  }

  const endpoint = isRegister ? "/api/register" : "/api/login";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Request failed");

    // Store token & redirect
    localStorage.setItem("token", data.token);
    if (data.role === "admin") {
      window.location.href = "/admin/index.html";
    } else {
      window.location.href = "/app/dashboard/index.html";
    }

  } catch (err) {
    errorMessage.textContent = err.message;
  }
});
