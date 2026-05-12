// Mermaid diagram initialization for Glee-fully Personalizable Tools™
// Relies on YAML front-matter in each diagram for theme/look (theme: neutral, look: neo).
// initialize() intentionally omits themeVariables to avoid overriding the YAML config.
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  flowchart: {
    curve: "basis",
    nodeSpacing: 55,
    rankSpacing: 65,
    htmlLabels: true,
  },
});

// Explicit run — more reliable than startOnLoad with ES module loading order
mermaid.run({
  querySelector: ".mermaid",
}).then(() => {
  // Strip inline width/height/max-width that Mermaid injects on every SVG.
  // CSS !important on .glee-main .mermaid svg handles the cascade, but removing
  // the attributes also fixes any browser that applies SVG presentation
  // attributes above the CSS layer for width/height specifically.
  document.querySelectorAll(".mermaid svg").forEach((svg) => {
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    if (svg.style.maxWidth) svg.style.removeProperty("max-width");
  });
}).catch((err) => {
  console.warn("[mermaid-init] render error:", err);
});
