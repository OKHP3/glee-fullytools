// ════════════════════════════════════════════════════════════════════════════
//  app.js — Shared client-side script (OverKill Hill P³)
//
//  Sections (in load order):
//   1. GLOBAL   · Reading-progress bar (article pages)
//   2. GLOBAL   · DOMContentLoaded: nav, year stamps, theme toggle (OKH only),
//                 scroll reveal, smooth anchors
//   3. GLEE     · Under-construction overlay gate (toolbox WIP pages)
//   4. GLOBAL   · Sticky TOC scroll-follow (article pages, ≥1024px)
//   5. OKH      · Site search — overlay + dedicated /search/ page
//                 (search.js consolidated here 2026-05-03)
//   7. GLOBAL   · Service-worker registration for the offline shell
// ════════════════════════════════════════════════════════════════════════════

// ── 1. Reading progress bar ─────────────────────────────────────────────────
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

// ── 2. Page interactions: nav, year, theme toggle, scroll reveal ───────────
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

    // Close nav on Escape and return focus to trigger (WCAG 2.1.1)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && header.classList.contains("nav-open")) {
        header.classList.remove("nav-open");
        navToggle.setAttribute("aria-expanded", "false");
        navToggle.focus();
      }
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

  // ── Header controls wrapper (holds search + theme toggle) ───────────────────
  // Created on all pages so injectTrigger() always has a consistent target.
  let headerControls = null;
  if (header) {
    const container = header.querySelector(".container");
    if (container) {
      headerControls = document.createElement("div");
      headerControls.className = "header-controls";
      const navTogglePre = container.querySelector(".nav-toggle");
      if (navTogglePre) {
        container.insertBefore(headerControls, navTogglePre);
      } else {
        container.appendChild(headerControls);
      }
    }
  }

  // Theme toggle – only for core OverKill Hill pages (brand-locked sites force light)
  const brandLocked =
    body.classList.contains("glee-main") ||
    body.classList.contains("askjamie-main");

  if (!brandLocked) {
    const STATES      = ["system", "light", "dark"];
    const STATE_ICONS = {
      system: '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
      light:  '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
      dark:   '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    };
    const STATE_ARIA  = {
      system: "Switch to light mode",
      light:  "Switch to dark mode",
      dark:   "Switch to system mode",
    };

    let savedTheme = null;
    try { savedTheme = localStorage.getItem("okh-theme"); } catch (_) {}
    let currentState = STATES.includes(savedTheme) ? savedTheme : "system";

    function applyThemeState(state) {
      if (state === "system") {
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
      } else {
        document.documentElement.setAttribute("data-theme", state);
      }
    }

    applyThemeState(currentState);

    const themeToggle = document.createElement("button");
    themeToggle.classList.add("theme-toggle");
    themeToggle.dataset.state = currentState;
    themeToggle.setAttribute("aria-label", STATE_ARIA[currentState]);
    themeToggle.innerHTML = STATE_ICONS[currentState];

    if (headerControls) {
      headerControls.appendChild(themeToggle);
    } else if (header && header.querySelector(".container")) {
      header.querySelector(".container").appendChild(themeToggle);
    }

    themeToggle.addEventListener("click", () => {
      const idx    = STATES.indexOf(currentState);
      currentState = STATES[(idx + 1) % STATES.length];
      themeToggle.dataset.state = currentState;
      themeToggle.setAttribute("aria-label", STATE_ARIA[currentState]);
      themeToggle.innerHTML = STATE_ICONS[currentState];
      applyThemeState(currentState);
      try { localStorage.setItem("okh-theme", currentState); } catch (_) {}
    });

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (currentState === "system") applyThemeState("system");
    });
  } else {
    // ── Glee-fully / AskJamie: brand-light surface + optional dark-scheme toggle ──
    // Both subsites keep data-theme="light" so their html[data-theme="light"] CSS rules
    // fire. They manage dark mode via a separate data-color-scheme attribute + their own
    // localStorage key (glee-color-scheme / askjamie-color-scheme).
    document.documentElement.setAttribute("data-theme", "light");

    const isGlee     = body.classList.contains("glee-main");
    const LS_KEY     = isGlee ? "glee-color-scheme" : "askjamie-color-scheme";
    const SCH_STATES = ["auto", "light", "dark"];
    const THEME_COLORS = isGlee
      ? { light: "#d35b2d", dark: "#1e1b19" }
      : { light: "#f5efe1", dark: "#2c5e6f" };

    // Icons shared with the OKH toggle (same SVG paths, same .tt-icon class)
    const SCH_ICONS = {
      auto:  '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
      light: '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
      dark:  '<svg class="tt-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    };
    const SCH_ARIA = {
      auto:  "Color scheme: following your device — click to pin light",
      light: "Color scheme: pinned light — click to switch to dark",
      dark:  "Color scheme: pinned dark — click to follow device",
    };

    // Restore saved state (the early-init <head> script already applied it before
    // first paint for pages that include it; this just syncs the button).
    let savedScheme = null;
    try { savedScheme = localStorage.getItem(LS_KEY); } catch (_) {}
    let schemeState   = SCH_STATES.includes(savedScheme) ? savedScheme : "auto";

    function applySchemeState(state) {
      if (state === "auto") {
        document.documentElement.removeAttribute("data-color-scheme");
      } else {
        document.documentElement.setAttribute("data-color-scheme", state);
      }

      document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
        if (state !== "auto") {
          meta.setAttribute("content", THEME_COLORS[state]);
          return;
        }

        const media = meta.getAttribute("media") || "";
        meta.setAttribute(
          "content",
          media.includes("prefers-color-scheme: dark")
            ? THEME_COLORS.dark
            : THEME_COLORS.light
        );
      });
    }

    // Apply on load (handles pages that don't have the early-init script)
    applySchemeState(schemeState);

    // Create the toggle button
    const schemeToggle = document.createElement("button");
    schemeToggle.classList.add("glee-color-toggle");
    schemeToggle.dataset.state = schemeState;
    schemeToggle.setAttribute("aria-label", SCH_ARIA[schemeState]);
    schemeToggle.innerHTML = SCH_ICONS[schemeState];

    if (headerControls) {
      headerControls.appendChild(schemeToggle);
    } else if (header && header.querySelector(".container")) {
      header.querySelector(".container").appendChild(schemeToggle);
    }

    schemeToggle.addEventListener("click", () => {
      const idx   = SCH_STATES.indexOf(schemeState);
      schemeState = SCH_STATES[(idx + 1) % SCH_STATES.length];
      schemeToggle.dataset.state = schemeState;
      schemeToggle.setAttribute("aria-label", SCH_ARIA[schemeState]);
      schemeToggle.innerHTML = SCH_ICONS[schemeState];
      applySchemeState(schemeState);
      try {
        if (schemeState === "auto") {
          localStorage.removeItem(LS_KEY);
        } else {
          localStorage.setItem(LS_KEY, schemeState);
        }
      } catch (_) {}
    });
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

  // ── 3. GLEE · Under-construction overlay gate ────────────────────────────
  // Used on glee-fully.tools toolbox pages that are live-but-not-finished.
  // No-op on pages without `.construction-overlay`.
  const constructionOverlay = document.querySelector(".construction-overlay");

  if (constructionOverlay) {
    constructionOverlay.setAttribute("role", "dialog");
    constructionOverlay.setAttribute("aria-modal", "true");
    constructionOverlay.setAttribute("aria-label", "Work-in-progress page notice");
    const body = document.body;
    const activeElement = document.activeElement;
    const opener = activeElement instanceof HTMLElement &&
      activeElement !== document.body &&
      activeElement !== document.documentElement
      ? activeElement
      : null;
    const wipKey =
      constructionOverlay.getAttribute("data-wip-key") ||
      window.location.pathname;

    const storageKey = `glee-wip-dismissed:${wipKey}`;

    // If user already dismissed this specific WIP page, hide overlay
    let wipDismissed = false;
    try { wipDismissed = localStorage.getItem(storageKey) === "true"; } catch (_) {}
    if (wipDismissed) {
      body.classList.add("construction-dismissed");
      constructionOverlay.setAttribute("hidden", "");
    } else {
      // Wire up dismiss buttons
      const dismissOverlay = () => {
        body.classList.add("construction-dismissed");
        constructionOverlay.setAttribute("aria-hidden", "true");
        constructionOverlay.setAttribute("hidden", "");
        try { localStorage.setItem(storageKey, "true"); } catch (_) {}

        // Return focus to the element that opened the gate when it still exists;
        // otherwise use the page heading as a stable, meaningful fallback.
        if (opener && opener.isConnected && !constructionOverlay.contains(opener)) {
          opener.focus();
          return;
        }
        const mainTarget = document.querySelector("#main h1, #main");
        if (mainTarget) {
          if (!mainTarget.hasAttribute("tabindex")) mainTarget.setAttribute("tabindex", "-1");
          mainTarget.focus({ preventScroll: true });
        }
      };

      const dismissButtons = constructionOverlay.querySelectorAll(
        "[data-wip-dismiss]"
      );

      dismissButtons.forEach((btn) => {
        btn.addEventListener("click", dismissOverlay);
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

      // Move focus into the overlay's dismiss button so keyboard users are
      // not left stranded on skip-link or outside the modal (WCAG 2.4.3)
      const overlayFocusable = Array.from(
        constructionOverlay.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      if (overlayFocusable.length) {
        requestAnimationFrame(() => overlayFocusable[0].focus());
      }

      // Focus trap — keep Tab/Shift+Tab inside the overlay while it is visible (WCAG 2.1.1)
      constructionOverlay.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          dismissOverlay();
          return;
        }
        if (e.key !== "Tab" || !overlayFocusable.length) return;
        const first = overlayFocusable[0];
        const last  = overlayFocusable[overlayFocusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
          if (document.activeElement === last)  { e.preventDefault(); first.focus(); }
        }
      });
    }
  }

});

