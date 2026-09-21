// Apply the saved preference before the page is painted.
(() => {
  const storageKey = "datapilot-theme";
  let savedTheme;
  try {
    savedTheme = localStorage.getItem(storageKey);
  } catch {
    // Storage can be unavailable in restricted browser sessions.
  }

  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  const initialTheme = ["light", "dark"].includes(savedTheme)
    ? savedTheme
    : (systemTheme.matches ? "dark" : "light");
  document.documentElement.dataset.theme = initialTheme;

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("theme-toggle");

    function updateToggle() {
      const isDark = document.documentElement.dataset.theme === "dark";
      toggle.textContent = isDark ? "Tema claro" : "Tema escuro";
      toggle.setAttribute("aria-pressed", String(isDark));
      toggle.setAttribute("aria-label", isDark ? "Ativar tema claro" : "Ativar tema escuro");
    }

    toggle.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = nextTheme;
      try {
        localStorage.setItem(storageKey, nextTheme);
      } catch {
        // Switching still works when persistence is unavailable.
      }
      updateToggle();
    });
    updateToggle();
  });
})();
