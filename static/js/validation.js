/* Клиентская валидация форм с атрибутом data-validate.
   Серверная валидация остаётся главной; здесь — быстрая подсказка пользователю.
   Поддерживаемые атрибуты полей:
     required            — обязательное поле
     data-min-age="18"   — дата рождения: возраст не меньше указанного
     data-match="id"     — значение должно совпадать с полем id (подтверждение пароля)
     data-after="id"     — дата не раньше даты в поле id
     pattern, min, max, type="email"
   Тексты сообщений берутся из #validation-messages (переводятся через i18n). */
(function () {
  "use strict";

  var box = document.getElementById("validation-messages");
  var messages = box ? box.dataset : {};
  function msg(key, fallback) { return messages[key] || fallback; }

  function ageFrom(isoDate) {
    var p = isoDate.split("-").map(Number);
    if (p.length !== 3 || p.some(isNaN)) { return null; }
    var now = new Date();
    var age = now.getFullYear() - p[0];
    var m = now.getMonth() + 1;
    if (m < p[1] || (m === p[1] && now.getDate() < p[2])) { age -= 1; }
    return age;
  }

  function validate(el) {
    var value = (el.value || "").trim();

    if (el.type === "checkbox") {
      return el.required && !el.checked ? msg("required", "Заполните это поле.") : "";
    }
    if (el.required && !value) { return msg("required", "Заполните это поле."); }
    if (!value) { return ""; }

    if (el.dataset.minAge) {
      var age = ageFrom(value);
      if (age === null || age < Number(el.dataset.minAge)) { return msg("adult", "Недопустимый возраст."); }
    }
    if (el.dataset.match) {
      var other = document.getElementById(el.dataset.match);
      if (other && other.value !== el.value) { return msg("match", "Значения не совпадают."); }
    }
    if (el.dataset.after) {
      var start = document.getElementById(el.dataset.after);
      if (start && start.value && value < start.value) { return msg("after", "Неверный период."); }
    }
    if (el.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      return msg("email", "Введите корректный email.");
    }
    if (el.getAttribute("pattern") && !new RegExp("^(?:" + el.getAttribute("pattern") + ")$").test(value)) {
      return msg("pattern", "Неверный формат.");
    }
    if (el.type === "number") {
      var n = Number(value);
      if (isNaN(n) || (el.min !== "" && n < Number(el.min)) || (el.max !== "" && n > Number(el.max))) {
        return msg("range", "Значение вне диапазона.");
      }
    }
    return "";
  }

  function show(el, message) {
    var holder = el.closest(".mb-3") || el.parentNode;
    holder.querySelectorAll(".invalid-feedback").forEach(function (node) { node.remove(); });
    el.classList.toggle("is-invalid", Boolean(message));
    if (message) {
      var div = document.createElement("div");
      div.className = "invalid-feedback d-block";
      div.textContent = message;
      holder.appendChild(div);
    }
  }

  function check(el) {
    var message = validate(el);
    show(el, message);
    return message === "";
  }

  document.querySelectorAll("form[data-validate]").forEach(function (form) {
    form.setAttribute("novalidate", "");
    var fields = form.querySelectorAll("input:not([type=hidden]):not([type=search]), select, textarea");

    fields.forEach(function (el) {
      el.addEventListener("blur", function () { if (el.value || el.classList.contains("is-invalid")) { check(el); } });
      el.addEventListener("change", function () { check(el); });
    });

    form.addEventListener("submit", function (event) {
      var firstInvalid = null;
      fields.forEach(function (el) {
        if (!check(el) && !firstInvalid) { firstInvalid = el; }
      });
      if (firstInvalid) {
        event.preventDefault();
        firstInvalid.focus();
      }
    });
  });
})();
