// Exercise the distributed script using DOM events; no npm install required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(process.argv[2], "utf8");

function browser(options = {}) {
  const dataset = {
    colorMode: options.mode || "auto",
    preferenceKey: "doukimd:example:color-mode",
    palette: options.palette || "terracotta",
    palettes: "terracotta,ocean,forest,violet,slate",
  };
  const media = new Map();
  const storage = new Map();
  if (options.stored !== undefined) storage.set(dataset.preferenceKey, options.stored);
  if (options.storedPalette !== undefined) {
    storage.set(dataset.preferenceKey + ":palette", options.storedPalette);
  }
  const picker = { hidden: true };
  const events = {};
  const select = {
    value: "",
    closest: () => picker,
    addEventListener: (name, fn) => { events[name] = fn; },
  };
  const palettePicker = { hidden: true };
  const paletteEvents = {};
  const paletteSelect = {
    value: "",
    closest: () => palettePicker,
    addEventListener: (name, fn) => { paletteEvents[name] = fn; },
  };
  const navigation = { open: true };
  let ready;
  const context = {
    document: {
      documentElement: { dataset },
      getElementById: (id) => options.noControls ? null : ({
        "color-mode": select, "color-palette": paletteSelect,
        "docs-navigation": navigation,
      }[id] || null),
      addEventListener: (name, fn) => { ready = fn; },
    },
    localStorage: {
      getItem: (key) => {
        if (options.blockStorage) throw new Error("Storage denied");
        return storage.get(key) || null;
      },
      setItem: (key, value) => {
        if (options.blockStorage) throw new Error("Storage denied");
        storage.set(key, value);
      },
    },
    window: {
      matchMedia: (query) => {
        const value = {
          matches: query.includes("color-scheme") ? !!options.dark : !!options.mobile,
          addEventListener: (name, fn) => { value.change = fn; },
        };
        media.set(query, value);
        return value;
      },
    },
  };
  vm.runInNewContext(source, context);
  ready();
  return {
    dataset, storage, navigation, select, picker, paletteSelect, palettePicker,
    choose: (mode) => { select.value = mode; events.change(); },
    choosePalette: (name) => {
      paletteSelect.value = name;
      paletteEvents.change();
    },
    system: (dark) => {
      const value = media.get("(prefers-color-scheme: dark)");
      value.matches = dark;
      value.change();
    },
    resize: (mobile) => {
      const value = media.get("(max-width: 960px)");
      value.matches = mobile;
      value.change();
    },
  };
}

const auto = browser({ dark: true });
assert.equal(auto.dataset.bsTheme, "dark");
assert.equal(auto.select.value, "auto");
assert.equal(auto.picker.hidden, false);
auto.system(false);
assert.equal(auto.dataset.bsTheme, "light");
auto.choose("dark");
auto.system(false);
assert.equal(auto.dataset.bsTheme, "dark");
assert.equal(auto.storage.get("doukimd:example:color-mode"), "dark");
auto.choose("light");
assert.equal(auto.dataset.bsTheme, "light");
auto.choose("auto");
auto.system(true);
assert.equal(auto.dataset.bsTheme, "dark");

const stored = browser({ mode: "light", stored: "dark" });
assert.equal(stored.dataset.bsTheme, "dark");
assert.equal(stored.select.value, "dark");
const invalid = browser({ mode: "light", stored: "invalid", dark: true });
assert.equal(invalid.dataset.bsTheme, "light");
invalid.choose("invalid");
assert.equal(invalid.dataset.bsTheme, "light");

const blocked = browser({ blockStorage: true, dark: true });
assert.equal(blocked.dataset.bsTheme, "dark");
blocked.choose("light");
assert.equal(blocked.dataset.bsTheme, "light");
assert.equal(browser({ noControls: true, dark: true }).dataset.bsTheme, "dark");
const mobile = browser({ mobile: true });
assert.equal(mobile.navigation.open, false);
mobile.resize(false);
assert.equal(mobile.navigation.open, true);
mobile.resize(true);
assert.equal(mobile.navigation.open, false);

for (const name of ["terracotta", "ocean", "forest", "violet", "slate"]) {
  const page = browser({ palette: name, dark: true });
  assert.equal(page.dataset.palette, name);
  assert.equal(page.paletteSelect.value, name);
  assert.equal(page.palettePicker.hidden, false);
  assert.equal(page.dataset.bsTheme, "dark");
  page.choosePalette("ocean");
  assert.equal(page.dataset.bsTheme, "dark");
  page.choose("light");
  assert.equal(page.dataset.palette, "ocean");
  page.choosePalette("forest");
  assert.equal(page.storage.get("doukimd:example:color-mode:palette"), "forest");
  assert.equal(page.storage.get("doukimd:example:color-mode"), "light");
  page.choose("auto");
  page.system(false);
  assert.equal(page.dataset.palette, "forest");
}
const reloaded = browser({ palette: "terracotta", storedPalette: "violet" });
assert.equal(reloaded.dataset.palette, "violet");
assert.equal(reloaded.paletteSelect.value, "violet");
const invalidPalette = browser({ palette: "slate", storedPalette: "unknown" });
assert.equal(invalidPalette.dataset.palette, "slate");
invalidPalette.choosePalette("unknown");
assert.equal(invalidPalette.dataset.palette, "slate");
blocked.choosePalette("violet");
assert.equal(blocked.dataset.palette, "violet");
console.log("Appearance, palette, and mobile navigation checks passed");
