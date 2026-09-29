# DNS migration: GoDaddy/Render → Cloudflare

Moving `amorframesbyluv.com` off Render and onto the Cloudflare Pages
deployment at `amorframes.pages.dev`.

Verify at every stage with:

```bash
python scripts/check_dns.py
```

## Current state (captured 2026-09-29, before any changes)

Nameservers: `ns19.domaincontrol.com`, `ns20.domaincontrol.com` (GoDaddy)

| Type | Name | Value | Action |
|---|---|---|---|
| A | `@` | `216.24.57.1` | **Replace** — Render |
| CNAME | `www` | `amorframes.onrender.com` | **Replace** — Render |
| TXT | `@` | `v=spf1 include:dc-77d78235e8._spfm.amorframesbyluv.com ~all` | **Keep / simplify** |
| TXT | `dc-77d78235e8._spfm` | `v=spf1 include:mailgun.org ~all` | **Keep** — see below |
| TXT | `pic._domainkey` | `k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDmtvMLnKS+IS2WhaAO/Uj1NI3rmKmlPMG0Y7OjWP9neBA9fD55m2FrZhxaPy7vgPr08wuRFatEe3or94BihCMOrNvSjrXdjBPqgjq39XGVrDzrJEcduY2Qt+POZuIJIhi21WIMnG+03Xfs+CV2iFoTD8Hu/Ecidcrbow6dkPuFUQIDAQAB` | **Keep** — Mailgun DKIM |
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:dmarc_rua@onsecureserver.net;` | **Keep** |
| CNAME | `email` | `mailgun.org` | **Keep** — Mailgun tracking |
| CNAME | `_domainconnect` | `_domainconnect.gd.domaincontrol.com` | **Drop** — GoDaddy automation, inert after the move |
| MX | — | *none* | Nothing to preserve; the domain is send-only |

There are **no MX records**, so the domain receives no mail. Inbound email is not
a migration risk. Form submissions go to `amorframesbyluv@gmail.com`.

## The one that will get missed

The root SPF record does **not** include Mailgun directly. It points at a
GoDaddy-generated subdomain which then includes `mailgun.org`:

```
@                      v=spf1 include:dc-77d78235e8._spfm.amorframesbyluv.com ~all
dc-77d78235e8._spfm    v=spf1 include:mailgun.org ~all
```

Cloudflare's import scans predictable record names. A record at
`dc-77d78235e8._spfm` is very unlikely to be found. If it is lost, the root SPF
include dead-ends on NXDOMAIN and SPF evaluation fails.

DKIM would still carry DMARC (`adkim=r` means relaxed alignment, and DMARC
passes on SPF *or* DKIM), so mail would probably still be delivered — but you'd
be one record away from silent quarantine under `p=quarantine`.

**Recommended:** collapse the chain while you're rebuilding the zone anyway. Set
the root TXT to:

```
v=spf1 include:mailgun.org ~all
```

and don't recreate `dc-77d78235e8._spfm` at all. Same result, one fewer DNS
lookup against SPF's 10-lookup limit, and no GoDaddy-specific indirection left
in a zone GoDaddy no longer serves.

If you'd rather change nothing, recreate **both** records exactly as above.

## Procedure

Get the Cloudflare zone fully correct **before** touching nameservers. While the
zone is pending, GoDaddy still answers, so a complete zone means no gap.

**1. Add the site.** Cloudflare dashboard → Add a site → `amorframesbyluv.com` →
Free plan. It scans and imports what it can find.

**2. Audit the imported zone against the table above.** This is the step that
matters. Confirm present: root SPF, DKIM at `pic._domainkey` (compare the key
end-to-end — a truncated key fails silently), `_dmarc`, and `email` → mailgun.org.
Add anything missing by hand. Apply the SPF simplification here if you're taking it.

**3. Delete the Render records** — the `A @ 216.24.57.1` and the
`CNAME www → amorframes.onrender.com`.

**4. Point the site at Pages.** Pages project → Custom domains → add both
`amorframesbyluv.com` and `www.amorframesbyluv.com`. Cloudflare creates the DNS
records itself and flattens the apex CNAME. If it refuses while the zone is
pending, come back after step 6.

**5. Switch nameservers at GoDaddy** to the two Cloudflare gave you. GoDaddy →
domain → Nameservers → Change → "I'll use my own".

**6. Wait for Cloudflare to show the zone Active.** Usually well under an hour;
the NS records carry a 3600s TTL. Allow up to 24h for stragglers.

**7. Verify.**

```bash
python scripts/check_dns.py
```

Everything should read OK. Then load the site on the real domain, click into a
gallery and a sub-shoot, and **submit the contact form** — that exercises the
Mailgun path end to end, which is the only thing DNS can quietly break.

**8. Delete the Render service** once the domain has served correctly for a day.

## Rollback

Nothing here is destructive until step 5, and even that reverses: point the
GoDaddy nameservers back to `ns19.domaincontrol.com` and
`ns20.domaincontrol.com`. GoDaddy retains the old zone, so the table above is
your reference if any record needs rebuilding by hand.

## After the cutover

- `amorframes.pages.dev` keeps working alongside the custom domain — useful for
  testing a deploy before anyone sees it.
- Cloudflare's proxy (the orange cloud) is on by default for the Pages records.
  Leave it on: that's the CDN and the free SSL.
- The SSL certificate provisions automatically once the zone is active. If the
  site loads but the certificate looks wrong for the first few minutes, that's
  normal — give it time before changing anything.