// ── 4. Sticky TOC: smooth-lerp scroll-follow for #toc-widget ───────────────
// Only activates on wide viewports (≥1024 px) when widget exists.
// No-op on every other page (return on missing element).
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

// ── 4b. TOC scrollspy — active-link tracking for #toc-widget ───────────
// Works on any page that has id="toc-widget" with .toc-list anchor links.
// Pairs with Section 4's lerp scroll-follow. No-op when widget is absent.
(function () {
  var links = Array.from(document.querySelectorAll('#toc-widget .toc-list a[href^="#"]'));
  if (!links.length) return;

  var targets = links
    .map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); })
    .filter(Boolean);
  if (!targets.length) return;

  function setActive() {
    var triggerY = window.scrollY + window.innerHeight * 0.20;
    var activeId = null;
    targets.forEach(function (el) {
      if (el.getBoundingClientRect().top + window.scrollY <= triggerY) activeId = el.id;
    });
    links.forEach(function (a) {
      a.classList.toggle('toc-active', a.getAttribute('href').slice(1) === activeId);
    });
  }

  window.addEventListener('scroll', setActive, { passive: true });
  setTimeout(setActive, 100);
}());

// ── 5. Glee-fully Search — overlay + dedicated /search/ page ────────────────
// Consolidated from search.js (2026-05-03). All production pages load this.
// Index: /assets/data/search-index.json  Styles: inlined into theme.css (2026-05-04)
// Keyboard: Ctrl/Cmd+K or "/" to open · Esc to close · ↑/↓ navigate · ↵ follow
(function () {
  "use strict";

  const INDEX_URL = "/assets/data/search-index.json";

  // ----- index loader (cached promise) -----
  let _indexPromise = null;
  function loadIndex() {
    if (!_indexPromise) {
      _indexPromise = fetch(INDEX_URL, { credentials: "same-origin" })
        .then((r) => {
          if (!r.ok) throw new Error("Index fetch failed: " + r.status);
          return r.json();
        })
        .then((d) => {
          // The current generator writes `pages`; accept the older `entries`
          // key too so a cached or older index cannot silently empty search.
          if (Array.isArray(d.pages)) return d.pages;
          return Array.isArray(d.entries) ? d.entries : [];
        })
        .catch((err) => {
          console.warn("[okh-search] index load failed:", err);
          return [];
        });
    }
    return _indexPromise;
  }

  // ----- scoring -----
  function normalizeSearchText(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/\p{M}/gu, "")
      .toLowerCase();
  }
  function tokenize(q) {
    return normalizeSearchText(q)
      .split(/[^\p{L}\p{N}'-]+/gu)
      .filter((t) => t.length >= 2);
  }
  function entrySection(entry) {
    return entry.section || entry.category || "Page";
  }
  function scoreEntry(entry, tokens) {
    if (!tokens.length) return 0;
    const title    = normalizeSearchText(entry.title);
    const desc     = normalizeSearchText(entry.description);
    const headings = normalizeSearchText((entry.headings || []).join(" "));
    const body     = normalizeSearchText(entry.body);
    const url      = normalizeSearchText(entry.url);

    let score = 0;
    let allHit = true;
    for (const t of tokens) {
      let tokenHit = 0;
      if (title.includes(t))    tokenHit += 8;
      if (headings.includes(t)) tokenHit += 5;
      if (desc.includes(t))     tokenHit += 4;
      if (body.includes(t))     tokenHit += 2;
      if (url.includes(t))      tokenHit += 1;
      if (tokenHit === 0) allHit = false;
      score += tokenHit;
    }
    // Bonus: full-phrase match
    const phrase = tokens.join(" ");
    if (phrase.length > 2) {
      if (title.includes(phrase)) score += 10;
      if (desc.includes(phrase))  score += 6;
      if (body.includes(phrase))  score += 4;
    }
    // Slight penalty for article-section duplicates so the parent ranks above
    if (entrySection(entry) === "Article Section") score -= 0.5;
    return allHit ? score : score * 0.4;
  }
  function search(entries, q, limit) {
    const tokens = tokenize(q);
    if (!tokens.length) return [];
    const scored = [];
    for (const e of entries) {
      const s = scoreEntry(e, tokens);
      if (s > 0) scored.push([s, e]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    return scored.slice(0, limit || 30).map(([s, e]) => ({ score: s, entry: e }));
  }

  // ----- snippet + highlight -----
  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }
  function snippetFor(entry, tokens, length) {
    const body = entry.body || entry.description || "";
    if (!body) return "";
    const lower = normalizeSearchText(body);
    let bestIdx = -1;
    for (const t of tokens) {
      const i = lower.indexOf(t);
      if (i !== -1 && (bestIdx === -1 || i < bestIdx)) bestIdx = i;
    }
    let start = 0;
    if (bestIdx > 80) start = Math.max(0, bestIdx - 60);
    let snip = body.slice(start, start + (length || 220));
    if (start > 0) snip = "…" + snip;
    if (start + (length || 220) < body.length) snip += "…";
    return snip;
  }
  function highlight(text, tokens) {
    let html = escapeHtml(text);
    for (const t of tokens) {
      if (!t) continue;
      const re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      html = html.replace(re, "<mark>$1</mark>");
    }
    return html;
  }

  // ----- result rendering -----
  function renderResultHtml(result, tokens) {
    const e = result.entry;
    const snip = snippetFor(e, tokens, 220);
    return (
      '<div class="okh-search-result-meta">' +
        '<span class="okh-search-result-cat">'  + escapeHtml(entrySection(e)) + "</span>" +
        '<span class="okh-search-result-url">'  + escapeHtml(e.url) + "</span>" +
      "</div>" +
      '<h3 class="okh-search-result-title">' + highlight(e.title || e.url, tokens) + "</h3>" +
      (snip ? '<p class="okh-search-result-snippet">' + highlight(snip, tokens) + "</p>" : "")
    );
  }

  // ── Overlay (every page) ────────────────────────────────────────────────
  function buildOverlay() {
    if (document.querySelector(".okh-search-overlay")) return null;
    const wrap = document.createElement("div");
    wrap.className = "okh-search-overlay";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");
    wrap.setAttribute("aria-label", "Search Glee-fully");
    wrap.innerHTML = (
      '<div class="okh-search-panel" role="document">' +
        '<div class="okh-search-input-row">' +
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
            '<circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />' +
          "</svg>" +
          '<input type="search" class="okh-search-input" autocomplete="off" spellcheck="false" ' +
            'placeholder="Search the Glee-fully Toolbox — tools, branches, guides…" aria-label="Search" />' +
          '<button type="button" class="okh-search-close" aria-label="Close search">Esc</button>' +
        "</div>" +
        '<div class="okh-search-results" role="list" aria-label="Search results"></div>' +
        '<div class="okh-search-status sr-only" role="status" aria-live="polite" aria-atomic="true"></div>' +
        '<div class="okh-search-footer">' +
          '<div class="okh-search-keys">' +
            "<span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>" +
            "<span><kbd>↵</kbd> open</span>" +
            "<span><kbd>Esc</kbd> close</span>" +
          "</div>" +
          '<a href="/search/">Open full search →</a>' +
        "</div>" +
      "</div>"
    );
    document.body.appendChild(wrap);
    return wrap;
  }

  function emptyStateHtml() {
    return (
      '<div class="okh-search-empty">' +
        "<p>Search across the Glee-fully Toolbox, branches, Tool-ettes, and guides.</p>" +
        '<ul class="okh-search-hint-list">' +
          '<li><button type="button" data-q="resume">Resume</button></li>' +
          '<li><button type="button" data-q="recipe">Recipe</button></li>' +
          '<li><button type="button" data-q="budget">Budget</button></li>' +
          '<li><button type="button" data-q="journal">Journal</button></li>' +
          '<li><button type="button" data-q="Arcade">Arcade</button></li>' +
          '<li><button type="button" data-q="wellness">Wellness</button></li>' +
        "</ul>" +
      "</div>"
    );
  }

  function initOverlay() {
    const overlay = buildOverlay();
    if (!overlay) return;
    const input    = overlay.querySelector(".okh-search-input");
    const list     = overlay.querySelector(".okh-search-results");
    const statusEl = overlay.querySelector(".okh-search-status");
    const closeBtn = overlay.querySelector(".okh-search-close");

    let entries        = [];
    let activeIdx      = 0;
    let currentResults = [];
    let lastTokens     = [];
    let lastFocus      = null;

    function focusableInPanel() {
      return Array.from(overlay.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), [tabindex]:not([tabindex="-1"])'
      )).filter((el) => el.offsetParent !== null || el === input);
    }

    function open() {
      if (overlay.dataset.open === "true") return;
      lastFocus = document.activeElement;
      if (!lastFocus || lastFocus === document.body || lastFocus === document.documentElement) {
        lastFocus = document.querySelector(".okh-search-trigger");
      }
      overlay.dataset.open = "true";
      document.documentElement.classList.add("okh-search-open");
      loadIndex().then((d) => {
        entries = d;
        if (input.value.trim()) render();
        else renderEmpty();
      });
      setTimeout(() => input.focus(), 30);
    }
    function close() {
      overlay.dataset.open = "false";
      document.documentElement.classList.remove("okh-search-open");
      if (lastFocus && typeof lastFocus.focus === "function") {
        try { lastFocus.focus(); } catch (e) { /* ignore */ }
      }
      lastFocus = null;
    }
    function renderEmpty() {
      list.innerHTML = emptyStateHtml();
      list.querySelectorAll("button[data-q]").forEach((btn) => {
        btn.addEventListener("click", () => {
          input.value = btn.getAttribute("data-q") || "";
          render();
          input.focus();
        });
      });
    }
    function setActive(i) {
      const links = list.querySelectorAll(".okh-search-result");
      activeIdx = Math.max(0, Math.min(i, links.length - 1));
      links.forEach((el, idx) => {
        if (idx === activeIdx) {
          el.setAttribute("data-active", "true");
          el.scrollIntoView({ block: "nearest" });
        } else {
          el.removeAttribute("data-active");
        }
      });
    }
    function render() {
      const q = input.value.trim();
      if (!q) { renderEmpty(); currentResults = []; lastTokens = []; if (statusEl) statusEl.textContent = ""; return; }
      lastTokens     = tokenize(q);
      currentResults = search(entries, q, 12);
      if (!currentResults.length) {
        list.innerHTML =
          '<div class="okh-search-noresults"><p>No matches for <strong>' +
          escapeHtml(q) + "</strong>.</p><p>Try <em>resume</em>, <em>recipe</em>, " +
          "<em>budget</em>, or <em>journal</em>.</p></div>";
        if (statusEl) statusEl.textContent = "No matches for " + q;
        return;
      }
      list.innerHTML = currentResults.map((r) => (
        '<div role="listitem"><a class="okh-search-result" href="' + escapeHtml(r.entry.url) + '">' +
          renderResultHtml(r, lastTokens) +
        "</a></div>"
      )).join("");
      if (statusEl) statusEl.textContent = currentResults.length + (currentResults.length === 1 ? " result" : " results") + " for " + q;
      setActive(0);
    }
    input.addEventListener("input", render);
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown")  { ev.preventDefault(); setActive(activeIdx + 1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); setActive(activeIdx - 1); }
      else if (ev.key === "Enter") {
        const links = list.querySelectorAll(".okh-search-result");
        if (links[activeIdx]) { ev.preventDefault(); window.location.href = links[activeIdx].getAttribute("href"); }
      }
    });
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });

    // Focus trap — keep Tab inside the panel while it's open
    overlay.addEventListener("keydown", (ev) => {
      if (ev.key !== "Tab" || overlay.dataset.open !== "true") return;
      const focusables = focusableInPanel();
      if (!focusables.length) { ev.preventDefault(); input.focus(); return; }
      const first  = focusables[0];
      const last   = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (ev.shiftKey) {
        if (active === first || !overlay.contains(active)) { ev.preventDefault(); last.focus(); }
      } else {
        if (active === last) { ev.preventDefault(); first.focus(); }
      }
    });

    document.addEventListener("keydown", (ev) => {
      if (overlay.dataset.open === "true" && ev.key === "Escape") { ev.preventDefault(); close(); return; }
      const constructionGate = document.querySelector(".construction-overlay");
      const constructionVisible = constructionGate &&
        !constructionGate.hasAttribute("hidden") &&
        !document.body.classList.contains("construction-dismissed");
      if (constructionVisible) return;
      const isMac    = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
      const trigger  = (isMac && ev.metaKey && ev.key.toLowerCase() === "k") ||
                       (!isMac && ev.ctrlKey && ev.key.toLowerCase() === "k");
      if (trigger) { ev.preventDefault(); open(); return; }
      if (ev.key === "/" && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
        const tag     = (document.activeElement && document.activeElement.tagName || "").toLowerCase();
        const isField = tag === "input" || tag === "textarea" || tag === "select" ||
                        (document.activeElement && document.activeElement.isContentEditable);
        if (!isField) { ev.preventDefault(); open(); }
      }
    });

    injectTrigger(open);
  }

  function injectTrigger(openFn) {
    if (document.querySelector(".okh-search-trigger")) return;
    const isMac    = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
    const shortcut = isMac ? "⌘K" : "Ctrl+K";
    const btn      = document.createElement("button");
    btn.type       = "button";
    btn.className  = "okh-search-trigger";
    btn.setAttribute("aria-label", "Open search (" + shortcut + ")");
    btn.innerHTML = (
      '<svg class="okh-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />' +
      "</svg>" +
      '<span class="okh-search-label">Search</span>' +
      '<kbd>' + shortcut + '</kbd>'
    );
    btn.addEventListener("click", (e) => { e.preventDefault(); openFn(); });

    // Primary: prepend into .header-controls so search sits left of theme toggle
    const controls = document.querySelector(".header-controls");
    if (controls) {
      controls.insertBefore(btn, controls.firstChild);
      return;
    }
    // Fallbacks for pages without .header-controls
    const toggle = document.querySelector(".nav-toggle");
    if (toggle && toggle.parentNode) { toggle.parentNode.insertBefore(btn, toggle); return; }
    const hdr = document.querySelector(".site-header .container, .site-header");
    if (hdr) { hdr.appendChild(btn); return; }
    document.body.appendChild(btn);
  }

  // ── Dedicated /search/ page ─────────────────────────────────────────────
  function initInlineSearch() {
    const root  = document.querySelector("[data-glee-search-inline]");
    const input = root && root.querySelector("[data-glee-search-inline-input]");
    const list  = root && root.querySelector("[data-glee-search-inline-results]");
    const stats = root && root.querySelector("[data-glee-search-inline-status]");
    const cats  = root && root.querySelector("[data-glee-search-inline-categories]");
    if (!root || !input || !list) return;

    let entries        = [];
    let activeCategory = "all";

    function readQueryFromURL() {
      return new URL(window.location.href).searchParams.get("q") || "";
    }
    function writeQueryToURL(q) {
      const url = new URL(window.location.href);
      if (q) url.searchParams.set("q", q); else url.searchParams.delete("q");
      window.history.replaceState({}, "", url.toString());
    }

    function render() {
      const q = input.value.trim();
      writeQueryToURL(q);
      if (!q) {
        list.innerHTML = "";
        if (stats) stats.textContent = entries.length
          ? "Type to search " + entries.length + " indexed entries."
          : "Loading index…";
        return;
      }
      const tokens = tokenize(q);
      let results  = search(entries, q, 60);
      if (activeCategory !== "all") {
        results = results.filter((r) =>
          entrySection(r.entry).toLowerCase() === activeCategory.toLowerCase()
        );
      }
      if (!results.length) {
        list.innerHTML =
          '<div class="search-empty-state"><p>No matches for <strong>' +
          escapeHtml(q) + "</strong>" +
          (activeCategory !== "all" ? ' in <em>' + escapeHtml(activeCategory) + "</em>" : "") +
          ".</p></div>";
        if (stats) stats.textContent = "0 results";
        return;
      }
      if (stats) stats.textContent =
        results.length + " result" + (results.length === 1 ? "" : "s") +
        " for \u201c" + q + "\u201d";
      list.innerHTML = results.map((r) => (
        '<li><a class="okh-search-result" href="' + escapeHtml(r.entry.url) + '">' +
          renderResultHtml(r, tokens) +
        "</a></li>"
      )).join("");
    }

    function buildCategoryChips() {
      if (!cats) return;
      const counts = {};
      for (const e of entries) {
        const c = entrySection(e);
        counts[c] = (counts[c] || 0) + 1;
      }
      const ordered = ["all"].concat(Object.keys(counts).sort());
      cats.innerHTML = ordered.map((c) => {
        const label   = c === "all" ? "All (" + entries.length + ")" : c + " (" + counts[c] + ")";
        const pressed = c === activeCategory ? "true" : "false";
        return '<button type="button" data-cat="' + escapeHtml(c) +
               '" aria-pressed="' + pressed + '">' + escapeHtml(label) + "</button>";
      }).join("");
      cats.querySelectorAll("button").forEach((b) => {
        b.addEventListener("click", () => {
          activeCategory = b.getAttribute("data-cat") || "all";
          cats.querySelectorAll("button").forEach((x) =>
            x.setAttribute("aria-pressed", x === b ? "true" : "false")
          );
          render();
        });
      });
    }

    loadIndex().then((d) => {
      entries = d;
      buildCategoryChips();
      const initialQ = readQueryFromURL();
      if (initialQ) input.value = initialQ;
      render();
    });

    input.addEventListener("input", render);
    const form = root.querySelector("form");
    if (form) {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        render();
        input.focus();
      });
    }
  }

  // ── Bootstrap ────────────────────────────────────────────────────────────
  function start() {
    if (document.querySelector("[data-glee-search-inline]")) initInlineSearch();
    initOverlay();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
}());

// ── 7. Offline shell registration ───────────────────────────────────────────
// The worker handles only same-origin public shell resources and navigations.
(function () {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {
      // Offline support is progressive enhancement; normal browsing is unaffected.
    });
  });
}());

// ── 6. Sparkle banner loader ─────────────────────────────────────────────────
//  Fetches /assets/data/sparkle.json and updates every [data-sparkle-link]
//  element's href and text content so a single JSON edit propagates site-wide.
(function () {
  function applySparkle(data) {
    var links = document.querySelectorAll("[data-sparkle-link]");
    if (!links.length) return;
    var text =
      (data.emoji ? data.emoji + " " : "") +
      (data.label || "") +
      (data.description ? " \u2014 " + data.description : "") +
      (data.suffix ? " " + data.suffix : "");
    links.forEach(function (el) {
      if (data.url) el.href = data.url;
      if (text) el.textContent = text;
    });
  }

  fetch("/assets/data/sparkle.json")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) { if (data) applySparkle(data); })
    .catch(function () { /* silently keep static fallback */ });
}());
