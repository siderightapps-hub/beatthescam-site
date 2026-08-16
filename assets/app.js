(function(){
  const navToggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if(navToggle && nav){
    // #site-nav sits BEFORE .nav-toggle in the document, because the checker
    // CTA has to live outside the element that collapses. That means the panel
    // precedes its own trigger in sequential focus order: without moving focus
    // on open, Tab from the toggle goes forward into <main> and the reader has
    // to Shift-Tab backwards past the CTA to reach the links they just opened.
    function setNav(open){
      navToggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
      if(open){
        const first = nav.querySelector('a[href]');
        if(first){ try { first.focus(); } catch (err) { /* not focusable */ } }
      }
    }
    function closeNav(restoreFocus){
      if(!nav.classList.contains('is-open')) return;
      setNav(false);
      if(restoreFocus){ try { navToggle.focus(); } catch (err) { /* gone */ } }
    }

    navToggle.addEventListener('click', function(){
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      if(expanded){ closeNav(true); } else { setNav(true); }
    });

    // Escape closes and hands focus back to the button that opened it.
    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape' || e.key === 'Esc'){ closeNav(true); }
    });

    // A click or a tab-out beyond the header dismisses the panel, but must not
    // steal focus back to the toggle — the reader has deliberately moved on.
    document.addEventListener('click', function(e){
      if(nav.contains(e.target) || navToggle.contains(e.target)) return;
      closeNav(false);
    });
    document.addEventListener('focusin', function(e){
      if(nav.contains(e.target) || navToggle.contains(e.target)) return;
      closeNav(false);
    });
  }

  const storageKey = 'bts_cookie_pref_v1';
  const banner = document.getElementById('cookieBanner');
  const accept = document.getElementById('cookieAccept');
  const reject = document.getElementById('cookieReject');
  const openSettings = document.getElementById('openCookieSettings');

  function safeGet(key){
    try { return window.localStorage.getItem(key); } catch (err) { return null; }
  }

  function safeSet(key, value){
    try { window.localStorage.setItem(key, value); return true; } catch (err) { return false; }
  }

  function consentAccepted(){
    if(safeGet(storageKey) === 'accepted') return true;
    // Google's certified CMP writes Consent Mode updates through gtag rather
    // than our fallback preference key. Read the latest analytics_storage
    // decision so CMP-consented visitors are measured too, while a denial (or
    // no decision yet) continues to suppress custom events.
    var dl = window.dataLayer || [];
    for(var i = dl.length - 1; i >= 0; i--){
      var item = dl[i];
      if(item && item[0] === 'consent' && item[1] === 'update' && item[2] &&
         typeof item[2].analytics_storage === 'string'){
        return item[2].analytics_storage === 'granted';
      }
    }
    return false;
  }

  // One consent-aware analytics gateway for every conversion surface. Event
  // payloads must never include checker text, email addresses, or other user
  // input. GA4 intentionally under-counts visitors who decline analytics.
  function trackEvent(name, params){
    if(typeof gtag !== 'function' || !consentAccepted()) return false;
    gtag('event', name, params || {});
    return true;
  }
  window.btsTrackEvent = trackEvent;

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

  // The banner is position:fixed, so while it shows it sits over the end of the
  // page — the footer's Trust & legal links and the Cookie settings button that
  // reopens it. Reserve exactly the height it occupies (bar + its bottom inset)
  // as body padding so that content stays reachable, and release it on dismissal.
  // Two fixed bars can occupy the bottom: the consent bar and the mobile action
  // bar. They are mutually exclusive by design (consent suppresses the actions),
  // so the reserved space is whichever one is actually on screen.
  function syncConsentOffset(){
    const root = document.documentElement;
    const actions = document.getElementById('mobileActions');
    let visible = null;
    if(banner && !banner.hidden){
      visible = banner;
    } else if(actions && actions.classList.contains('is-visible') &&
              getComputedStyle(actions).display !== 'none'){
      visible = actions;
    }
    if(!visible){
      root.style.removeProperty('--consent-offset');
      return;
    }
    // offsetHeight and the computed `bottom`, not getBoundingClientRect: the
    // action bar slides in on a transform, and a rect read mid-transition
    // reports the off-screen position and under-reserves the space.
    const inset = parseFloat(getComputedStyle(visible).bottom) || 0;
    root.style.setProperty('--consent-offset',
      Math.ceil(visible.offsetHeight + inset * 2) + 'px');
  }

  // Where focus was before the bar took it, so dismissing returns the reader
  // to what they were doing rather than dropping them at the top of the page.
  var focusBeforeBanner = null;
  // Set by the mobile action bar below, so consent showing or being dismissed
  // re-evaluates whether the action bar should be on screen.
  var consentChanged = null;

  function hideBanner(){
    if(!banner) return;
    var hadFocus = banner.contains(document.activeElement);
    banner.hidden = true;
    banner.setAttribute('aria-hidden','true');
    var live = document.getElementById('liveStatus');
    if(live){ live.textContent = ''; }
    if(consentChanged) consentChanged();
    syncConsentOffset();
    if(hadFocus && focusBeforeBanner && document.contains(focusBeforeBanner)){
      try { focusBeforeBanner.focus(); } catch (err) { /* element went away */ }
    }
    focusBeforeBanner = null;
  }

  // moveFocus is opt-in, and only the "Cookie settings" button passes it.
  // The 2s fallback timer must NOT move focus: a reader tabbing toward "Check
  // a message", or typing into the search field, would be relocated mid-action
  // by something they never asked for (WCAG 3.2.5 Change on Request). On that
  // path the bar is announced instead — it carries aria-live and sits at tab
  // stop 2, so it is reachable immediately without seizing anything.
  function showBanner(opts){
    if(!banner) return;
    if(banner.hidden){
      focusBeforeBanner = document.activeElement;
      banner.hidden = false;
      banner.setAttribute('aria-hidden','false');
      // Announce through the always-present live region. Writing into an
      // element that was already in the accessibility tree is what screen
      // readers reliably treat as an update; revealing a region that carries
      // aria-live itself often announces nothing.
      var live = document.getElementById('liveStatus');
      if(live){ live.textContent = 'Cookies and privacy choice available at the end of the page.'; }
      if(consentChanged) consentChanged();
      syncConsentOffset();
    }
    // Reject first: it is the privacy-preserving option and must never be the
    // harder of the two to reach.
    if(opts && opts.moveFocus && reject){
      try { reject.focus(); } catch (err) { /* not focusable yet */ }
    }
  }

  // The bar reflows between the one-line desktop layout and the stacked mobile
  // grid, so the reserved space has to be re-measured, not cached.
  window.addEventListener('resize', syncConsentOffset);

  // ─── Mobile standing routes ────────────────────────────────────────────────
  (function(){
    const actions = document.getElementById('mobileActions');
    if(!actions) return;
    const check = actions.querySelector('.ma-check');
    const recovery = actions.querySelector('.ma-recovery');
    // Drop whichever route the reader is already on, and let the other fill the
    // bar rather than offering someone on /check/ a button back to /check/.
    const path = window.location.pathname;
    if(check && path.indexOf('/check') === 0){ check.remove(); actions.classList.add('is-single'); }
    else if(recovery && path.indexOf('/recovery') === 0){ recovery.remove(); actions.classList.add('is-single'); }

    // Below the header the reader has no standing route; above it they still
    // have the header CTA and, on the homepage, the hero tiles themselves.
    const REVEAL_AT = 420;
    let shown = false;
    function update(){
      const consentUp = banner && !banner.hidden;
      const want = !consentUp && window.scrollY > REVEAL_AT;
      if(want === shown) return;
      shown = want;
      actions.classList.toggle('is-visible', want);
      syncConsentOffset();
    }
    window.addEventListener('scroll', update, {passive:true});
    window.addEventListener('resize', update);
    consentChanged = update;
    update();
  })();

  function setPreference(mode){
    safeSet(storageKey, mode);
    applyConsent(mode);
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
      hideBanner();
    } else {
      showBanner();
    }
  }

  // AdSense's own tag installs window.__tcfapi and loads Google's certified
  // consent message; there is NO separate tag in base.html and Google documents
  // that none is needed. It follows that pages served WITHOUT the ad tag have no
  // certified CMP, which is why the fallback below is the real consent surface
  // there (verified live, 2026-07-31),
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
        if(typeof tcData.gdprApplies === 'boolean'){
          var wasUnknown = (gdprApplies === null);
          gdprApplies = tcData.gdprApplies;
          // gdprApplies resolves asynchronously and can land AFTER the 2s
          // fallback timer has already applied a stored "accepted" preference
          // (with advertising denied, because the region was still unknown).
          // For a confirmed NON-GDPR visitor with no CMP takeover, re-apply the
          // stored preference so advertising consent upgrades for this
          // pageview instead of staying denied until the next visit.
          if(wasUnknown && gdprApplies === false && !cmpTookOver){
            var stored = safeGet(storageKey);
            if(stored === 'accepted'){ applyConsent(stored); }
          }
        }
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
        // The reader asked for this one, so moving focus into it is correct.
        showBanner({moveFocus:true});
      }
    });
  }

  document.addEventListener('click', function(e){
    const link = e.target.closest('a');
    if(!link) return;
    if(link.dataset && link.dataset.affiliateId){
      trackEvent('affiliate_click', {
        affiliate_id: link.dataset.affiliateId,
        affiliate_name: link.dataset.affiliateName || '',
        commercial_status: link.dataset.commercialStatus || 'unknown',
        link_url: link.href
      });
    }
    if(link.hostname && link.hostname !== window.location.hostname){
      trackEvent('outbound_click', {
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
          trackEvent('newsletter_confirmation_requested', {
            event_category: 'engagement',
            method: 'double_opt_in'
          });
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

  // This marker is rendered only after confirm-subscribe has successfully
  // added or reactivated the address in Resend and issued a 303 redirect.
  if(document.querySelector('[data-newsletter-confirmed="true"]')){
    (function trackConfirmedSignup(attemptsLeft){
      var sent = trackEvent('newsletter_signup_confirmed', {
        event_category: 'conversion',
        method: 'double_opt_in'
      });
      // The CMP can resolve after deferred app.js runs. Retry until it records
      // a consent decision; stop immediately after one successful send.
      if(!sent && attemptsLeft > 0){
        setTimeout(function(){ trackConfirmedSignup(attemptsLeft - 1); }, 500);
      }
    })(16);
  }
})();
