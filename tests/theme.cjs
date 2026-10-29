// Exercise the distributed script using DOM events; no npm install required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(process.argv[2], "utf8");

function browser(options = {}) {
  const dataset = {
    colorMode: options.mode || "auto",
    preferenceKey: "doukimd:example:color-mode",
  };
  const media = new Map();
  const storage = new Map();
  if (options.stored !== undefined) storage.set(dataset.preferenceKey, options.stored);
  const picker = { hidden: true };
  const events = {};
  const select = {
    value: "",
    closest: () => picker,
    addEventListener: (name, fn) => { events[name] = fn; },
  };
  const navigation = { open: true };
  let ready;
  const context = {
    document: {
      documentElement: { dataset },
      getElementById: (id) => options.noControls ? null
        : (id === "color-mode" ? select : navigation),
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
    dataset, storage, navigation, select, picker,
    choose: (mode) => { select.value = mode; events.change(); },
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
console.log("Appearance and mobile navigation checks passed");
