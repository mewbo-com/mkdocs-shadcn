# Video

A video in the content area plays while it is on screen and pauses when it
scrolls away, so a page of clips does not decode all of them at once.

<video src="../assets/video/sample.mp4" loop width="320"></video>

Autoplay requires a muted video, so the theme mutes any clip it starts — a
clip with meaningful audio should opt out with `data-no-autoplay` and keep
its own controls. A reader who has asked for reduced motion gets controls
instead of playback.

<video src="../assets/video/sample.mp4" loop width="320" data-no-autoplay controls></video>
