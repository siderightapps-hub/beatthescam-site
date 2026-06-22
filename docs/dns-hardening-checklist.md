# DNS / email / TLS hardening checklist (tranche F)

Operator runbook for the DNS, email-auth, and TLS items from the Executive
Verdict audit (2026-06-22). These are **manual dashboard tasks** — none of this
lives in the repo. Status reflects the live state confirmed by `dig` on
2026-06-22.

## Where everything is managed

| Thing | Provider | Notes |
|---|---|---|
| Registrar **and** DNS host | **Dynadot** | Dynadot DNS, nameservers `ns1/ns2.dyna-ns.net`. All records below are edited in the Dynadot control panel. |
| Corporate email (apex) | **Microsoft 365** | MX `beatthescam-com.mail.protection.outlook.com`; SPF `include:spf.protection.outlook.com -all`; DKIM via `selector1/2._domainkey` CNAMEs. |
| Newsletter sender | **Resend** | From `updates.beatthescam.com`; DKIM at `resend._domainkey.updates`. |
| Static site TLS | **Netlify** | Let's Encrypt certificate, auto-renew. |

**Reporting mailbox:** `dmarc@beatthescam.com` is an **alias of `privacy@beatthescam.com`**
(set up by the operator 2026-06-22). Use it for DMARC `rua`/`ruf`.

---

## 1. DMARC — staged `p=none` → `quarantine` → `reject`

Current: `_dmarc.beatthescam.com TXT "v=DMARC1; p=none;"` (monitor only, no reporting).
Two senders must stay aligned before enforcing: **Microsoft 365** (apex) and
**Resend** (newsletter from `updates.`).

- **Step 1 — ✅ DONE (live 2026-06-22), reporting on, still `p=none`:**
  ```
  _dmarc.beatthescam.com  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@beatthescam.com; fo=1"
  ```
- **Step 2 — after ~1–2 weeks, once reports show BOTH M365 and Resend passing:**
  ```
  "v=DMARC1; p=quarantine; pct=25; rua=mailto:dmarc@beatthescam.com"
  ```
  then ramp `pct` 25 → 50 → 100.
- **Step 3 — enforce:**
  ```
  "v=DMARC1; p=reject; sp=reject; rua=mailto:dmarc@beatthescam.com"
  ```
- ⚠️ **Do not skip to reject.** Enforcing before Resend newsletter passes DMARC
  (via DKIM alignment on `updates.`) would quarantine/reject your own subscriber
  emails.

## 2. DKIM → 2048-bit

- **Microsoft 365 — ✅ rotated 2026-06-22.** "Rotate DKIM keys" in the Defender
  portal regenerates a 2048-bit key; CNAMEs unchanged. New key publishes within a
  few hours. Authoritative check is the portal ("Signing DKIM signatures") or a
  DKIM pass on a real sent email — the Microsoft-hosted key TXT does not always
  resolve via a plain `dig` of the CNAME target.
- **Resend (newsletter) — was 1024-bit; ⏳ support ticket open 2026-06-22** to
  confirm/rotate the key bit length. There is **no key-size toggle in the Resend
  dashboard**; if support can't rotate it, the fallback is to remove and re-add
  the `updates.beatthescam.com` domain in Resend (issues a fresh key), then update
  the regenerated `resend._domainkey.updates` record in Dynadot. Target key starts
  `MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A…` (2048) vs `MIGfMA0…` (1024). **Priority:
  low** — 1024 still passes DMARC. Re-adding re-verifies all Resend records, so do
  it in a quiet window if needed.

## 3. CAA records — ✅ DONE (live 2026-06-22)

All three records live (`dig +short CAA beatthescam.com` returns issue, issuewild,
iodef for letsencrypt.org). Restrict which CA can issue certs. **Dynadot format:**
choose Record Type **CAA**, leave **Subdomain blank** (= apex), and type the whole
record — `Flag Tag Value`, single spaces — into the one destination field. There
are no separate issue/issuewild/iodef dropdowns. Add three records:
```
0 issue "letsencrypt.org"
0 issuewild "letsencrypt.org"
0 iodef "mailto:dmarc@beatthescam.com"
```
⚠️ If any subdomain ever gets a cert from a different CA — e.g. if Resend's
custom **tracking subdomain** is later enabled — add that CA too, or its cert
issuance will fail. Verify after saving: `dig +short CAA beatthescam.com`.

## 4. DNSSEC — blocked on Dynadot DNS

No DS record today. **Dynadot only offers DNSSEC when the domain uses third-party
nameservers** (the Settings page shows: *"The domain must use third-party Name
Servers server setting first."*). Because the domain currently uses **Dynadot
DNS**, DNSSEC is not available without first moving DNS hosting to a DNSSEC-capable
provider (e.g. Cloudflare) and re-creating every record there. **Priority: low /
optional** — weigh the migration effort against the benefit; defer unless DNS is
being moved for another reason.

## 5. HSTS preload — ✅ SUBMITTED 2026-06-22 (pending inclusion)

`netlify.toml` serves `Strict-Transport-Security: max-age=63072000;
includeSubDomains; preload` (confirmed live). Submitted at https://hstspreload.org
— status "pending inclusion". ⚠️ Preload + `includeSubDomains` covers ALL
subdomains, so every current/future subdomain (incl. any Resend tracking
subdomain) MUST serve valid HTTPS or it becomes unreachable. Re-check status over
the next few weeks.

## 6. (Optional) Resend TLS

Resend domain TLS is currently **Opportunistic** (Configuration tab). That is the
safe default. "Enforced" guarantees encryption but bounces mail to receivers
without TLS — leave Opportunistic unless you have a specific compliance reason.

---

## Status snapshot (2026-06-22)

- ✅ DMARC Step 1 (reporting on, `p=none`) — live.
- ✅ CAA records — live.
- ✅ HSTS preload — submitted, pending inclusion.
- ✅ M365 DKIM — rotated to 2048-bit (propagating).
- ⏳ Resend DKIM → 2048 — support ticket open (low priority; 1024 passes DMARC).
- ⬜ DMARC Step 2 → 3 (quarantine → reject) — wait ~1–2 weeks, confirm `dmarc@`
  reports show BOTH M365 and Resend passing, then ramp.
- ⬜ DNSSEC — blocked on Dynadot (needs third-party NS); optional, deferred.
