// Full-screen image viewer for content images. GLightbox is loaded from the CDN
// ahead of this file (emitted when theme `lightbox: true`); we poll briefly for
// it, then bind. If it never loads the page is unchanged and images stay
// ordinary images, which is the same failure mode the carousel has.
//
// Binding is by DELEGATION rather than by wrapping each image in an anchor,
// which is what GLightbox's own docs suggest. Two reasons, both load bearing:
//
//   1. The carousel runs Swiper with `loop: true`, so Swiper CLONES slides.
//      Wrapping every `img` would put the same picture in the gallery two or
//      three times and the arrows would walk through duplicates.
//   2. Wrapping mutates the document after the fact, so anything that arrives
//      later (a clone, a lazily rendered block) is missed. A delegated click
//      handler covers whatever is on the page when the click happens.
(() => {
  "use strict";

  const OPT_OUT = ".no-lightbox, [data-lightbox='false']";
  // An icon or a badge is not a picture worth a full screen. Below this on
  // either axis, leave it alone.
  const MIN_EDGE = 96;

  const eligible = (img) => {
    if (!img || img.tagName !== "IMG") return false;
    if (img.closest(OPT_OUT)) return false;
    // An image that is already a link belongs to that link.
    const link = img.closest("a");
    if (link && !link.classList.contains("ms-shots__zoom")) return false;
    if (!img.currentSrc && !img.src) return false;
    const r = img.getBoundingClientRect();
    return r.width >= MIN_EDGE && r.height >= MIN_EDGE;
  };

  const src = (img) => img.currentSrc || img.src;

  // Every unique picture in the same carousel, in slide order, so the viewer's
  // arrows walk the gallery rather than dead-ending on one slide. Swiper's
  // duplicated slides are skipped by src, which also covers a carousel that
  // legitimately shows the same shot twice.
  const gallery = (img) => {
    const shots = img.closest(".swiper");
    if (!shots) return [img];
    const seen = new Set();
    const out = [];
    shots.querySelectorAll(".swiper-slide img").forEach((candidate) => {
      const key = src(candidate);
      if (!key || seen.has(key)) return;
      seen.add(key);
      out.push(candidate);
    });
    return out.length ? out : [img];
  };

  const caption = (img) => {
    const fig = img.closest("figure");
    const cap = fig && fig.querySelector("figcaption");
    return (cap && cap.textContent.trim()) || img.getAttribute("alt") || "";
  };

  const open = (img) => {
    const items = gallery(img);
    const target = src(img);
    let index = items.findIndex((candidate) => src(candidate) === target);
    if (index < 0) index = 0;
    const lb = window.GLightbox({
      // No zoom. The ask is to see the picture at full size, nothing more.
      zoomable: false,
      draggable: items.length > 1,
      loop: items.length > 1,
      touchNavigation: items.length > 1,
      openEffect: "fade",
      closeEffect: "fade",
      elements: items.map((candidate) => ({
        href: src(candidate),
        type: "image",
        description: caption(candidate),
      })),
      startAt: index,
    });
    lb.open();
    // Each open builds its own instance, so drop it once it closes rather than
    // leaving a stack of detached modals behind.
    lb.on("close", () => {
      window.setTimeout(() => lb.destroy(), 0);
    });
  };

  const onClick = (event) => {
    const img = event.target.closest("img");
    if (!eligible(img)) return;
    // A carousel arrow or pagination dot sits above the slide; let it win.
    if (event.target.closest(".swiper-button-prev, .swiper-button-next, .swiper-pagination")) return;
    event.preventDefault();
    open(img);
  };

  const mark = (root) => {
    root.querySelectorAll("img").forEach((img) => {
      if (eligible(img)) img.classList.add("ms-zoomable");
    });
  };

  const bind = () => {
    const roots = document.querySelectorAll("article, .md-content");
    if (!roots.length) return;
    roots.forEach((root) => {
      root.addEventListener("click", onClick);
      mark(root);
    });
    // Swiper mounts after this file runs and images decode later still, so the
    // affordance is re-applied once things settle. The click handler already
    // works regardless; this only keeps the cursor honest.
    window.setTimeout(() => roots.forEach(mark), 600);
    window.addEventListener("load", () => roots.forEach(mark), { once: true });
  };

  const start = (attempt = 0) => {
    if (typeof window.GLightbox === "function") {
      bind();
      return;
    }
    if (attempt > 40) return; // ~4s, then give up quietly
    window.setTimeout(() => start(attempt + 1), 100);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => start(), { once: true });
  } else {
    start();
  }
})();
