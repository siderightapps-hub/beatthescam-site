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

  // ─── NEWSLETTER SIGNUP ────────────────────────────────────────────────────
  const nlForm = document.getElementById('nl-form');
  if(nlForm){
    const nlEmail   = document.getElementById('nl-email');
    const nlConsent = document.getElementById('nl-consent');
    const nlWebsite = document.getElementById('nl-website');
    const nlSubmit  = document.getElementById('nl-submit');
    const nlMsg     = document.getElementById('nl-msg');
    const EMAIL_RE  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function nlShow(text, kind){
      if(!nlMsg) return;
      nlMsg.textContent = text;
      nlMsg.classList.remove('is-error','is-success');
      if(kind){ nlMsg.classList.add(kind === 'error' ? 'is-error' : 'is-success'); }
    }

    nlForm.addEventListener('submit', function(e){
      e.preventDefault();
      const email = ((nlEmail && nlEmail.value) || '').trim();
      const consent = !!(nlConsent && nlConsent.checked);

      if(!EMAIL_RE.test(email)){
        nlShow('Please enter a valid email address.', 'error');
        if(nlEmail) nlEmail.focus();
        return;
      }
      if(!consent){
        nlShow('Please tick the box to confirm you agree.', 'error');
        return;
      }

      if(nlSubmit){ nlSubmit.disabled = true; nlSubmit.textContent = 'Subscribing…'; }
      nlShow('', null);

      fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          consent: consent,
          website: (nlWebsite && nlWebsite.value) || ''
        })
      }).then(function(res){
        return res.json().catch(function(){ return {}; }).then(function(data){
          return { ok: res.ok, data: data };
        });
      }).then(function(r){
        if(r.ok){
          nlForm.reset();
          nlShow("You're in. Check your inbox for a welcome email.", 'success');
          if(typeof gtag === 'function'){
            gtag('event', 'newsletter_signup', { event_category: 'engagement' });
          }
        } else {
          nlShow((r.data && r.data.error) || 'Something went wrong. Please try again.', 'error');
        }
      }).catch(function(){
        nlShow('Network error. Please try again in a moment.', 'error');
      }).finally(function(){
        if(nlSubmit){ nlSubmit.disabled = false; nlSubmit.textContent = 'Subscribe'; }
      });
    });
  }
})();
