# Commercial measurement ledger

This folder is the monthly, buyer-verifiable record of audience behaviour, revenue and operating cost. It complements the retained Search Console and Bing AI snapshots in `analytics/search-ai/`; it does not replace platform exports or invoices.

## Monthly close

Complete both CSV files after each calendar month closes:

1. Export the month from GA4, Google Search Console, Bing AI Performance, Resend, AdSense and every approved affiliate platform.
2. Store raw exports in a dated private evidence folder outside the public site. Do not commit subscriber addresses, credentials, tax records or unredacted invoices.
3. Add one row to `monthly-kpis.csv` and one row to `monthly-pnl.csv`.
4. Use blank for unknown/not-yet-reported. Use `0` only when the platform or invoice proves the value was zero.
5. Reconcile revenue to platform statements or bank receipts and costs to invoices.
6. Record any definition change, outage, campaign, redirect or partial period in `notes`.

## Event definitions

| Event | Meaning | Authoritative source |
|---|---|---|
| `scam_check_submitted` | A consented visitor sent a checker request after client validation | GA4 |
| `scam_check_success` | The checker returned a usable result | GA4 |
| `scam_check_error` | The request failed before a usable result | GA4 + Netlify logs for diagnosis |
| `newsletter_confirmation_requested` | The signup endpoint accepted the request and sent/attempted a confirmation email | GA4 |
| `newsletter_signup_confirmed` | Resend successfully added or reactivated the contact after double opt-in | GA4, consented subset only |
| `affiliate_click` | A consented visitor clicked a configured recommendation | GA4; partner dashboard for conversions/revenue |

No event contains checker text or an email address. GA4 intentionally excludes visitors who decline analytics, so Resend's active-contact count is the source of truth for total subscribers.

## GA4 setup after deployment

- Mark `newsletter_signup_confirmed` as a key event.
- Treat `scam_check_success` as the primary product-use event; do not count a submission and success as two conversions.
- Build a funnel: guide/page view → `scam_check_submitted` → `scam_check_success` → `newsletter_signup_confirmed`.
- Break down `affiliate_click` by `affiliate_id` and `commercial_status`.
- Keep `newsletter_confirmation_requested` diagnostic; it is not a subscriber conversion.

The 18 July baseline row contains only figures already retained in the repository. Empty commercial fields are unknown, not zero.
