document.addEventListener('DOMContentLoaded', function () {
  const popoverBtn = document.getElementById('popoverBtn');

  if (!popoverBtn) return; // Exit if button not found (i.e., not on the 'text' tab page)

  const popover = new bootstrap.Popover(popoverBtn, {
    html: true,
    trigger: 'manual',
    customClass: 'custom-popover',
    content: `
<pre>RA              DEC
000000.000      +-000000.00
12h34m56.7s     -76d54m32.1s
12h 34m 56.7s   -76d 54m 32.1s
12h34m56s       -65d43m21s
12h 34m 56s     -65d 43m 21s
12h34.5m         54d32.1m
12h 34m         +54d 32m
12.5h            54.3d
12h             +54d
12h34m56.7      -76d54m32.1
12h 34m 56.7    -76d 54m 32.1
12h34m56        -65d43m21
12h 34m 56      -65d 43m 21
12h34.5          54d32.1
12h34           +54d32
12h 34          +54d 32
12:34:56.7      -76:54:32.1
12:34:56         65:43:21
12:34.5         +54:32.1
123.4            54.3
123             -54 </pre>
    `
  });

  let isPopoverShown = false;

  function showPopover() {
    if (!isPopoverShown) {
      popover.show();
      popoverBtn.classList.add('active');
      isPopoverShown = true;
    }
  }

  function hidePopover() {
    if (isPopoverShown) {
      popover.hide();
      popoverBtn.classList.remove('active');
      isPopoverShown = false;
    }
  }

  function updatePopoverBasedOnTab(activeTabId) {
    if (activeTabId === 'text') {
      showPopover();
    } else {
      hidePopover();
    }
  }

  // Toggle manually via click
  popoverBtn.addEventListener('click', () => {
    if (isPopoverShown) {
      hidePopover();
    } else {
      showPopover();
    }
  });

  // Listen for Bootstrap tab changes
  const tabLinks = document.querySelectorAll('.nav-tabs .nav-link');
  tabLinks.forEach(link => {
    link.addEventListener('shown.bs.tab', event => {
      const href = event.target.getAttribute('data-bs-target'); // e.g. "#text"
      const activeTabId = href ? href.replace('#', '') : '';
      updatePopoverBasedOnTab(activeTabId);
    });
  });

  // Initial check this after the DOM is ready
  const activeLink = document.querySelector('.nav-tabs .nav-link.active');
  if (activeLink) {
    const initialTabId = activeLink.getAttribute('data-bs-target').replace('#', '');
    updatePopoverBasedOnTab(initialTabId);
  }

});
