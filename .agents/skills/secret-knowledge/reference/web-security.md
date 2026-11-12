# Web Security Reference

Curated from [the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge).

---

## SSL/TLS Testing Services

| Tool | URL | Use Case |
|------|-----|----------|
| SSL Labs Server Test | https://www.ssllabs.com/ssltest | Deep analysis of SSL web server config |
| SSL Labs Server Test (DEV) | https://dev.ssllabs.com/ssltest | Dev version with latest checks |
| Mozilla Observatory | https://observatory.mozilla.org | Scan + rating for security headers, TLS, etc. |
| ImmuniWeb SSLScan | https://www.immuniweb.com/ssl | SSL/TLS test (PCI DSS, HIPAA, NIST) |
| Hardenize | https://www.hardenize.com | Deploy security standards, full audit |
| CryptCheck | https://cryptcheck.fr | TLS server configuration test |
| SSL Check | https://www.jitbit.com/sslcheck | Scan for non-secure content |
| SSL Scanner | http://www.ssltools.com | Website security analysis |
| BadSSL | https://badssl.com | Test client against bad SSL configs |
| TLS Cipher Suite Search | https://ciphersuite.info | Search cipher suites |

---

## HTTP Security Headers

| Tool | URL | Checks |
|------|-----|--------|
| Security Headers | https://securityheaders.com | Full HTTP response header analysis + rating |
| CSP Evaluator | https://csp-evaluator.withgoogle.com | Content Security Policy evaluation |
| Report URI | https://report-uri.com | CSP/HPKP monitoring |
| Useless CSP | https://uselesscsp.com | Public list of ineffective CSP configs |
| webhint | https://webhint.io | Accessibility, speed, security, cross-browser lint |

---

## Command-Line SSL Tools

```bash
# Mozilla SSL Config Generator
# Generates configs for Apache, Nginx, Lighttpd, etc.
# https://ssl-config.mozilla.org

# SSL certificate chain builder
mkchain

# Local dev certificates
mkcert -install
mkcert example.com "*.example.com"

# Certificate transparency log search
curl -s "https://crt.sh/?q=example.com&output=json" | jq .

# Test client SSL capabilities
curl -s https://www.howsmyssl.com/a/check | jq .
```

---

## Key Security Headers to Check

| Header | Purpose | Example Value |
|--------|---------|---------------|
| `Strict-Transport-Security` | Force HTTPS | `max-age=63072000; includeSubDomains; preload` |
| `Content-Security-Policy` | Prevent XSS/data injection | `default-src 'self'` |
| `X-Content-Type-Options` | Prevent MIME sniffing | `nosniff` |
| `X-Frame-Options` | Prevent clickjacking | `DENY` |
| `Referrer-Policy` | Control referrer info | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Control browser features | `camera=(), microphone=()` |
| `X-XSS-Protection` | Legacy XSS filter (mostly deprecated) | `0` (disable, in favor of CSP) |

---

## SSL Configuration References

| Resource | URL |
|----------|-----|
| Mozilla SSL Configuration Generator | https://ssl-config.mozilla.org |
| cipherli.st — Strong Ciphers | https://cipherli.st |
| CAA Record Helper | https://sslmate.com/caa |
| Common CA Database | https://ccadb.org |
| CertStream (real-time CT logs) | https://certstream.calidog.io |
| crt.sh — Certificate Search | https://crt.sh |
| security.txt Generator | https://securitytxt.org |

---

## OWASP References

| Resource | URL |
|----------|-----|
| OWASP Top 10 | https://owasp.org/www-project-top-ten |
| OWASP ASVS 4.0 | https://owasp.org/ASVS |
| OWASP WSTG | https://owasp.org/wstg |
| OWASP API Security Top 10 | https://owasp.org/API-Security |
| OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org |
| OWASP Proactive Controls | https://owasp.org/www-project-proactive-controls |
| OWASP Dependency Check | https://owasp.org/www-project-dependency-check |

---

## Quick SSL Check Commands

```bash
# Full certificate chain + details
openssl s_client -connect example.com:443 -servername example.com -showcerts

# Check certificate expiry
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>&1 \
  | openssl x509 -noout -dates

# Check supported TLS versions
openssl s_client -connect example.com:443 -servername example.com -tls1_2
openssl s_client -connect example.com:443 -servername example.com -tls1_3

# Check OCSP stapling
openssl s_client -connect example.com:443 -servername example.com -status \
  | grep -E "OCSP response|Next Update"

# Check HSTS
curl -sI https://example.com | grep -i strict-transport

# Check CSP
curl -sI https://example.com | grep -i content-security-policy

# Full security scan with testssl.sh
testssl.sh --quiet --parallel https://example.com

# Fast cipher enumeration
sslscan --targets=example.com:443
```
