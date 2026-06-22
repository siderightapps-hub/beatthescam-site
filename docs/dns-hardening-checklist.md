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

- **Resend (newsletter) — currently 1024-bit.** There is **no key-size toggle in
  the Resend dashboard.** To move to 2048-bit you must re-provision: remove the
  `updates.beatthescam.com` domain in Resend and re-add it (Resend issues a fresh
  DKIM key on new domains), then update the regenerated `resend._domainkey.updates`
  record in Dynadot — or ask Resend support to rotate the key. Confirm the new
  public key starts `MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A…` (2048) instead of
  `MIGfMA0…` (1024). **Priority: low** — a 1024-bit key still passes DMARC; this
  is "preferable," not a vulnerability. Re-adding the domain re-verifies all
  Resend DNS records, so do it during a quiet window.
- **Microsoft 365:** Defender portal → Email & collaboration → Policies & rules →
  Threat policies → DKIM → `beatthescam.com` → ensure enabled; rotate to 2048-bit
  if it is still 1024.

## 3. CAA records — none today

Restrict which CA can issue certs (Netlify uses Let's Encrypt). **Dynadot format:**
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

## Suggested order

1. DMARC Step 1 (reporting on, still `p=none`) — zero risk, start collecting data.
2. CAA records — zero delivery risk.
3. HSTS preload submission (after confirming the header is live).
4. M365 DKIM → 2048 (low risk).
5. DMARC Step 2 → 3 once reports are clean.
6. Resend DKIM → 2048 and DNSSEC — optional, lower priority.
