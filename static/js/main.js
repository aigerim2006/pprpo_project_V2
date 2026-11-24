/* Переключение светлой/тёмной темы (выбор хранится в localStorage). */
(function () {
  "use strict";
  var KEY = "ais-theme";
  var root = document.documentElement;
  var button = document.getElementById("themeToggle");
  if (!button) { return; }

  button.addEventListener("click", function () {
    var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-bs-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) { /* хранилище недоступно */ }
  });
})();
