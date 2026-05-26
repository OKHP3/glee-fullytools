// Shared scripts for OverKill Hill P³ + subsites

// ──────────────────────────────────────────────────────────────
// Reading progress bar
// ──────────────────────────────────────────────────────────────
(function () {
  const bar = document.getElementById("reading-progress");
  if (!bar) return;

  window.addEventListener(
    "scroll",
    function () {
      const scrollTop =
        window.scrollY || document.documentElement.scrollTop;
      const docHeight =
        document.documentElement.scrollHeight -
        document.documentElement.clientHeight;
      const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = Math.min(pct, 100) + "%";
    },
    { passive: true }
  );
})();

// ──────────────────────────────────────────────────────────────
// Theme toggle, nav, and page interactions
// ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.querySelector(".theme-toggle");
  const savedTheme = localStorage.getItem("okh-theme");
  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme");
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("okh-theme", newTheme);
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector(".site-header");
  const navToggle = document.querySelector(".nav-toggle");
  const yearSpans = document.querySelectorAll(
    "#current-year, #current-year-about, #current-year-manifesto, #current-year-projects, #current-year-glee, #current-year-askjamie"
  );
  const body = document.body;

  // Mobile nav
  if (navToggle && header) {
    navToggle.addEventListener("click", () => {
      header.classList.toggle("nav-open");
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!expanded));
    });
  }

  // Header shadow
  if (header) {
    window.addEventListener("scroll", () => {
      if (window.scrollY > 50) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    });
  }

  // Year stamps
  const year = new Date().getFullYear();
  yearSpans.forEach((el) => {
    if (el) el.textContent = year;
  });

  // Theme toggle – only for core OverKill Hill pages
  const brandLocked =
    body.classList.contains("glee-main") ||
    body.classList.contains("askjamie-main");

  if (!brandLocked) {
    const themeToggle = document.createElement("button");
    themeToggle.classList.add("theme-toggle");
    themeToggle.setAttribute("aria-label", "Toggle theme");
    themeToggle.textContent = "🌓";

    if (header && header.querySelector(".container")) {
      header.querySelector(".container").appendChild(themeToggle);
    }

    const savedTheme = localStorage.getItem("okh-theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      document.documentElement.setAttribute("data-theme", savedTheme);
    }

    themeToggle.addEventListener("click", () => {
      const current =
        document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("okh-theme", next);
    });
  } else {
    // Subsites stay on their brand "light" look
    document.documentElement.setAttribute("data-theme", "light");
  }

  // Scroll reveal
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  if (!prefersReducedMotion && "IntersectionObserver" in window) {
    const revealEls = document.querySelectorAll(".reveal-on-scroll");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    revealEls.forEach((el) => observer.observe(el));
  } else {
    document
      .querySelectorAll(".reveal-on-scroll")
      .forEach((el) => el.classList.add("is-visible"));
  }

  // Smooth scroll for internal anchors
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (!href || href === "#") return;
      const target = document.querySelector(href);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

    // -----------------------------------------
  // Under-construction overlay gate (Glee, etc.)
  // -----------------------------------------
  const constructionOverlay = document.querySelector(".construction-overlay");

  if (constructionOverlay) {
    const body = document.body;
    const wipKey =
      constructionOverlay.getAttribute("data-wip-key") ||
      window.location.pathname;

    const storageKey = `glee-wip-dismissed:${wipKey}`;

    // If user already dismissed this specific WIP page, hide overlay
    if (localStorage.getItem(storageKey) === "true") {
      body.classList.add("construction-dismissed");
      constructionOverlay.setAttribute("hidden", "true");
    } else {
      // Wire up dismiss buttons
      const dismissButtons = constructionOverlay.querySelectorAll(
        "[data-wip-dismiss]"
      );

      dismissButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          body.classList.add("construction-dismissed");
          constructionOverlay.setAttribute("aria-hidden", "true");
          localStorage.setItem(storageKey, "true");
        });
      });

      // Optional: clicking the dark scrim (outside the card) also dismisses
      constructionOverlay.addEventListener("click", (event) => {
        if (event.target === constructionOverlay) {
          const primaryDismiss = constructionOverlay.querySelector(
            "[data-wip-dismiss]"
          );
          if (primaryDismiss) primaryDismiss.click();
        }
      });
    }
  }

});

