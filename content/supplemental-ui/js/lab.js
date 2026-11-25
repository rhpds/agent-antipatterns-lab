(function () {
  'use strict';
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
    overlay.appendChild(svg.cloneNode(true));
    document.body.appendChild(overlay);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') close();
  });
})();
