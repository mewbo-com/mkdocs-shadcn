(() => {
  const COPY_STATE = 'data-copy-state';

  async function writeClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand('copy');
    document.body.removeChild(textarea);
    if (!copied) {
      throw new Error('Clipboard copy was rejected');
    }
  }

  function findCopyButton() {
    return document.querySelector('#page-header [data-copy-markdown]');
  }

  function setState(button, state) {
    button.setAttribute(COPY_STATE, state);
    const label = state === 'copied' ? button.dataset.copiedLabel
      : state === 'failed' ? button.dataset.copyFailedLabel : button.dataset.copyLabel;
    if (label) {
      const span = button.querySelector('span');
      if (span) span.textContent = label;
      button.setAttribute('aria-label', label);
    }
    // Both 'copied' and 'failed' are transient acknowledgements, not modes.
    // Without this the button keeps saying "Copied" forever and a second copy
    // gives no feedback at all, because the label never changed back.
    if (state !== 'ready') {
      clearTimeout(button._copyResetTimer);
      button._copyResetTimer = setTimeout(() => setState(button, 'ready'), 2000);
    }
  }

  function bindCopyHandler(button) {
    setState(button, 'ready');
    button.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      try {
        const markdown = button.dataset.copyMarkdown;
        if (markdown === undefined) {
          throw new Error('No page Markdown was emitted');
        }
        await writeClipboard(markdown);
        setState(button, 'copied');
      } catch (error) {
        setState(button, 'failed');
        console.warn('Copy page markdown failed:', error);
      }
    });
  }

  /* The disclosure menu beside the copy button. Only present when the site
     sets `repo_url` — every item in it needs a URL for the page source — so
     everything here no-ops on a site without one. */
  function bindMenu(root, copyButton) {
    const toggle = root.querySelector('[data-mewbo-page-actions-toggle]');
    const menu = root.querySelector('[data-mewbo-page-actions-menu]');
    if (!toggle || !menu) return;

    const setOpen = (open) => {
      menu.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      root.toggleAttribute('data-open', open);
    };

    toggle.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      setOpen(menu.hidden);
    });

    // The menu item that duplicates the main button. It delegates rather than
    // re-implementing the copy so there is one clipboard path and one place
    // the "Copied" acknowledgement is produced.
    const proxy = menu.querySelector('[data-mewbo-copy-proxy]');
    if (proxy && copyButton) {
      proxy.addEventListener('click', (event) => {
        event.preventDefault();
        copyButton.click();
        setOpen(false);
      });
    }

    // A menu that swallows the next click anywhere, or traps focus with no way
    // back, is worse than no menu. Close on outside click, on Escape, and
    // whenever a link inside it is followed.
    document.addEventListener('click', (event) => {
      if (!menu.hidden && !root.contains(event.target)) setOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !menu.hidden) {
        setOpen(false);
        toggle.focus();
      }
    });
    menu.querySelectorAll('a[role="menuitem"]').forEach((link) => {
      link.addEventListener('click', () => setOpen(false));
    });
  }

  function initCopyButton() {
    const button = findCopyButton();
    if (button) {
      bindCopyHandler(button);
    }
    const root = document.querySelector('[data-mewbo-page-actions]');
    if (root) {
      bindMenu(root, button);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopyButton);
  } else {
    initCopyButton();
  }
})();
