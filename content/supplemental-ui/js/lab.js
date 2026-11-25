(function () {
  'use strict';
  // Mermaid draws diagrams after the page loads and scales them down to the
  // pane's width, which leaves the text too small to read in Showroom's narrow
  // instructions pane. Give each diagram its natural size instead; the
  // container scrolls sideways when it's wider than the pane.
  function naturalSize(svg) {
    if (svg.dataset.labSized) return;
    var box = svg.viewBox && svg.viewBox.baseVal;
    if (!box || !box.width) return;
    svg.style.width = box.width + 'px';
    svg.style.height = box.height + 'px';
    svg.dataset.labSized = 'true';
    var diagram = svg.closest('.mermaid');
    if (diagram.scrollWidth > diagram.clientWidth && !diagram.nextElementSibling?.classList.contains('lab-diagram-hint')) {
      var hint = document.createElement('p');
      hint.className = 'lab-diagram-hint';
      hint.textContent = 'Scroll sideways, or click the diagram to see it full screen.';
      diagram.after(hint);
    }
  }
  function sizeAll() {
    document.querySelectorAll('.doc .mermaid svg').forEach(naturalSize);
  }
  new MutationObserver(sizeAll).observe(document.documentElement, { childList: true, subtree: true });
  sizeAll();

  // Click a diagram to see it full screen; click again or press Escape to close.
  function close() {
    var open = document.querySelector('.lab-diagram-overlay');
    if (open) open.remove();
  }
  document.addEventListener('click', function (event) {
    if (event.target.closest('.lab-diagram-overlay')) { close(); return; }
    var diagram = event.target.closest('.doc .mermaid');
    var svg = diagram && diagram.querySelector('svg');
    if (!svg) return;
    var overlay = document.createElement('div');
    overlay.className = 'lab-diagram-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Diagram, full screen. Click or press Escape to close.');
    var copy = svg.cloneNode(true);
    copy.style.width = '';
    copy.style.height = '';
    overlay.appendChild(copy);
    document.body.appendChild(overlay);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') close();
  });
})();
