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
  const openSettings = document.getElementById('openCookieSettings');
  const status = document.getElementById('cookieStatus');

  function safeGet(key){
    try { return window.localStorage.getItem(key); } catch (err) { return null; }
  }

  function safeSet(key, value){
    try { window.localStorage.setItem(key, value); return true; } catch (err) { return false; }
  }

  function updateStatus(mode){
    if(!status) return;
    if(mode === 'accepted'){
      status.textContent = 'Non-essential cookies are enabled.';
    } else if(mode === 'rejected'){
      status.textContent = 'Non-essential cookies are disabled.';
    } else {
      status.textContent = 'No choice saved yet.';
    }
  }

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

  function hideBanner(){ if(banner){ banner.hidden = true; banner.setAttribute('aria-hidden','true'); } }
  function showBanner(){ if(banner){ banner.hidden = false; banner.setAttribute('aria-hidden','false'); } }

  function setPreference(mode){
    safeSet(storageKey, mode);
    applyConsent(mode);
    updateStatus(mode);
    hideBanner();
  }

  const current = safeGet(storageKey);
  if(current === 'accepted' || current === 'rejected'){
    applyConsent(current);
    updateStatus(current);
    hideBanner();
  } else {
    updateStatus(null);
    showBanner();
  }

  if(accept){
    accept.addEventListener('click', function(e){
      e.preventDefault();
      setPreference('accepted');
    });
  }
  if(reject){
    reject.addEventListener('click', function(e){
      e.preventDefault();
      setPreference('rejected');
    });
  }
  if(openSettings){
    openSettings.addEventListener('click', function(e){
      e.preventDefault();
      showBanner();
      banner && banner.scrollIntoView({behavior:'smooth', block:'nearest'});
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
