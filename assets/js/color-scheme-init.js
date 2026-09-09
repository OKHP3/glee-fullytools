// Apply a saved Glee-fully color preference before the first paint.
// This file is intentionally loaded without defer in document heads so the
// page never needs an inline executable script or script-src exception.
(function () {
  try {
    var savedScheme = localStorage.getItem("glee-color-scheme");
    if (savedScheme === "dark" || savedScheme === "light") {
      document.documentElement.setAttribute("data-color-scheme", savedScheme);
    }
  } catch (error) {
    // Disabled storage must not prevent the page from rendering.
  }
}());