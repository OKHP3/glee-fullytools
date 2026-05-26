/**
 * sparkle-loader.js
 * Populates the "Today's Sparkle" banner from assets/data/sparkle.json.
 * Falls back silently to static HTML if fetch fails (offline / slow).
 * To update the banner site-wide: edit assets/data/sparkle.json only.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var link = document.querySelector('[data-sparkle-link]');
    if (!link) return;

    fetch('/assets/data/sparkle.json?v=' + Date.now())
      .then(function (res) {
        if (!res.ok) throw new Error('sparkle fetch failed');
        return res.json();
      })
      .then(function (data) {
        link.textContent =
          data.emoji + '\u00a0' + data.label + '\u00a0\u2014\u00a0' +
          data.description + '\u00a0' + data.suffix;
        link.href = data.url;
      })
      .catch(function () {
        /* fail silently — static banner text remains visible */
      });
  });
})();
