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
    var next = diagram.nextElementSibling;
    if (diagram.scrollWidth > diagram.clientWidth && !(next && next.classList.contains('lab-diagram-hint'))) {
      var hint = document.createElement('p');
      hint.className = 'lab-diagram-hint';
      hint.textContent = 'Scroll sideways to see the whole diagram.';
      diagram.after(hint);
    }
  }
  var observer = new MutationObserver(function () {
    var diagrams = document.querySelectorAll('.doc .mermaid');
    document.querySelectorAll('.doc .mermaid svg').forEach(naturalSize);
    // Stop watching once every diagram on the page has been sized.
    if (document.querySelectorAll('.doc .mermaid svg[data-lab-sized]').length === diagrams.length) {
      observer.disconnect();
    }
  });
  if (document.querySelector('.doc .mermaid')) {
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
