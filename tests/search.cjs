// DOM contract checks for the shipped search UI; no npm dependencies.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { test } = require("node:test");
const source = fs.readFileSync(process.argv[2], "utf8");

function browser(options = {}) {
  const events = new Map();
  const timers = new Map();
  const document = {
    baseURI: options.base || "https://docs.example/project/api/python/item.html",
    activeElement: null,
    addEventListener: (name, fn) => events.set(name, fn),
  };
  class Element {
    constructor(tagName, id = "") {
      this.tagName = tagName.toUpperCase();
      this.id = id;
      this.dataset = {};
      this.events = new Map();
      this.children = [];
      this.attributes = {};
      this.textContent = "";
      this.hidden = true;
      this.value = "";
      this.open = false;
    }
    addEventListener(name, fn) { this.events.set(name, fn); }
    fire(name, event = {}) { this.events.get(name)?.(event); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this.attributes[name] = value; }
    focus() { document.activeElement = this; }
    select() { this.selected = true; }
    showModal() { this.open = true; }
    close() { this.open = false; this.fire("close"); }
    querySelectorAll(tagName) {
      return this.children.flatMap((child) => [
        ...(child.tagName === tagName.toUpperCase() ? [child] : []),
        ...child.querySelectorAll(tagName),
      ]);
    }
    set innerHTML(_) { throw new Error("Search must use text-only DOM writes"); }
  }
  const ids = Object.fromEntries([
    ["search-open", "button"], ["search-dialog", "dialog"],
    ["search-input", "input"], ["search-results", "ol"], ["search-status", "p"],
  ].map(([id, tag]) => [id, new Element(tag, id)]));
  ids["search-dialog"].dataset = { indexUrl: "../../search.json", limit: String(options.limit || 8), minLength: "2" };
  if (options.unsupported) ids["search-dialog"].showModal = undefined;
  document.getElementById = (id) => options.noControls ? null : ids[id];
  document.createElement = (tag) => new Element(tag);
  document.activeElement = ids["search-open"];
  const requests = [];
  const records = options.records || [
    { title: "Guide", url: "guide.html", text: "Intro with Compiler and arrow functions." },
    { title: "Compiler", url: "api/compiler.html", text: "Compile a module." },
    { title: "Compiler · Dispatch", url: "api/compiler.html#dispatch", text: "Dispatch variants." },
    { title: "Notebook", url: "tutorial/lesson.html#results", text: "Saved result includes café and arrays." },
  ];
  let response = options.response || { ok: true, json: async () => records };
  const context = {
    document, URL, Set,
    fetch: (url, args) => {
      requests.push({ url, args });
      return typeof response === "function" ? response() : Promise.resolve(response);
    },
    setTimeout: (fn) => { timers.set(fn, fn); return fn; },
    clearTimeout: (fn) => timers.delete(fn),
  };
  vm.runInNewContext(source, context);
  events.get("DOMContentLoaded")();
  const key = (value, target, modifiers = {}) => {
    const event = { key: value, target, preventDefault() { this.prevented = true; }, ...modifiers };
    events.get("keydown")?.(event);
    return event;
  };
  const tick = async () => {
    for (const [id, fn] of [...timers]) { timers.delete(id); fn(); }
    for (let i = 0; i < 12; i++) await Promise.resolve();
  };
  return {
    ids, document, requests, key, tick,
    open: () => ids["search-open"].fire("click"),
    close: () => ids["search-dialog"].close(),
    query: async (value) => { ids["search-input"].value = value; ids["search-input"].fire("input"); await tick(); },
    links: () => ids["search-results"].querySelectorAll("a"),
    status: () => ids["search-status"].textContent,
    respond: (value) => { response = value; },
  };
}

