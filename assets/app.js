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

  function consentAccepted(){ return safeGet(storageKey) === 'accepted'; }

  // AdSense loads on every page (in the document head) and honours Consent Mode
  // via the gtag consent signal below — non-personalised ads until the visitor
  // accepts, personalised after. Only our own GA4 events wait for consent.
  function applyConsent(mode){
    const granted = mode === 'accepted';
    if(typeof gtag === 'function'){
      gtag('consent', 'update', {
        ad_storage: granted ? 'granted' : 'denied',
        analytics_storage: granted ? 'granted' : 'denied',
        ad_user_data: granted ? 'granted' : 'denied',
        ad_personalization: granted ? 'granted' : 'denied'
      });
    }
  }

  function hideBanner(){ if(banner){ banner.hidden = true; banner.setAttribute('aria-hidden','true'); } }
  function showBanner(){ if(banner){ banner.hidden = false; banner.setAttribute('aria-hidden','false'); } }

  function setPreference(mode){
    safeSet(storageKey, mode);
    applyConsent(mode);
    updateStatus(mode);
    hideBanner();
  }

  // Google's certified CMP (AdSense "Privacy & messaging") owns ad + analytics
  // consent via IAB TCF wherever it applies — it injects window.__tcfapi /
  // window.googlefc. When present, defer to it: keep our custom banner hidden
  // (no double prompt) and let the CMP drive Consent Mode. The custom banner is
  // the fallback only for visitors outside the CMP's regulated regions, where
  // Google's message isn't shown. Verify per-region behaviour in a preview.
  function googleCmpActive(){
    return typeof window.__tcfapi === 'function' ||
           (window.googlefc && typeof window.googlefc === 'object');
  }

  if(googleCmpActive()){
    hideBanner(); // Google's CMP is the consent surface here.
  } else {
    const current = safeGet(storageKey);
    if(current === 'accepted' || current === 'rejected'){
      applyConsent(current);
      updateStatus(current);
      hideBanner();
    } else {
      updateStatus(null);
      showBanner();
    }
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
      // Re-open Google's CMP where it manages consent; else our fallback banner.
      if(window.googlefc && typeof window.googlefc.showRevocationMessage === 'function'){
        window.googlefc.showRevocationMessage();
      } else {
        showBanner();
        banner && banner.scrollIntoView({behavior:'smooth', block:'nearest'});
      }
    });
  }

  document.addEventListener('click', function(e){
    const link = e.target.closest('a');
    if(!link || typeof gtag !== 'function' || !consentAccepted()) return;
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
          nlShow("Almost there — check your inbox and click the link to confirm your subscription.", 'success');
          if(typeof gtag === 'function' && consentAccepted()){
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
