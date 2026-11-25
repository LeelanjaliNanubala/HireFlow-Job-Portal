/* HireFlow site-wide behaviour: confirmation prompts, loading buttons, auto-hiding alerts. */
document.addEventListener('DOMContentLoaded', function () {
  // 1. Confirmation prompt: <form data-confirm="Are you sure?">
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.getAttribute('data-confirm'))) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    });
  });

  // 2. Loading state: show a spinner on the submit button while the page is sending.
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (event.defaultPrevented) { return; }
      var button = form.querySelector('button[type="submit"]:not([data-no-loading])');
      if (!button) { return; }
      setTimeout(function () {
        button.classList.add('is-loading');
        button.setAttribute('aria-busy', 'true');
        var label = button.getAttribute('data-loading-text') || 'Please wait...';
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' + label;
      }, 0);
    });
  });

  // 3. Success/info alerts disappear after a few seconds.
  document.querySelectorAll('.alert-success, .alert-info').forEach(function (alert) {
    setTimeout(function () {
      if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(alert).close(); }
    }, 6000);
  });
});
