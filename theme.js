/* DoukiMD appearance preferences. No framework JavaScript is required. */
(() => {
  "use strict";
  const root = document.documentElement;
  const modes = ["auto", "light", "dark"];
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const key = root.dataset.preferenceKey;
  let mode = root.dataset.colorMode;
  try {
    const stored = localStorage.getItem(key);
    if (modes.includes(stored)) mode = stored;
  } catch (_) {
    // Browsers may deny storage, including when viewing local files.
  }
  const apply = () => {
    root.dataset.bsTheme = mode === "auto"
      ? (system.matches ? "dark" : "light") : mode;
    root.dataset.colorMode = mode;
  };
  apply();
  system.addEventListener("change", () => {
    if (mode === "auto") apply();
  });
  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("color-mode");
    if (select) {
      select.value = mode;
      select.closest(".mode-picker").hidden = false;
      select.addEventListener("change", () => {
        if (!modes.includes(select.value)) return;
        mode = select.value;
        apply();
        try { localStorage.setItem(key, mode); } catch (_) { /* Optional. */ }
      });
    }
    const navigation = document.getElementById("docs-navigation");
    if (navigation) {
      const mobile = window.matchMedia("(max-width: 960px)");
      const resize = () => { navigation.open = !mobile.matches; };
      resize();
      mobile.addEventListener("change", resize);
    }
  });
})();
