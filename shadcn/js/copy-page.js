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

  function initCopyButton() {
    const button = findCopyButton();
    if (button) {
      bindCopyHandler(button);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopyButton);
  } else {
    initCopyButton();
  }
})();
