// Light/dark toggle (footer). Two states: follow the system, or the opposite of the system.
// The stored override lives in localStorage "color-scheme" and is mirrored to
// <meta name="color-scheme">, which tokens.css maps to the CSS color-scheme property.
(() => {
  const meta = document.querySelector('meta[name="color-scheme"]');
  const button = document.querySelector(".theme-toggle");
  if (!meta || !button) return;

  const systemDark = matchMedia("(prefers-color-scheme: dark)");
  const read = () => { try { return localStorage.getItem("color-scheme"); } catch { return null; } };
  const write = (value) => {
    try { value ? localStorage.setItem("color-scheme", value) : localStorage.removeItem("color-scheme"); } catch { /* not persisted */ }
    meta.content = value || "light dark";
  };

  button.hidden = false;
  button.addEventListener("click", () => {
    const system = systemDark.matches ? "dark" : "light";
    const rendered = read() || (meta.content === "light" || meta.content === "dark" ? meta.content : system);
    const target = rendered === "dark" ? "light" : "dark";
    // Matching the system means undoing the override: don't pin it.
    write(target === system ? null : target);
  });

  // Keep other open tabs in sync.
  addEventListener("storage", (e) => {
    if (e.key === "color-scheme") meta.content = e.newValue || "light dark";
  });
})();
