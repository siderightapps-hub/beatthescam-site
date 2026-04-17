
(function(){
  const navToggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if(navToggle && nav){
    navToggle.addEventListener('click', function(){
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));
      nav.classList.toggle('is-open');
    });
  }

  const storageKey = 'bts_cookie_pref_v1';
  const banner = document.getElementById('cookieBanner');
  const accept = document.getElementById('cookieAccept');
  const reject = document.getElementById('cookieReject');

  function applyConsent(mode){
    if(typeof gtag !== 'function') return;
    const granted = mode === 'accepted';
    gtag('consent', 'update', {
      ad_storage: granted ? 'granted' : 'denied',
      analytics_storage: granted ? 'granted' : 'denied',
      ad_user_data: granted ? 'granted' : 'denied',
      ad_personalization: granted ? 'granted' : 'denied'
    });
  }

  function hideBanner(){ if(banner) banner.hidden = true; }
  function showBanner(){ if(banner) banner.hidden = false; }

  const current = localStorage.getItem(storageKey);
  if(current){
    applyConsent(current);
    hideBanner();
  } else {
    showBanner();
  }

  if(accept){
    accept.addEventListener('click', function(){
      localStorage.setItem(storageKey, 'accepted');
      applyConsent('accepted');
      hideBanner();
    });
  }
  if(reject){
    reject.addEventListener('click', function(){
      localStorage.setItem(storageKey, 'rejected');
      applyConsent('rejected');
      hideBanner();
    });
  }

  document.addEventListener('click', function(e){
    const link = e.target.closest('a');
    if(!link || typeof gtag !== 'function') return;
    if(link.hostname && link.hostname !== window.location.hostname){
      gtag('event', 'outbound_click', {
        event_category: 'engagement',
        event_label: link.href,
        transport_type: 'beacon'
      });
    }
  });
})();
