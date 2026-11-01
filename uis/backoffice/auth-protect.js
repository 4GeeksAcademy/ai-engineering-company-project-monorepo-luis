// auth-protect.js – ensures a page is only visible to authenticated users

(function () {
  // Wait until DOM is ready
  function onReady(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  onReady(() => {
    if (!window.inventoryApi || !window.inventoryApi.isAuthenticated()) {
      // Open login modal; once login succeeds, the page will reload implicitly via the auth UI
      if (typeof openLoginModal === 'function') {
        openLoginModal();
      }
    }
  });
})();

