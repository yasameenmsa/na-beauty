(function () {
  "use strict";

  /* ---- Mobile Navigation ---- */
  var toggle = document.getElementById("navToggle");
  var mobile = document.getElementById("navMobile");

  function openNav() {
    toggle.classList.add("active");
    toggle.setAttribute("aria-expanded", "true");
    mobile.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeNav() {
    toggle.classList.remove("active");
    toggle.setAttribute("aria-expanded", "false");
    mobile.classList.remove("active");
    document.body.style.overflow = "";
  }

  toggle.addEventListener("click", function () {
    mobile.classList.contains("active") ? closeNav() : openNav();
  });

  document.querySelectorAll("[data-nav-close]").forEach(function (link) {
    link.addEventListener("click", closeNav);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && mobile.classList.contains("active")) {
      closeNav();
    }
  });

  /* ---- Nav Background on Scroll ---- */
  var nav = document.querySelector("nav");
  var ticking = false;

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(function () {
        nav.style.background =
          window.scrollY > 60
            ? "rgba(26,23,16,0.97)"
            : "linear-gradient(to bottom, rgba(26,23,16,0.95) 0%, transparent 100%)";
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });

  /* ---- Smooth Scroll for Anchor Links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      var target = document.querySelector(this.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
})();
