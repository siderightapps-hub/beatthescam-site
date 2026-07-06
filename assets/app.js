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

  // Best-effort signal: does UK/EEA data-protection law (and thus the IAB TCF)
  // apply to this visitor? null = unknown. Populated from the TCF stub below.
  // The custom fallback banner must NEVER grant TCF-scope advertising consent
  // on its own — that consent is only valid from Google's certified CMP. So we
  // upgrade advertising signals via the fallback ONLY when we can positively
  // confirm GDPR does not apply; otherwise ads stay non-personalised until the
  // certified CMP supplies a valid TC string (which drives Consent Mode itself).
  var gdprApplies = null;

  // AdSense loads on every page (in the document head) and honours Consent Mode
  // via the gtag consent signal below. Analytics consent comes from this banner
  // (or the CMP); advertising consent only upgrades when GDPR provably does not
  // apply here, or when the certified CMP grants it.
  function applyConsent(mode){
    const granted = mode === 'accepted';
    // Only grant advertising consent through this fallback for confirmed non-GDPR
    // visitors. In the UK/EEA (gdprApplies === true) or when the region is unknown
    // (null), advertising stays denied → non-personalised ads, no ad cookies.
    const adGranted = granted && gdprApplies === false;
    if(typeof gtag === 'function'){
      gtag('consent', 'update', {
        ad_storage: adGranted ? 'granted' : 'denied',
        ad_user_data: adGranted ? 'granted' : 'denied',
        ad_personalization: adGranted ? 'granted' : 'denied',
        analytics_storage: granted ? 'granted' : 'denied'
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

  // Defer to Google's certified CMP (AdSense "Privacy & messaging") ONLY when it
  // genuinely runs — i.e. it shows its message or yields a real TC decision —
  // NOT merely when the __tcfapi/googlefc stub is present. The stub can load
  // while AdSense / the message isn't serving yet (e.g. before AdSense is
  // approved), and trusting its mere presence would leave the page with NO
  // consent UI at all. So: default to our own banner, and hide it only once a
  // TCF CMP actually takes over. This self-corrects when AdSense goes live.
  var cmpTookOver = false;
  function deferToCmp(){
    if(cmpTookOver) return;
    cmpTookOver = true;
    hideBanner();
  }

  // Custom-banner fallback — the consent surface wherever Google's CMP isn't
  // actively shown (non-regulated regions, or before the CMP is live).
  function showFallbackBanner(){
    if(cmpTookOver) return;
    var current = safeGet(storageKey);
    if(current === 'accepted' || current === 'rejected'){
      applyConsent(current);
      updateStatus(current);
      hideBanner();
    } else {
      updateStatus(null);
      showBanner();
    }
  }

  // AdSense installs window.__tcfapi via an async <script> tag (see base.html),
  // which can finish loading AFTER this deferred script runs — a single
  // "typeof === 'function'" check here would then never register the listener
  // below, so a CMP that shows up a moment later displays its own message on
  // top of our fallback banner (the double-prompt this design exists to
  // avoid). Poll briefly instead of checking once. This is safe to keep trying
  // even after the fallback timeout below has fired: deferToCmp() hides an
  // already-shown fallback banner the moment the CMP actually takes over.
  function registerTcfListener(){
    try {
      window.__tcfapi('addEventListener', 2, function(tcData, success){
        if(!success || !tcData) return;
        // Record whether GDPR/TCF applies so the fallback banner knows whether it
        // may grant advertising consent (only when this is strictly false).
        if(typeof tcData.gdprApplies === 'boolean'){ gdprApplies = tcData.gdprApplies; }
        if(tcData.eventStatus === 'cmpuishown' ||
           tcData.eventStatus === 'useractioncomplete' ||
           (tcData.gdprApplies === true && tcData.tcString)){
          deferToCmp();
        }
      });
    } catch(e){ /* malformed stub — fall through to our own banner */ }
  }
  (function pollForTcf(attemptsLeft){
    if(typeof window.__tcfapi === 'function'){
      registerTcfListener();
      return;
    }
    if(attemptsLeft > 0){
      setTimeout(function(){ pollForTcf(attemptsLeft - 1); }, 500);
    }
  })(16); // ~8s of retries — generous enough for a slow-loading AdSense script

  // If a real CMP hasn't taken over shortly, show our own banner as the consent UI.
  setTimeout(function(){ if(!cmpTookOver){ showFallbackBanner(); } }, 2000);

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
      // Re-open Google's CMP only when it actually manages consent here; else
      // show our own banner (the active consent surface in this region/state).
      if(cmpTookOver && window.googlefc && typeof window.googlefc.showRevocationMessage === 'function'){
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
