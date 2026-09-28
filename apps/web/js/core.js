/* ==========================================================================
   Great Church AI — core
   Shared utilities: DOM helpers, API client, AI bridge, nav, toasts.
   No framework, no build step.
   ========================================================================== */

(() => {
  "use strict";

  /* --- DOM ------------------------------------------------------------- */
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) =>
    Array.from(scope.querySelectorAll(selector));

  const el = (tag, props = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "html") node.innerHTML = value;
      else if (key.startsWith("on") && typeof value === "function") {
        node.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (value !== null && value !== undefined && value !== false) {
        node.setAttribute(key, value === true ? "" : String(value));
      }
    }
    for (const child of [].concat(children)) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
    return node;
  };

  /* Never build HTML from model or user text. Use textContent. */
  const escapeHtml = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (ch) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[ch]
    );

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Clipboard API needs a secure context; fall back to a temporary node.
      try {
        const scratch = el("textarea", { value: text, "aria-hidden": "true" });
        scratch.style.position = "fixed";
        scratch.style.opacity = "0";
        document.body.append(scratch);
        scratch.select();
        const ok = document.execCommand("copy");
        scratch.remove();
        return ok;
      } catch {
        return false;
      }
    }
  };

  /* --- API client ------------------------------------------------------- */
  class ApiError extends Error {
    constructor(message, { status, code, retryAfter, payload } = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status ?? 0;
      this.code = code ?? "unknown";
      this.retryAfter = retryAfter ?? null;
      this.payload = payload ?? null;
    }
  }

  const readErrorMessage = (payload, status) => {
    if (payload && payload.error) {
      if (typeof payload.error === "string") return payload.error;
      if (typeof payload.error.message === "string") return payload.error.message;
    }
    if (status === 404) return "We could not find what you were looking for.";
    if (status >= 500) return "Something went wrong while preparing your response. Please try again.";
    return "That request could not be completed. Please try again.";
  };

  const request = async (path, options = {}) => {
    const { method = "GET", body, signal } = options;

    let response;
    try {
      response = await fetch(path, {
        method,
        signal,
        headers: {
          Accept: "application/json",
          ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      if (error && error.name === "AbortError") throw error;
      throw new ApiError(
        "We could not reach Great Church AI. Check your connection and try again.",
        { status: 0, code: "network" }
      );
    }

    let payload = null;
    const type = response.headers.get("Content-Type") || "";
    if (type.includes("application/json")) {
      payload = await response.json().catch(() => null);
    }

    if (!response.ok) {
      const retryAfterHeader = response.headers.get("Retry-After");
      const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : null;
      throw new ApiError(readErrorMessage(payload, response.status), {
        status: response.status,
        code: payload?.error?.code ?? `http_${response.status}`,
        retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
        payload,
      });
    }

    return payload;
  };

  const api = {
    request,
    ApiError,
    health: () => request("/api/health"),
    starterPrompts: () => request("/api/ai/starters"),
    prepareChat: (message, history = [], reference = null) =>
      request("/api/ai/chat", {
        method: "POST",
        body: { message, history, reference: reference || null },
      }),
    prepareStudy: (reference, action, includeScripture = true) =>
      request("/api/ai/study", {
        method: "POST",
        body: {
          reference,
          action,
          include_scripture: includeScripture,
        },
      }),
    preparePrayer: (topic, detail = null) =>
      request("/api/ai/prayer-prompt", { method: "POST", body: { topic, detail } }),
    prayerDraft: (situation, reference = null) =>
      request("/api/ai/prayer-draft", {
        method: "POST",
        body: { situation, reference: reference || null },
      }),
    books: () => request("/api/bible/books"),
    passage: (reference) =>
      request(`/api/bible/reference?reference=${encodeURIComponent(reference)}`),
    book: (book, chapter) =>
      request(
        `/api/bible/book?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapter)}`
      ),
    searchBible: (query, limit = 20) =>
      request(`/api/bible/search?q=${encodeURIComponent(query)}&limit=${limit}`),
    verseOfTheDay: () => request("/api/bible/verse-of-the-day"),
    prayerTopics: () => request("/api/prayer/topics"),
    generatePrayer: (body) => request("/api/prayer", { method: "POST", body }),
    sermons: () => request("/api/sermons"),
    sermon: (id) => request(`/api/sermons/${encodeURIComponent(id)}`),
    outlineSermon: (body) => request("/api/sermons/outline", { method: "POST", body }),
  };

  /* --- AI bridge (Puter.js) -------------------------------------------- */
  /* Great Church AI ships no server-side model key. The browser calls Puter,
     which uses the visitor's own session, so there is nothing to leak.
     If Puter is missing or refuses, callers get null and must show a
     graceful, honest fallback rather than a fake answer. */
  const ai = {
    isReady() {
      return (
        typeof window.puter !== "undefined" &&
        typeof window.puter?.ai?.chat === "function"
      );
    },

    isSignedIn() {
      try {
        return typeof window.puter?.auth?.isSignedIn === "function"
          ? window.puter.auth.isSignedIn()
          : null;
      } catch {
        return null;
      }
    },

    async run({ system, messages, model }) {
      if (!this.isReady()) {
        return { ok: false, reason: "unavailable" };
      }

      const payload = [
        { role: "system", content: system },
        ...messages.map((m) => ({ role: m.role, content: m.content })),
      ];

      try {
        const raw = await window.puter.ai.chat(payload, {
          model: model || "gpt-4o-mini",
        });
        const text =
          typeof raw === "string"
            ? raw
            : raw?.message?.content || raw?.text || raw?.choices?.[0]?.message?.content || "";
        const clean = String(text).trim();
        if (!clean) return { ok: false, reason: "empty" };
        return { ok: true, text: clean };
      } catch (error) {
        // Puter prompts for sign-in on first use; that is a normal path.
        const name = error?.name || "";
        if (name === "AbortError") return { ok: false, reason: "aborted" };
        return { ok: false, reason: "error", detail: String(error?.message || error) };
      }
    },
  };

  /* --- Toast ------------------------------------------------------------ */
  let toastStack = null;

  const toast = (message, icon = "info") => {
    if (!toastStack) {
      toastStack = el("div", {
        class: "toast-stack",
        role: "status",
        "aria-live": "polite",
      });
      document.body.append(toastStack);
    }
    const node = el("div", { class: "toast" }, [
      icons[icon] ? icons[icon](18) : icons.info(18),
      el("span", { text: message }),
    ]);
    toastStack.append(node);
    setTimeout(() => {
      node.style.transition = "opacity .3s, transform .3s";
      node.style.opacity = "0";
      node.style.transform = "translateY(6px)";
      setTimeout(() => node.remove(), 320);
    }, 4200);
  };

  /* --- Notice helper ---------------------------------------------------- */
  const setNotice = (node, message, kind = "info") => {
    if (!node) return;
    if (!message) {
      node.hidden = true;
      node.textContent = "";
      return;
    }
    node.className = `notice notice--${kind}`;
    node.textContent = "";
    node.append(icons.alert(18), el("span", { text: message }));
    node.hidden = false;
  };

  const describeError = (error) => {
    if (!error) return "Something went wrong. Please try again.";
    if (error.code === "network") {
      return "We could not reach Great Church AI. Check your connection, then try again.";
    }
    if (error.code === "rate_limit_exceeded" || error.status === 429) {
      const seconds = error.retryAfter;
      if (seconds && seconds > 0) {
        const mins = Math.ceil(seconds / 60);
        return `Too many requests just now. Please wait about ${mins} minute${
          mins === 1 ? "" : "s"
        } and try again.`;
      }
      return "Too many requests just now. Please wait a moment and try again.";
    }
    return error.message || "Something went wrong. Please try again.";
  };

  /* --- Icons (inline SVG) ----------------------------------------------- */
  const svg = (paths, size = 20, extra = {}) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
      stroke-linecap="round" stroke-linejoin="round" width="${size}" height="${size}"
      aria-hidden="true" focusable="false" ${extra}>${paths}</svg>`;

  const icons = {
    church: (s) =>
      svg(
        `<path d="M12 2 3 7v2h18V7l-9-5Z"/><path d="M5 9v11M19 9v11M9.5 20v-6a2.5 2.5 0 0 1 5 0v6"/>`,
        s
      ),
    chat: (s) =>
      svg(
        `<path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.5 8.5 0 0 1-3.9-.9L3 20.5l1.5-4.6A8.4 8.4 0 0 1 12 3.1a8.4 8.4 0 0 1 9 8.4Z"/>`,
        s
      ),
    book: (s) =>
      svg(
        `<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>`,
        s
      ),
    study: (s) =>
      svg(
        `<path d="M12 6.25S10 4.5 6.5 4.5c-1.9 0-3 .4-3 .4v13s1.1-.4 3-.4c3.5 0 5.5 1.75 5.5 1.75s2-1.75 5.5-1.75c1.9 0 3 .4 3 .4v-13s-1.1-.4-3-.4C14 4.5 12 6.25 12 6.25Z"/><path d="M12 6.25v13"/>`,
        s
      ),
    prayer: (s) =>
      svg(
        `<path d="M12 21s-7.5-4.4-7.5-9.6A4.4 4.4 0 0 1 12 8.2a4.4 4.4 0 0 1 7.5 3.2C19.5 16.6 12 21 12 21Z"/><path d="M9 11h6M12 8v6"/>`,
        s
      ),
    sermon: (s) =>
      svg(
        `<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19a1 1 0 0 1 1 1v13.5"/><path d="M6.5 16H20v5H6.5A2.5 2.5 0 0 1 4 18.5v-13"/><path d="M8.5 7.5h7M8.5 11h5"/>`,
        s
      ),
    info: (s) =>
      svg(`<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>`, s),
    about: (s) =>
      svg(
        `<circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/>`,
        s
      ),
    send: (s) => svg(`<path d="M4.5 12h15M12.5 5l7 7-7 7"/>`, s),
    copy: (s) =>
      svg(
        `<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>`,
        s
      ),
    check: (s) => svg(`<path d="m4.5 12.5 5 5 10-11"/>`, s),
    retry: (s) =>
      svg(
        `<path d="M3 12a9 9 0 1 0 2.6-6.4"/><path d="M3 4.5V10h5.5"/>`,
        s
      ),
    trash: (s) =>
      svg(
        `<path d="M4 7h16M10 7V5h4v2M6 7l1 13h10l1-13"/><path d="M10.5 11v6M13.5 11v6"/>`,
        s
      ),
    search: (s) => svg(`<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>`, s),
    spark: (s) =>
      svg(
        `<path d="M12 3.5 13.9 9l5.6 1.9-5.6 2L12 18.5 10.1 13l-5.6-2L10.1 9 12 3.5Z"/><path d="M18.5 3v3M20 4.5h-3"/>`,
        s
      ),
    alert: (s) =>
      svg(
        `<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>`,
        s
      ),
    sun: (s) =>
      svg(
        `<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/>`,
        s
      ),
    shield: (s) =>
      svg(
        `<path d="M12 3 5 6v5.5c0 4.2 2.9 8.1 7 9.5 4.1-1.4 7-5.3 7-9.5V6l-7-3Z"/><path d="m9 12 2 2 4-4"/>`,
        s
      ),
    quote: (s) =>
      svg(
        `<path d="M9.5 6.5C7 8 5.5 10 5.5 12.8c0 2.4 1.4 4 3.3 4 1.7 0 2.9-1.2 2.9-2.8 0-1.6-1.1-2.7-2.6-2.7h-.5c.2-1.4 1.1-2.6 2.5-3.4l-1.6-1.4ZM17 6.5c-2.5 1.5-4 3.5-4 6.3 0 2.4 1.4 4 3.3 4 1.7 0 2.9-1.2 2.9-2.8 0-1.6-1.1-2.7-2.6-2.7h-.5c.2-1.4 1.1-2.6 2.5-3.4L17 6.5Z"/>`,
        s
      ),
    menu: (s) => svg(`<path d="M4 7h16M4 12h16M4 17h16"/>`, s),
  };

  /* --- Nav --------------------------------------------------------------- */
  const initNav = () => {
    const header = $("[data-header]");
    const toggle = $("[data-nav-toggle]");
    const nav = $("[data-nav]");

    if (toggle && nav) {
      toggle.addEventListener("click", () => {
        const open = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!open));
        nav.dataset.open = String(!open);
      });

      nav.addEventListener("click", (event) => {
        if (event.target.closest("a")) {
          toggle.setAttribute("aria-expanded", "false");
          nav.dataset.open = "false";
        }
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && nav.dataset.open === "true") {
          toggle.setAttribute("aria-expanded", "false");
          nav.dataset.open = "false";
          toggle.focus();
        }
      });
    }

    if (header) {
      const onScroll = () => {
        header.dataset.scrolled = String(window.scrollY > 8);
      };
      onScroll();
      window.addEventListener("scroll", onScroll, { passive: true });
    }

    // Mark the current page in the nav without hardcoding it per template.
    const here = window.location.pathname.replace(/\/index\.html$/, "/").replace(/\.html$/, "");
    $$("[data-nav] a").forEach((link) => {
      const target = new URL(link.href, window.location.href).pathname
        .replace(/\/index\.html$/, "/")
        .replace(/\.html$/, "");
      if (target === here || (here === "/" && target === "/")) {
        link.setAttribute("aria-current", "page");
      }
    });
  };

  /* --- Scroll reveal ------------------------------------------------------ */
  const initReveal = () => {
    const nodes = $$("[data-reveal]");
    if (!nodes.length) return;

    if (
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const delay = Number(entry.target.dataset.revealDelay || 0);
          setTimeout(() => entry.target.classList.add("is-visible"), delay);
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );

    nodes.forEach((node) => observer.observe(node));
  };

  /* --- Auto-growing textarea ---------------------------------------------- */
  const initAutogrow = (node) => {
    if (!node) return;
    const resize = () => {
      node.style.height = "auto";
      node.style.height = `${Math.min(node.scrollHeight, 180)}px`;
    };
    node.addEventListener("input", resize);
    resize();
  };

  /* --- Minimal markdown for model output ---------------------------------- */
  /* Renders a conservative subset into real DOM nodes. No innerHTML, so model
     output can never inject markup. */
  const renderRich = (target, text) => {
    target.textContent = "";
    const lines = String(text ?? "").split(/\r?\n/);
    let list = null;
    let listType = null;

    const closeList = () => {
      if (list) {
        target.append(list);
        list = null;
        listType = null;
      }
    };

    for (const raw of lines) {
      const line = raw.trimEnd();
      if (!line.trim()) {
        closeList();
        continue;
      }

      const heading = /^(#{1,4})\s+(.*)$/.exec(line);
      if (heading) {
        closeList();
        const level = Math.min(heading[1].length + 1, 5);
        target.append(el(`h${level}`, { text: heading[2] }));
        continue;
      }

      const quote = /^>\s?(.*)$/.exec(line);
      if (quote) {
        closeList();
        target.append(el("blockquote", { text: quote[1] }));
        continue;
      }

      const bullet = /^[-*•]\s+(.*)$/.exec(line);
      const numbered = /^\d+[.)]\s+(.*)$/.exec(line);
      if (bullet || numbered) {
        const type = bullet ? "ul" : "ol";
        if (!list || listType !== type) {
          closeList();
          list = el(type);
          listType = type;
        }
        list.append(el("li", { text: (bullet || numbered)[1] }));
        continue;
      }

      closeList();
      target.append(el("p", { text: line }));
    }

    closeList();
  };

  /* --- Boot --------------------------------------------------------------- */
  const boot = () => {
    initNav();
    initReveal();
    initAutogrow($("[data-autogrow]"));
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.GCA = {
    $, $$, el, escapeHtml, copyText, api, ApiError, ai, toast, setNotice,
    describeError, icons, renderRich, initReveal, initAutogrow,
  };
})();