test("lazy loading, nested URLs, ranking, section deduplication, and cache", async () => {
  const b = browser();
  assert.equal(b.ids["search-open"].hidden, false);
  b.open();
  assert.equal(b.document.activeElement.id, "search-input");
  assert.equal(b.requests.length, 0);
  await b.query("compiler");
  assert.equal(b.requests[0].url, "https://docs.example/project/search.json");
  assert.equal(b.requests[0].args.credentials, "same-origin");
  assert.equal(b.links().length, 2);
  assert.equal(b.links()[0].textContent, "Compiler");
  assert.equal(b.links()[0].href, "https://docs.example/project/api/compiler.html");
  await b.query("dispatch");
  assert.equal(b.links()[0].href, "https://docs.example/project/api/compiler.html#dispatch");
  await b.query("ＣＡＦÉ");
  assert.equal(b.links()[0].textContent, "Notebook");
  assert.equal(b.requests.length, 1);
  await b.query("not present anywhere");
  assert.equal(b.status(), "No matches found.");
  await b.query(" ");
  assert.match(b.status(), /at least 2/);
});

test("shortcuts, arrow keys, dialog focus restoration, and editable exclusions", async () => {
  const b = browser();
  const event = b.key("/", b.ids["search-open"]);
  assert.equal(event.prevented, true);
  assert.equal(b.ids["search-dialog"].open, true);
  await b.query("compiler");
  const down = { key: "ArrowDown", preventDefault() {} };
  b.ids["search-dialog"].fire("keydown", down);
  assert.equal(b.document.activeElement, b.links()[0]);
  b.ids["search-dialog"].fire("keydown", { key: "ArrowUp", preventDefault() {} });
  assert.equal(b.document.activeElement, b.links()[1]);
  b.key("/", b.links()[1]);
  b.close();
  assert.equal(b.document.activeElement, b.ids["search-open"]);
  for (const target of [{ tagName: "INPUT" }, { tagName: "TEXTAREA" }, { isContentEditable: true }]) {
    assert.equal(b.key("/", target).prevented, undefined);
  }
  assert.equal(b.key("/", {}, { altKey: true }).prevented, undefined);
  assert.equal(b.key("/", {}, { ctrlKey: true }).prevented, undefined);
  assert.equal(b.key("k", {}, { ctrlKey: true }).prevented, true);
});

test("query changes and close events discard in-flight responses", async () => {
  let resolve;
  const b = browser({ response: () => new Promise((done) => { resolve = done; }) });
  b.open();
  await b.query("compiler");
  await b.query("other");
  resolve({ ok: true, json: async () => [{ title: "Other", url: "other.html", text: "Other" }] });
  await b.tick();
  assert.equal(b.links()[0].textContent, "Other");
  b.close();
  await b.query("compiler");
  assert.equal(b.links().length, 0);
});

test("failure messages and retry after a rejected fetch", async () => {
  const b = browser({ response: { ok: false } });
  b.open();
  await b.query("compiler");
  assert.match(b.status(), /unavailable/);
  assert.equal(b.ids["search-results"].attributes["aria-busy"], "false");
  b.close();
  b.respond({ ok: true, json: async () => [{ title: "Compiler", url: "guide.html", text: "Compile" }] });
  b.open();
  await b.tick();
  assert.equal(b.links().length, 1);
  assert.equal(b.requests.length, 2);
});

test("text-only results and rejection of invalid or escaping index records", async () => {
  const b = browser({ records: [{ title: '<img onerror="bad()">', url: "safe.html", text: "needle <script>bad()</script>" }] });
  b.open();
  await b.query("needle");
  assert.equal(b.links()[0].textContent, '<img onerror="bad()">');
  for (const url of ["javascript:bad()", "https://other.example/", "../outside.html", "/outside.html"]) {
    const unsafe = browser({ records: [{ title: "Needle", url, text: "needle" }] });
    unsafe.open();
    await unsafe.query("needle");
    assert.match(unsafe.status(), /unavailable/);
    assert.equal(unsafe.links().length, 0);
  }
  const invalid = browser({ response: { ok: true, json: async () => ({}) } });
  invalid.open();
  await invalid.query("needle");
  assert.match(invalid.status(), /unavailable/);
});

test("result limits and absent or unsupported controls", async () => {
  const b = browser({ limit: 1 });
  b.open();
  await b.query("compiler");
  assert.equal(b.links().length, 1);
  assert.equal(b.status(), "Showing 1 of 2 matching pages.");
  browser({ noControls: true });
  const unsupported = browser({ unsupported: true });
  assert.equal(unsupported.ids["search-open"].hidden, true);
});