// ──────────────────────────────────────────────────────────────────────────
// Sticky TOC: smooth-lerp scroll-follow for #toc-widget
// Only activates on wide viewports (≥1024 px) when widget exists.
// Cross-site shared module — kept in parity with overkillhill.com + askjamie.bot.
// Self-disables when no #toc-widget is present (Glee currently has none).
// ──────────────────────────────────────────────────────────────────────────
(function () {
  if (window.innerWidth < 1024) return;

  var toc    = document.getElementById('toc-widget');
  var footer = document.querySelector('.site-footer');
  if (!toc || !footer) return;

  var lerpedY = 0;
  var targetY = 0;
  var SPEED   = 0.08;   /* 0 = no movement, 1 = instant */
  var NAV_H   = 112;    /* minimum px from viewport top — clears sticky nav */
  var PAD     = 32;     /* px breathing room above the footer */

  function lerp(a, b, t) { return a + (b - a) * t; }

  /* Natural document position of the TOC widget before any transforms */
  function getNaturalTop(el) {
    var top = 0;
    while (el) { top += el.offsetTop; el = el.offsetParent; }
    return top;
  }

  var tocNaturalTop = getNaturalTop(toc);
  var tocH          = toc.offsetHeight;

  function tick() {
    var scrollY   = window.scrollY;
    var footerTop = footer.offsetTop;

    var centeredOffset = Math.max(NAV_H, (window.innerHeight - tocH) / 2);
    var raw = Math.max(0, scrollY + centeredOffset - tocNaturalTop);
    var max = Math.max(0, footerTop - PAD - tocNaturalTop - tocH);
    targetY = Math.min(raw, max);

    lerpedY = lerp(lerpedY, targetY, SPEED);
    toc.style.transform = 'translateY(' + lerpedY.toFixed(2) + 'px)';

    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);

  window.addEventListener('resize', function () {
    if (window.innerWidth < 1024) {
      toc.style.transform = '';
    } else {
      toc.style.transform = '';
      tocNaturalTop = getNaturalTop(toc);
      tocH = toc.offsetHeight;
    }
  });
}());


