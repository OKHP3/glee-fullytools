// Mermaid initialization — shared module across overkillhill.com,
// glee-fully.tools, and askjamie.bot.
// Relies on YAML front-matter in each diagram for theme/look (theme: neutral, look: neo).
//
// Dark mode: themeVariables are resolved at render time so Mermaid bakes the
// correct line/node colours into the SVG's own <style> block.  External CSS
// cannot reliably override those inline SVG styles, so we pass them here.
//
// Performance: on pages with many diagrams (e.g. the v0.3 article) we use
// IntersectionObserver to defer rendering until each diagram approaches the
// viewport. Falls back to immediate render where the API is unavailable.
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

// ── Dark-mode detection ────────────────────────────────────────────────────
// Glee uses data-color-scheme attr + glee-color-scheme localStorage.
// AskJamie / OKH use the same attr convention.
function resolveIsDark() {
  const attr = document.documentElement.getAttribute("data-color-scheme");
  if (attr === "dark")  return true;
  if (attr === "light") return false;
  // Attr absent → follow OS
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

// ── Site-specific themeVariables ───────────────────────────────────────────
function resolveThemeVariables(isDark) {
  const isGlee     = document.body.classList.contains("glee-main");
  const isAskJamie = document.body.classList.contains("askjamie-main");

  if (isDark) {
    if (isGlee) {
      return {
        background:          "#1a1210",
        primaryColor:        "#241c1a",
        primaryTextColor:    "#f0e8e0",
        primaryBorderColor:  "#f07585",
        lineColor:           "#f07585",
        secondaryColor:      "#2e2220",
        tertiaryColor:       "#2e2220",
        edgeLabelBackground: "#241c1a",
        clusterBkg:          "#1a1210",
        clusterBorder:       "#f07585",
      };
    }
    if (isAskJamie) {
      return {
        background:          "#0d1f23",
        primaryColor:        "#112a30",
        primaryTextColor:    "#e0f0f3",
        primaryBorderColor:  "#3d9aad",
        lineColor:           "#3d9aad",
        secondaryColor:      "#0d2228",
        tertiaryColor:       "#0d2228",
        edgeLabelBackground: "#112a30",
      };
    }
    // OKH / default dark
    return {
      background:          "#0d1117",
      primaryColor:        "#111827",
      primaryTextColor:    "#e5e7eb",
      primaryBorderColor:  "#c46a2c",
      lineColor:           "#c46a2c",
      secondaryColor:      "#181f26",
      tertiaryColor:       "#1c3a34",
      edgeLabelBackground: "#181f26",
    };
  }

  // Light mode — per-brand
  if (isGlee) {
    return {
      background:          "#f6f2ee",
      primaryColor:        "#fffdfa",
      primaryTextColor:    "#2e2b29",
      primaryBorderColor:  "#d94f63",
      lineColor:           "#d94f63",
      secondaryColor:      "#f6f2ee",
      tertiaryColor:       "#e5d9ce",
      edgeLabelBackground: "#fff7f1",
    };
  }
  if (isAskJamie) {
    return {
      background:          "#f4fbfc",
      primaryColor:        "#fdfbf7",
      primaryTextColor:    "#1a3038",
      primaryBorderColor:  "#2d6f7e",
      lineColor:           "#2d6f7e",
      secondaryColor:      "#f6f2ee",
      tertiaryColor:       "#e1ecef",
      edgeLabelBackground: "#f6f2ee",
    };
  }
  // OKH default — let YAML front-matter override
  return undefined;
}

// ── Initialise ─────────────────────────────────────────────────────────────
const isDark = resolveIsDark();
const themeVars = resolveThemeVariables(isDark);

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  ...(themeVars ? { theme: "base", themeVariables: themeVars } : {}),
  flowchart: {
    curve: "basis",
    nodeSpacing: 55,
    rankSpacing: 65,
    htmlLabels: true,
  },
});

const diagrams = Array.from(document.querySelectorAll(".mermaid"));

function renderOne(node) {
  if (node.dataset.mermaidRendered === "1") return;
  node.dataset.mermaidRendered = "1";
  mermaid.run({ nodes: [node] }).catch((err) => {
    console.warn("[mermaid-init] render error:", err);
  });
}

// If only a few diagrams, or no IntersectionObserver, render immediately.
if (diagrams.length <= 2 || typeof IntersectionObserver === "undefined") {
  diagrams.forEach(renderOne);
} else {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          renderOne(entry.target);
          io.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "400px 0px", threshold: 0.01 }
  );
  diagrams.forEach((node) => io.observe(node));
}
