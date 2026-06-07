---
title: Mewbo components
summary: Brand components consolidated into the theme — carousel, screenshot figure, device mockups, alternate-style tabs
---

This page exercises the Mewbo brand components that ship in the theme so a
consumer site gets them without forking: the image carousel, the captioned
screenshot figure, the device-mockup pair, and modern (`alternate_style`)
tabbed content. It doubles as the Playwright fixture for these features.

## Alternate-style tabs

These use `pymdownx.tabbed` with `alternate_style: true` (the modern,
accessible markup). The theme styles both this and the legacy markup.

=== "Alpha"

    Panel marker: **ALPHA_PANEL**. The first tab is open by default.

=== "Bravo"

    Panel marker: **BRAVO_PANEL**. Clicking this label reveals this panel.

=== "Charlie"

    Panel marker: **CHARLIE_PANEL**. A third panel to prove positional mapping.

## Image carousel

A `.swiper.ms-shots` block. The theme loads Swiper (CDN) and mounts it when
`theme.carousel` is true; the markup below is all a consumer writes.

<div class="swiper ms-shots">
  <div class="swiper-wrapper">
    <div class="swiper-slide">
      <figure>
        <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect width='800' height='600' fill='%23c46b48'/%3E%3Ctext x='400' y='320' font-size='64' fill='white' text-anchor='middle'%3ESlide 1%3C/text%3E%3C/svg%3E" alt="Slide 1">
        <figcaption>First slide</figcaption>
      </figure>
    </div>
    <div class="swiper-slide">
      <figure>
        <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect width='800' height='600' fill='%235b8a72'/%3E%3Ctext x='400' y='320' font-size='64' fill='white' text-anchor='middle'%3ESlide 2%3C/text%3E%3C/svg%3E" alt="Slide 2">
        <figcaption>Second slide</figcaption>
      </figure>
    </div>
    <div class="swiper-slide">
      <figure>
        <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect width='800' height='600' fill='%234a6fa5'/%3E%3Ctext x='400' y='320' font-size='64' fill='white' text-anchor='middle'%3ESlide 3%3C/text%3E%3C/svg%3E" alt="Slide 3">
        <figcaption>Third slide</figcaption>
      </figure>
    </div>
  </div>
  <div class="swiper-pagination"></div>
  <div class="swiper-button-prev"></div>
  <div class="swiper-button-next"></div>
</div>

## Screenshot figure

A bezel-framed, captioned screenshot (`.ms-shot`). The frame tint is the
`--ms-shot-frame` token.

<figure class="ms-shot">
  <div class="ms-shot__frame">
    <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='750'%3E%3Crect width='1200' height='750' fill='%23f5f3ef'/%3E%3Ctext x='600' y='390' font-size='56' fill='%23c46b48' text-anchor='middle'%3EApp screenshot%3C/text%3E%3C/svg%3E" alt="App screenshot">
  </div>
  <figcaption class="ms-shot__body">A captioned screenshot figure (<code>.ms-shot</code>).</figcaption>
</figure>

## Device mockups

A matched-height laptop + phone pair (`.ms-devices`). Widths come from the
`--ms-devices-primary` / `--ms-devices-secondary` tokens.

<div class="ms-devices">
  <img class="no-border" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1000' height='640'%3E%3Crect width='1000' height='640' rx='24' fill='%231f1d1a'/%3E%3Crect x='40' y='40' width='920' height='520' fill='%23c46b48'/%3E%3C/svg%3E" alt="Laptop">
  <img class="no-border" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='620'%3E%3Crect width='300' height='620' rx='40' fill='%231f1d1a'/%3E%3Crect x='20' y='60' width='260' height='500' fill='%235b8a72'/%3E%3C/svg%3E" alt="Phone">
  <p class="ms-devices__caption">Matched-height device mockups (<code>.ms-devices</code>).</p>
</div>