// ══════════════════════════════════════════════════════════════════════════════
// Search — merged from search.js
// Vanilla JS, zero-dependency client-side search. Self-contained IIFE.
// See original file history at: assets/js/search.js (removed 2026-05-04)
// ══════════════════════════════════════════════════════════════════════════════
/* ──────────────────────────────────────────────────────────────
 * Glee-fully Personalizable Tools™ — Internal Search
 *
 * Vanilla JS, zero-dependency client-side search:
 *  • Lazy-loads /assets/data/search-index.json on first interaction
 *  • Tokenizes the query and scores results by weighted field match
 *    (title > description > headings > body)
 *  • Renders a modal overlay with grouped results (branches / tools / pages)
 *
 * Trigger:
 *  • Click the magnifier button injected into the primary nav
 *  • Press “/” anywhere outside an input
 *  • Press ⌘K (or Ctrl+K)
 *
 * Close:
 *  • Esc, click the backdrop, or click the close button
 *
 * The UI is injected into every page by app.js so individual
 * page templates do not have to be edited.
 * ────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  const INDEX_URL = "/assets/data/search-index.json";
  const MAX_RESULTS = 12;        // modal overlay cap
  const MAX_RESULTS_INLINE = 60; // dedicated /search/ page cap
  const MIN_QUERY = 2;

  // ── Tokenization ────────────────────────────────────────────
  const STOP_WORDS = new Set([
    "the", "a", "an", "and", "or", "of", "in", "on", "at",
    "to", "for", "with", "by", "is", "are", "be", "from",
    "your", "you", "this", "that", "it", "as", "but", "if",
    "into", "out", "up", "down", "off"
  ]);

  function tokenize(text) {
    if (!text) return [];
    return text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, " ")
      .split(/\s+/)
      .map(t => t.replace(/^-+|-+$/g, ""))
      .filter(t => t.length >= 2 && !STOP_WORDS.has(t));
  }

  // ── Scoring ────────────────────────────────────────────────
  // Field weights — bigger = matters more.
  const W = {
    title: 10,
    titleStart: 6,      // bonus when token appears at start of title
    headings: 5,
    description: 4,
    keywords: 4,
    branch: 3,
    section: 2,
    body: 1,
  };

  function scorePage(page, tokens, originalQuery) {
    if (tokens.length === 0) return 0;
    let score = 0;
    const titleLower = (page.title || "").toLowerCase();
    const descLower = (page.description || "").toLowerCase();
    const kwLower = (page.keywords || "").toLowerCase();
    const sectionLower = (page.section || "").toLowerCase();
    const branchLower = (page.branch || "").toLowerCase();
    const headingsLower = (page.headings || []).join(" ").toLowerCase();
    const bodyLower = (page.body || "").toLowerCase();
    const queryLower = (originalQuery || "").toLowerCase().trim();

    // Phrase bonus — exact substring match wins big
    if (queryLower.length >= 3) {
      if (titleLower.includes(queryLower)) score += 25;
      if (descLower.includes(queryLower)) score += 8;
      if (headingsLower.includes(queryLower)) score += 8;
      if (bodyLower.includes(queryLower)) score += 3;
    }

    let allTokensFound = true;

    for (const tok of tokens) {
      let tokenHit = false;

      if (titleLower.includes(tok)) {
        score += W.title;
        tokenHit = true;
        if (titleLower.startsWith(tok)) score += W.titleStart;
      }
      if (descLower.includes(tok)) { score += W.description; tokenHit = true; }
      if (headingsLower.includes(tok)) { score += W.headings; tokenHit = true; }
      if (kwLower.includes(tok)) { score += W.keywords; tokenHit = true; }
      if (branchLower.includes(tok)) { score += W.branch; tokenHit = true; }
      if (sectionLower.includes(tok)) { score += W.section; tokenHit = true; }
      if (bodyLower.includes(tok)) { score += W.body; tokenHit = true; }

      if (!tokenHit) allTokensFound = false;
    }

    // All-tokens-match bonus
    if (allTokensFound) score += 6;

    // Slight boost for branch landing pages and the toolbox hub —
    // they’re higher-value entry points.
    if (page.section === "Branch" || page.section === "Toolbox") score += 1;

    return score;
  }

  function search(index, query, limit) {
    const tokens = tokenize(query);
    if (tokens.length === 0) return [];
    const results = [];
    for (const page of index.pages) {
      const score = scorePage(page, tokens, query);
      if (score > 0) results.push({ page, score });
    }
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, limit || MAX_RESULTS);
  }

  // ── Snippet builder ────────────────────────────────────────
  function buildSnippet(page, tokens) {
    const haystacks = [page.description, page.headings.join(" · "), page.body];
    for (const text of haystacks) {
      if (!text) continue;
      const lower = text.toLowerCase();
      for (const tok of tokens) {
        const i = lower.indexOf(tok);
        if (i !== -1) {
          const start = Math.max(0, i - 50);
          const end = Math.min(text.length, i + tok.length + 90);
          let slice = text.slice(start, end).trim();
          if (start > 0) slice = "…" + slice;
          if (end < text.length) slice = slice + "…";
          return slice;
        }
      }
    }
    return page.description || (page.body || "").slice(0, 140);
  }

  function highlight(text, tokens) {
    if (!text) return "";
    let escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    for (const tok of tokens) {
      if (!tok) continue;
      const re = new RegExp("(" + tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      escaped = escaped.replace(re, "<mark>$1</mark>");
    }
    return escaped;
  }

  // ── Index loader (lazy, cached) ────────────────────────────
  let indexPromise = null;

  function loadIndex() {
    if (indexPromise) return indexPromise;
    // "no-cache" forces a conditional revalidation (sends If-Modified-Since
    // and accepts a 304). This means a fresh index ships immediately after a
    // rebuild, while unchanged indexes still short-circuit to a 304 with no
    // payload — the right tradeoff for a 130 KB static file.
    indexPromise = fetch(INDEX_URL, { cache: "no-cache" })
      .then(r => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .catch(err => {
        console.error("[search] failed to load index:", err);
        indexPromise = null;
        throw err;
      });
    return indexPromise;
  }

  // ── DOM: build the UI once and inject ──────────────────────
  function buildUI() {
    if (document.getElementById("glee-search-modal")) return;

    const overlay = document.createElement("div");
    overlay.id = "glee-search-modal";
    overlay.className = "glee-search-modal";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Site search");
    overlay.setAttribute("hidden", "");

    overlay.innerHTML = `
      <div class="glee-search-backdrop" data-search-close></div>
      <div class="glee-search-panel" role="document">
        <header class="glee-search-header">
          <label for="glee-search-input" class="glee-search-label" aria-label="Search this site">
            <svg class="glee-search-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <circle cx="11" cy="11" r="7"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              id="glee-search-input"
              type="search"
              autocomplete="off"
              autocapitalize="off"
              spellcheck="false"
              placeholder="Search Tools, branches, pages…"
              aria-controls="glee-search-results"
            />
          </label>
          <button type="button" class="glee-search-close" data-search-close aria-label="Close search">
            <span aria-hidden="true">×</span>
          </button>
        </header>
        <div class="glee-search-status" id="glee-search-status" role="status" aria-live="polite"></div>
        <ul id="glee-search-results" class="glee-search-results" role="listbox" aria-label="Search results"></ul>
        <footer class="glee-search-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>Enter</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </footer>
      </div>
    `;

    document.body.appendChild(overlay);

    const input = overlay.querySelector("#glee-search-input");
    const results = overlay.querySelector("#glee-search-results");
    const status = overlay.querySelector("#glee-search-status");
    let activeIndex = -1;
    let lastTokens = [];

    function setStatus(msg) {
      status.textContent = msg || "";
    }

    function renderResults(matches, tokens) {
      results.innerHTML = "";
      activeIndex = -1;
      lastTokens = tokens;
      if (matches.length === 0) return;

      matches.forEach((m, i) => {
        const li = document.createElement("li");
        li.className = "glee-search-result";
        li.setAttribute("role", "option");
        li.dataset.index = String(i);

        const a = document.createElement("a");
        a.href = m.page.url;
        a.className = "glee-search-result-link";
        a.tabIndex = -1;

        const sectionTag = m.page.section || "Page";
        const snippet = buildSnippet(m.page, tokens);

        a.innerHTML = `
          <span class="glee-search-result-section">${escapeHtml(sectionTag)}</span>
          <span class="glee-search-result-title">${highlight(m.page.title, tokens)}</span>
          <span class="glee-search-result-url">${escapeHtml(m.page.url)}</span>
          <span class="glee-search-result-snippet">${highlight(snippet, tokens)}</span>
        `;

        li.appendChild(a);
        results.appendChild(li);
      });
    }

    function setActive(i) {
      const items = results.querySelectorAll(".glee-search-result");
      if (items.length === 0) return;
      if (i < 0) i = items.length - 1;
      if (i >= items.length) i = 0;
      items.forEach(el => el.classList.remove("is-active"));
      items[i].classList.add("is-active");
      items[i].scrollIntoView({ block: "nearest" });
      activeIndex = i;
    }

    function runQuery(q) {
      const trimmed = q.trim();
      if (trimmed.length < MIN_QUERY) {
        results.innerHTML = "";
        setStatus(trimmed.length === 0 ? "" : "Keep typing…");
        return;
      }
      loadIndex()
        .then(idx => {
          const matches = search(idx, trimmed);
          if (matches.length === 0) {
            setStatus(`No results for “${trimmed}”.`);
            results.innerHTML = "";
            return;
          }
          setStatus(`${matches.length} result${matches.length === 1 ? "" : "s"} for “${trimmed}”.`);
          renderResults(matches, tokenize(trimmed));
        })
        .catch(() => {
          setStatus("Search index could not load. Please try again.");
        });
    }

    let debounceId = null;
    input.addEventListener("input", () => {
      clearTimeout(debounceId);
      const value = input.value;
      debounceId = setTimeout(() => runQuery(value), 90);
    });

    input.addEventListener("keydown", (e) => {
      const items = results.querySelectorAll(".glee-search-result");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive(activeIndex + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(activeIndex - 1);
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          const link = items[activeIndex].querySelector("a");
          if (link) window.location.href = link.href;
        } else if (items.length > 0) {
          e.preventDefault();
          const link = items[0].querySelector("a");
          if (link) window.location.href = link.href;
        }
      }
    });

    overlay.addEventListener("click", (e) => {
      const t = e.target;
      if (t && (t.matches("[data-search-close]") || t.closest("[data-search-close]"))) {
        closeModal();
      }
    });

    // expose handles for opener
    overlay._gleeSearch = { input, results, status, runQuery };
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ── Open / close ───────────────────────────────────────────
  function openModal(prefill) {
    buildUI();
    const overlay = document.getElementById("glee-search-modal");
    if (!overlay) return;
    overlay.removeAttribute("hidden");
    document.documentElement.classList.add("glee-search-open");
    // Pre-warm the index in the background
    loadIndex().catch(() => {});
    const { input, runQuery } = overlay._gleeSearch;
    if (typeof prefill === "string" && prefill.length > 0) {
      input.value = prefill;
      runQuery(prefill);
    }
    setTimeout(() => input.focus(), 30);
  }

  function closeModal() {
    const overlay = document.getElementById("glee-search-modal");
    if (!overlay) return;
    overlay.setAttribute("hidden", "");
    document.documentElement.classList.remove("glee-search-open");
  }

  function toggleModal() {
    const overlay = document.getElementById("glee-search-modal");
    if (!overlay || overlay.hasAttribute("hidden")) {
      openModal();
    } else {
      closeModal();
    }
  }

  // ── Inject the search button into the primary nav ──────────
  function injectNavButton() {
    const nav = document.querySelector(".primary-nav ul");
    if (!nav) return;
    if (nav.querySelector("[data-glee-search-trigger]")) return;

    const li = document.createElement("li");
    li.className = "glee-search-nav";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "glee-search-trigger";
    btn.setAttribute("data-glee-search-trigger", "");
    btn.setAttribute("aria-label", "Search the site");
    btn.title = "Search ( / )";
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <circle cx="11" cy="11" r="7"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <span class="glee-search-trigger-label">Search</span>
    `;
    btn.addEventListener("click", () => openModal());

    li.appendChild(btn);
    nav.appendChild(li);
  }

  // ── Global key bindings ────────────────────────────────────
  function bindKeys() {
    document.addEventListener("keydown", (e) => {
      // Esc closes
      if (e.key === "Escape") {
        const overlay = document.getElementById("glee-search-modal");
        if (overlay && !overlay.hasAttribute("hidden")) {
          e.preventDefault();
          closeModal();
        }
        return;
      }
      // Cmd/Ctrl + K opens
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        openModal();
        return;
      }
      // Slash opens (only when not typing in a field)
      if (e.key === "/" && !isTypingTarget(e.target)) {
        e.preventDefault();
        openModal();
      }
    });
  }

  function isTypingTarget(el) {
    if (!el) return false;
    const tag = (el.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    if (el.isContentEditable) return true;
    return false;
  }

  // ── Inline rendering (for the dedicated /search/ page) ─────
  // Renders results into a host element instead of opening the modal.
  // The host page provides:
  //   <input data-glee-search-inline-input>      ← controlled input
  //   <div   data-glee-search-inline-status>     ← live status text
  //   <ul    data-glee-search-inline-results>    ← results target
  //   <div   data-glee-search-inline-categories> ← optional chip rail
  // Returns a controller { runQuery(q) } so the host can drive it.
  function attachInline(root) {
    root = root || document;
    const input = root.querySelector("[data-glee-search-inline-input]");
    const status = root.querySelector("[data-glee-search-inline-status]");
    const list = root.querySelector("[data-glee-search-inline-results]");
    const cats = root.querySelector("[data-glee-search-inline-categories]");
    if (!input || !list) return null;

    let cachedIndex = null;
    let activeCategory = "all";
    let lastQuery = "";

    function setStatus(msg) {
      if (status) status.textContent = msg || "";
    }

    function renderInto(matches, tokens) {
      list.innerHTML = "";
      if (matches.length === 0) return;
      matches.forEach((m) => {
        const li = document.createElement("li");
        li.className = "glee-search-result";
        const a = document.createElement("a");
        a.href = m.page.url;
        a.className = "glee-search-result-link";
        const sectionTag = m.page.section || "Page";
        const snippet = buildSnippet(m.page, tokens);
        a.innerHTML = `
          <span class="glee-search-result-section">${escapeHtml(sectionTag)}</span>
          <span class="glee-search-result-title">${highlight(m.page.title, tokens)}</span>
          <span class="glee-search-result-url">${escapeHtml(m.page.url)}</span>
          <span class="glee-search-result-snippet">${highlight(snippet, tokens)}</span>
        `;
        li.appendChild(a);
        list.appendChild(li);
      });
    }

    function buildCategoryChips(index) {
      if (!cats) return;
      const counts = {};
      for (const p of index.pages) {
        const c = p.section || "Page";
        counts[c] = (counts[c] || 0) + 1;
      }
      const ordered = ["all"].concat(Object.keys(counts).sort());
      cats.innerHTML = ordered.map((c) => {
        const label = c === "all"
          ? `All (${index.pages.length})`
          : `${c} (${counts[c]})`;
        const pressed = c === activeCategory ? "true" : "false";
        return `<button type="button" class="glee-search-chip" data-cat="${escapeHtml(c)}" aria-pressed="${pressed}">${escapeHtml(label)}</button>`;
      }).join("");
      cats.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          activeCategory = btn.getAttribute("data-cat") || "all";
          cats.querySelectorAll("button").forEach((b) => {
            b.setAttribute("aria-pressed", b === btn ? "true" : "false");
          });
          // Re-run the most recent query against the new filter
          runQuery(lastQuery, { skipUrl: false });
        });
      });
    }

    function syncUrl(q) {
      // Keep the URL synchronized with the live UI: write `?q=` for valid
      // queries, drop it entirely for empty/too-short ones. Avoids stale
      // params misrepresenting the visible state.
      try {
        const url = new URL(window.location.href);
        // Always strip the legacy `?s=` param — `?q=` is the single
        // authoritative search param across the inline page, regardless of
        // whether the visitor arrived from a sitelink that used `s`.
        url.searchParams.delete("s");
        if (q && q.length >= MIN_QUERY) {
          url.searchParams.set("q", q);
        } else {
          url.searchParams.delete("q");
        }
        window.history.replaceState({}, "", url);
      } catch (_) { /* noop */ }
    }

    function setIdleStatus(index) {
      // Friendly idle line shown when no query is active — matches the
      // "Type to search N indexed entries." pattern from the sibling site.
      setStatus(`Type to search ${index.pages.length} indexed entries.`);
    }

    function runQuery(q, opts) {
      opts = opts || {};
      const trimmed = (q || "").trim();
      lastQuery = trimmed;

      // Empty query → clear results, show idle status, drop URL params
      if (trimmed.length === 0) {
        list.innerHTML = "";
        if (cachedIndex) setIdleStatus(cachedIndex); else setStatus("");
        if (!opts.skipUrl) syncUrl("");
        return;
      }
      if (trimmed.length < MIN_QUERY) {
        list.innerHTML = "";
        setStatus("Type at least 2 characters to search.");
        if (!opts.skipUrl) syncUrl("");
        return;
      }
      setStatus("Searching…");
      loadIndex()
        .then((index) => {
          cachedIndex = index;
          let matches = search(index, trimmed, MAX_RESULTS_INLINE);
          if (activeCategory !== "all") {
            matches = matches.filter((m) =>
              (m.page.section || "Page").toLowerCase() === activeCategory.toLowerCase()
            );
          }
          const inCat = activeCategory !== "all" ? ` in ${activeCategory}` : "";
          if (matches.length === 0) {
            setStatus(`No results for “${trimmed}”${inCat}. Try a different word.`);
          } else {
            setStatus(`${matches.length} result${matches.length === 1 ? "" : "s"} for “${trimmed}”${inCat}.`);
          }
          renderInto(matches, tokenize(trimmed));
          if (!opts.skipUrl) syncUrl(trimmed);
        })
        .catch(() => {
          setStatus("Search index could not load. Please try again.");
        });
    }

    // Pre-warm the index so the chip rail and idle-state stats appear as
    // soon as possible, even before the user types anything.
    setStatus("Loading index…");
    loadIndex()
      .then((index) => {
        cachedIndex = index;
        buildCategoryChips(index);
        if (!input.value.trim()) setIdleStatus(index);
      })
      .catch(() => setStatus("Search index could not load. Please try again."));

    let debounceId = null;
    input.addEventListener("input", () => {
      clearTimeout(debounceId);
      debounceId = setTimeout(() => runQuery(input.value), 120);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runQuery(input.value);
      }
    });

    return { runQuery };
  }

  // ── Boot ───────────────────────────────────────────────────
  function init() {
    // Detect the dedicated search page first — on that page we run
    // inline (no modal) and skip the auto-open behavior.
    const inlineRoot = document.querySelector("[data-glee-search-inline]");
    const isInline = !!inlineRoot;

    injectNavButton();
    bindKeys();

    if (isInline) {
      const controller = attachInline(inlineRoot);
      const params = new URLSearchParams(window.location.search);
      const q = (params.get("q") || params.get("s") || "").trim();
      const input = inlineRoot.querySelector("[data-glee-search-inline-input]");
      if (input) {
        if (q) input.value = q;
        setTimeout(() => input.focus(), 30);
      }
      if (controller && q.length >= MIN_QUERY) controller.runQuery(q);
      return;
    }

    // Auto-open if URL contains ?s=query  (matches the JSON-LD SearchAction
    // declaration on index.html — visitors arriving from a search engine
    // sitelink will see results immediately).
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("s");
      if (q && q.trim().length >= MIN_QUERY) {
        openModal(q.trim());
      }
    } catch (_) { /* noop */ }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // expose for other scripts/debugging
  window.GleeSearch = {
    open: openModal,
    close: closeModal,
    toggle: toggleModal,
    attachInline: attachInline,
  };
})();
