// Dependency-free regression tests: node --test tools/theme.test.cjs
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(path.join(__dirname, "../assets/js/theme.js"), "utf8");
const head = readFileSync(path.join(__dirname, "../layouts/_partials/site/theme-head.html"), "utf8").match(/<script>([\s\S]*?)<\/script>/)[1];

function setup({ dark = false, saved = null, blocked = false } = {}) {
  const storage = new Map(saved === null ? [] : [["color-scheme", saved]]);
  const meta = { content: "light dark" };
  const attributes = new Map();
  const clicks = {};
  const events = {};
  const media = { matches: dark, addEventListener: (type, fn) => { events[type] = fn; } };
  const button = {
    hidden: true,
    setAttribute: (name, value) => attributes.set(name, value),
    addEventListener: (type, fn) => { clicks[type] = fn; },
  };
  const context = vm.createContext({
    document: { querySelector: (selector) => selector === ".theme-toggle" ? button : meta },
    localStorage: {
      getItem(key) { if (blocked) throw new Error("Blocked"); return storage.get(key) ?? null; },
      setItem(key, value) { if (blocked) throw new Error("Blocked"); storage.set(key, value); },
      removeItem(key) { if (blocked) throw new Error("Blocked"); storage.delete(key); },
    },
    matchMedia: () => media,
    addEventListener: (type, fn) => { events[type] = fn; },
  });
  vm.runInContext(head, context); // The actual blocking startup script, before the footer JS.
  const initial = meta.content;
  vm.runInContext(source, context);
  return { meta, button, storage, attributes, initial, click: () => clicks.click(),
    changeOS(value) { media.matches = value; events.change(); },
    fromOtherTab(key, newValue) { events.storage({ key, newValue }); },
  };
}

for (const dark of [false, true]) {
  test(`System → Light → Dark → System (OS ${dark ? "dark" : "light"})`, () => {
    const t = setup({ dark });
    assert.equal(t.meta.content, "light dark");
    assert.equal(t.button.hidden, false);
    assert.match(t.attributes.get("aria-label"), /Theme: System/);
    t.click();
    assert.equal(t.meta.content, "light");
    assert.equal(t.storage.get("color-scheme"), "light");
    t.click();
    assert.equal(t.meta.content, "dark");
    assert.equal(t.storage.get("color-scheme"), "dark");
    assert.match(t.button.title, /Use system theme/);
    t.click();
    assert.equal(t.meta.content, "light dark");
    assert.equal(t.storage.has("color-scheme"), false);
  });
}

for (const saved of ["light", "dark"]) {
  test(`restores ${saved} before rendering and keeps it pinned across OS changes`, () => {
    const t = setup({ saved });
    assert.equal(t.initial, saved);
    for (const dark of [true, false]) {
      t.changeOS(dark);
      assert.equal(t.meta.content, saved);
      assert.equal(t.storage.get("color-scheme"), saved);
    }
  });
}

test("System reflects OS changes in its accessible name", () => {
  const t = setup();
  t.changeOS(true);
  assert.match(t.attributes.get("aria-label"), /System \(dark\)/);
  t.changeOS(false);
  assert.match(t.attributes.get("aria-label"), /System \(light\)/);
  assert.equal(t.storage.has("color-scheme"), false);
});

test("other tabs can set, reset, or clear theme preferences", () => {
  const t = setup();
  t.fromOtherTab("color-scheme", "dark");
  assert.equal(t.meta.content, "dark");
  t.fromOtherTab("unrelated", "light");
  assert.equal(t.meta.content, "dark");
  t.fromOtherTab("color-scheme", null);
  assert.equal(t.meta.content, "light dark");
  t.fromOtherTab("color-scheme", "light");
  t.fromOtherTab(null, null);
  assert.equal(t.meta.content, "light dark");
});

test("invalid saved preferences fall back to System before rendering", () => {
  for (const saved of ["system", "light dark", "invalid", ""]) {
    const t = setup({ saved });
    assert.equal(t.initial, "light dark");
    assert.equal(t.meta.content, "light dark");
  }
});

test("all three modes work in the current tab when storage is blocked", () => {
  const t = setup({ blocked: true });
  for (const mode of ["light", "dark", "light dark"]) {
    t.click();
    assert.equal(t.meta.content, mode);
  }
});
