---
title: Display face regression
summary: Regression fixture — which text wears the serif display face, and which does not
---

This page is a regression fixture for the IBM Plex Serif display face. It
exists to pin the BOUNDARY: headings and card titles take the serif, while
body copy, deep headings, code spans and API symbols stay on the sans.

The interesting cases are the ones that must NOT change, because a broadened
selector is silent — nothing errors, the page simply starts reading wrong.

## A section heading takes the serif

Body copy under it stays on the sans face. That contrast is the whole point of
the treatment: a heading should announce a section on shape alone, before its
size or weight registers.

### A subsection heading takes it too

H3 is the floor. Below it the type is close enough to body size that a serif
reads as a font bug rather than as a deliberate choice.

#### A fourth-level heading must stay sans

##### A fifth-level heading must stay sans

## Code inside a heading keeps the mono face: `get_config(**kwargs)`

A code span names a symbol, and a symbol set in a serif is a symbol dressed as
prose. `article code:not(pre code)` and the heading rule reach the same
specificity, so without an explicit rule the heading would win on source order
and swallow the code span.

## Cards

<div class="ms-cards">
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

## Compositions that opt out

<div class="ms-hero">
  <h1>A hero heading stays on the sans</h1>
  <p>The hero is brand composition with its own type treatment, so it is
  excluded by name rather than inheriting the prose rule.</p>
</div>
