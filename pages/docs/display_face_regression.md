---
title: Display face regression
summary: Regression fixture — which text wears the serif display face, and which does not
---

This page checks the theme's editorial type roles. Instrument Serif names
sections and cards. Newsreader carries paragraphs and navigation links.
Compact controls and API symbols keep Geist, and code keeps Geist Mono.

Each role loads from the theme's own font files. No font service is needed
when a reader opens the site.

## A section heading takes the serif

Body copy uses Newsreader at a comfortable reading size and leading. The
display face names the section without borrowing the paragraph's weight.

### A subsection heading takes it too

Deep headings keep the technical face so small labels remain easy to scan.

#### A fourth-level heading must stay sans

##### A fifth-level heading must stay sans

## Code inside a heading keeps the mono face: `get_config(**kwargs)`

A code span names a symbol, and a symbol set in a serif is a symbol dressed as
prose. Inline code retains its own mono stack even inside a display heading.

## Cards

<div class="ms-grid ms-grid--3">
  <div class="ms-card">
    <span class="ms-card__title">Android</span>
    <span class="ms-card__body">A card title names the thing the card is
    about — the same job a heading does — so it takes the display face. This
    body copy does not.</span>
  </div>
  <div class="ms-card">
    <span class="ms-card__title">iOS</span>
    <span class="ms-card__body">Second card, so the test can confirm the rule
    applies to every card rather than to the first one only.</span>
  </div>
</div>

## Lifecycle steps

The numbered lifecycle is a SECOND card family with its own class names. It is
here because styling `.ms-card__title` alone silently left `.ms-step__title`
behind on a real site — the two look like siblings and are not.

<div class="ms-lifecycle">
  <div class="ms-step">
    <p class="ms-step__title">Install</p>
    <div class="ms-step__links">
      <p class="ms-card__body">A step title names the step, so it takes the
      display face. This body copy does not.</p>
    </div>
  </div>
  <div class="ms-step">
    <p class="ms-step__title">Configure</p>
    <div class="ms-step__links">
      <p class="ms-card__body">Second step, so the rule is shown to apply to
      every step rather than to the first one only.</p>
    </div>
  </div>
</div>

## The hero

The hero title takes the display face. Its lede uses the reading face, while
the eyebrow stays a compact interface label.

<div class="ms-hero">
  <p class="ms-hero__eyebrow">Eyebrow · stays on the sans</p>
  <h1 class="ms-hero__title">A hero title takes the display face</h1>
  <p class="ms-hero__lede">The lede is a paragraph, read line after line, so it
  stays on the body face like any other prose.</p>
</div>
