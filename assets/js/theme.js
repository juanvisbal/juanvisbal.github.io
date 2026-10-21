// Footer theme cycle: System → Light → Dark → System.
// The meta element is the current preference; tokens.css maps it to color-scheme.
// Only explicit light/dark choices are persisted. System removes the override.
(() => {
  const meta = document.querySelector('meta[name="color-scheme"]');
  const button = document.querySelector(".theme-toggle");
  if (!meta || !button) return;

  const systemDark = matchMedia("(prefers-color-scheme: dark)");
  const modes = ["system", "light", "dark"];
  const actions = {
    system: "Use system theme",
    light: "Switch to light theme",
    dark: "Switch to dark theme",
  };
  const preference = () => meta.content === "light" || meta.content === "dark" ? meta.content : "system";
  const nextMode = () => modes[(modes.indexOf(preference()) + 1) % modes.length];
  const render = () => {
    const current = preference();
    const name = current === "system" ? `System (${systemDark.matches ? "dark" : "light"})` : current === "light" ? "Light" : "Dark";
    const label = `Theme: ${name}. ${actions[nextMode()]}.`;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.hidden = false;
  };
  const apply = (value) => {
    meta.content = value === "light" || value === "dark" ? value : "light dark";
    render();
  };

  apply(meta.content);
  button.addEventListener("click", () => {
    const next = nextMode();
    try {
      if (next === "system") localStorage.removeItem("color-scheme");
      else localStorage.setItem("color-scheme", next);
    } catch { /* Theme still changes in this tab when storage is blocked. */ }
    apply(next);
  });

  // CSS follows OS changes automatically; update the System label as well.
  systemDark.addEventListener("change", render);
  addEventListener("storage", (e) => {
    if (e.key === "color-scheme" || e.key === null) apply(e.newValue);
  });
})();
