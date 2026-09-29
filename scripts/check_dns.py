"""Verify DNS and the live site during the Cloudflare migration.

    python scripts/check_dns.py

Safe to run any time -- it only reads public DNS and makes GET requests.
Run it before switching nameservers, after Cloudflare shows the zone active,
and again a day later.

The check that matters most is SPF_CHAIN. The root SPF record does not include
Mailgun directly; it points at a GoDaddy-generated subdomain which in turn
includes mailgun.org. Automated DNS imports are unlikely to discover a record
at that name, and if it is lost the SPF chain dead-ends.
"""
import json
import sys
import urllib.error
import urllib.request

DOMAIN = 'amorframesbyluv.com'
PAGES_HOST = 'amorframes.pages.dev'
SPF_CHAIN_HOST = f'dc-77d78235e8._spfm.{DOMAIN}'
DKIM_HOST = f'pic._domainkey.{DOMAIN}'

OK, WARN, FAIL = 'OK  ', 'WARN', 'FAIL'
results = []


def resolve(name, rtype):
    url = f'https://dns.google/resolve?name={name}&type={rtype}'
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
    except Exception as exc:
        return None, str(exc)
    return [a.get('data', '') for a in data.get('Answer', [])], None


def record(label, status, detail):
    results.append((status, label, detail))
    print(f"[{status}] {label:<22} {detail}")


def check_nameservers():
    answers, err = resolve(DOMAIN, 'NS')
    if err:
        return record('NAMESERVERS', FAIL, err)
    ns = sorted(a.lower().rstrip('.') for a in answers)
    if any('cloudflare' in n for n in ns):
        record('NAMESERVERS', OK, f"on Cloudflare: {', '.join(ns)}")
    elif any('domaincontrol' in n for n in ns):
        record('NAMESERVERS', WARN, f"still GoDaddy: {', '.join(ns)}")
    else:
        record('NAMESERVERS', WARN, ', '.join(ns) or 'none')


def check_site_records():
    for host in (DOMAIN, f'www.{DOMAIN}'):
        cname, _ = resolve(host, 'CNAME')
        a, _ = resolve(host, 'A')
        target = (cname or []) + (a or [])
        joined = ' '.join(t.rstrip('.') for t in target)
        label = 'APEX' if host == DOMAIN else 'WWW'
        if not target:
            record(label, FAIL, 'does not resolve')
        elif PAGES_HOST in joined:
            record(label, OK, f'-> {joined}')
        elif 'onrender' in joined or '216.24.57' in joined:
            record(label, WARN, f'still Render: {joined}')
        else:
            record(label, WARN, joined)


def check_spf():
    answers, err = resolve(DOMAIN, 'TXT')
    if err:
        return record('SPF_ROOT', FAIL, err)
    spf = [a for a in answers if a.lower().startswith('v=spf1')]
    if not spf:
        return record('SPF_ROOT', FAIL, 'no SPF record on the root domain')
    root = spf[0]
    record('SPF_ROOT', OK, root)

    if 'include:mailgun.org' in root:
        return record('SPF_CHAIN', OK, 'includes mailgun.org directly')
    if '_spfm.' not in root:
        return record('SPF_CHAIN', WARN, 'no mailgun include and no chain host')

    chain, err = resolve(SPF_CHAIN_HOST, 'TXT')
    if err or not chain:
        record('SPF_CHAIN', FAIL,
               f'{SPF_CHAIN_HOST} does not resolve -- SPF dead-ends here')
    elif any('mailgun.org' in c for c in chain):
        record('SPF_CHAIN', OK, f'{SPF_CHAIN_HOST} -> {chain[0]}')
    else:
        record('SPF_CHAIN', WARN, f'resolves but no mailgun: {chain[0]}')


def check_dkim():
    answers, err = resolve(DKIM_HOST, 'TXT')
    if err or not answers:
        return record('DKIM', FAIL, f'{DKIM_HOST} missing -- Mailgun cannot sign')
    key = answers[0]
    if 'p=' not in key:
        return record('DKIM', FAIL, 'record present but has no public key')
    plen = len(key.split('p=', 1)[1].strip().strip('"'))
    status = OK if plen > 200 else WARN
    record('DKIM', status, f'{plen} char key (truncation would break signing)')


def check_dmarc():
    answers, err = resolve(f'_dmarc.{DOMAIN}', 'TXT')
    if err or not answers:
        return record('DMARC', WARN, 'no DMARC record')
    record('DMARC', OK, answers[0])


def check_mailgun_cname():
    answers, err = resolve(f'email.{DOMAIN}', 'CNAME')
    if err or not answers:
        return record('MAILGUN_CNAME', WARN,
                      f'email.{DOMAIN} missing (open/click tracking only)')
    record('MAILGUN_CNAME', OK, f"-> {answers[0].rstrip('.')}")


def check_mx():
    answers, _ = resolve(DOMAIN, 'MX')
    if answers:
        record('MX', OK, '; '.join(answers))
    else:
        record('MX', OK, 'none -- domain is send-only, nothing to preserve')


def check_https():
    for host in (DOMAIN, f'www.{DOMAIN}', PAGES_HOST):
        req = urllib.request.Request(f'https://{host}/',
                                     headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read(4000).decode('utf-8', 'replace')
                served = 'Amor Frames' in body
                record(f'HTTPS {host}', OK if served else WARN,
                       f'{r.status}, {"site content" if served else "unexpected body"}')
        except urllib.error.HTTPError as exc:
            record(f'HTTPS {host}', WARN, f'HTTP {exc.code}')
        except Exception as exc:
            record(f'HTTPS {host}', FAIL, type(exc).__name__)


def main():
    print(f"Checking {DOMAIN}\n")
    check_nameservers()
    check_site_records()
    print()
    check_spf()
    check_dkim()
    check_dmarc()
    check_mailgun_cname()
    check_mx()
    print()
    check_https()

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    print(f"\n{len(results)} checks, {len(fails)} failed, {len(warns)} warnings")
    if fails:
        print("\nMUST FIX:")
        for _, label, detail in fails:
            print(f"  {label}: {detail}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
