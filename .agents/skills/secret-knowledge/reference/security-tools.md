# Security Tools Reference

Curated from [the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge).

---

## Auditing & Hardening

| Tool | Category | Description | Install / Run |
|------|----------|-------------|---------------|
| Lynis | Auditing | Battle-tested security tool for Linux, macOS, Unix | `lynis audit system` |
| OSSEC | HIDS | Host-based intrusion detection + FIM | `/var/ossec/bin/ossec-control start` |
| Tiger | Auditing/IDS | Security audit and intrusion detection | `tiger` |
| auditd | Auditing | Linux kernel audit daemon | `auditctl -w /etc/passwd -p wa -k passwd_changes` |
| Rkhunter | Malware | Rootkit hunter scanner | `rkhunter --check --skip-keypress` |
| grapheneX | Hardening | Automated system hardening framework | `graphenex --hardening` |
| DevSec Hardening | Hardening | Ansible-based server hardening | `ansible-playbook hardening-playbook.yml` |
| PEASS (linpeas/winpeas) | PE | Privilege escalation awesome scripts | `./linpeas.sh` |
| LinEnum | PE | Local Linux enumeration & PE checks | `./LinEnum.sh` |
| SUDO_KILLER | PE | Sudo rule misconfiguration exploiter | `./sudokiller.sh` |

Key: PE = Privilege Escalation, FIM = File Integrity Monitoring, HIDS = Host-based IDS

---

## Vulnerability Scanning

| Tool | Description | Scope |
|------|-------------|-------|
| vuls | Agent-less vulnerability scanner | Linux, FreeBSD |
| tsunami (Google) | General purpose network security scanner | Network |
| OWASP dependency-check | SCA — checks dependencies against CVEs | App (Java, .NET, Python, Ruby) |
| Nikto2 | Web server scanner | Web |
| w3af | Web application attack and audit framework | Web |
| OpenVAS | Full-featured vulnerability scanner | Network |
| nessus | Commercial vulnerability scanner | Network |

---

## Network Scanning

| Tool | Description | Command Pattern |
|------|-------------|----------------|
| nmap | Port scanning + OS detection + service version | `nmap -sV -sC -O <target>` |
| masscan | Fastest internet port scanner | `masscan <range> -p80,443 --rate=1000` |
| RustScan | Rust-based fast port discovery | `rustscan -a <target>` |
| zmap | Single-packet network scanner | `zmap -p 443 <range>` |
| hping | TCP/IP packet assembler/analyzer | `hping -S <target> -p 80` |
| unicornscan | Distributed TCP port scanner | `unicornscan <target> -p 1-65535` |

---

## Web Application Security

| Tool | Description | Use Case |
|------|-------------|----------|
| Burp Suite | Intercepting proxy + scanner | Web app pentesting |
| OWASP ZAP | Open source intercepting proxy | Web app security testing |
| sqlmap | SQL injection automation | Database exploitation |
| XSStrike | XSS detection suite | Cross-site scripting |
| WhatWaf | WAF detection + bypass | Web application firewall testing |
| Corsy | CORS misconfiguration scanner | API security testing |
| gobuster | Directory/file + DNS busting | Content discovery |
| dirhunt | Find web dirs without bruteforce | Directory enumeration |
| aquatone | Domain flyover screenshot tool | Subdomain visual inspection |
| Photon | OSINT web crawler | Information gathering |

---

## Fuzzing

| Tool | Description |
|------|-------------|
| AFL / AFL++ | Coverage-guided fuzzer |
| syzkaller (Google) | Kernel fuzzer |
| fuzzdb | Attack pattern dictionary for black-box fuzzing |
| libFuzzer | In-process, coverage-guided fuzzer |

---

## Reverse Engineering

| Tool | Description |
|------|-------------|
| Ghidra (NSA) | Software reverse engineering framework (decompiler) |
| radare2 | Portable reverse engineering framework |
| IDA | Multi-processor disassembler + debugger |
| Cutter | RE platform integrating Ghidra's decompiler |
| Binary Ninja | Reverse engineering platform |
| x64dbg | Windows debugger |
| pwndbg | GDB exploit development assistance |
| GDB PEDA | Python exploit development for GDB |

---

## Password Security

| Tool | Description |
|------|-------------|
| John The Ripper | Fast password cracker, many Unix flavors |
| hashcat | World's fastest GPU-accelerated password recovery |
| Mentalist | Graphical custom wordlist generator |
| mimikatz | Windows credential extraction (offensive only) |

---

## OSINT

| Tool | Description |
|------|-------------|
| Recon-ng | Web reconnaissance framework |
| subfinder | Passive subdomain discovery |
| Sublist3r | Fast subdomain enumeration |
| Amass (OWASP) | Subdomain discovery via scraping + crawling |
| theHarvester | Email, subdomain, name enumeration |
| Sherlock | Social media account hunt by username |
| Maltego | Link analysis and data mining |

---

## Standards & References

| Resource | URL |
|----------|-----|
| OWASP ASVS 4.0 | https://owasp.org/ASVS |
| OWASP WSTG | https://owasp.org/wstg |
| OWASP API Security Top 10 | https://owasp.org/API-Security |
| OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org |
| OWASP Proactive Controls | https://owasp.org/www-project-proactive-controls |
| Mozilla Web Security Guidelines | https://infosec.mozilla.org/guidelines/web_security.html |
| Mozilla SSL Config Generator | https://ssl-config.mozilla.org |
| PTES | http://www.pentest-standard.org |
| cipherli.st | https://cipherli.st |

---

## Checklists

| Resource | URL |
|----------|-----|
| API Security Checklist | https://github.com/shieldfy/API-Security-Checklist |
| Front-End Security Checklist | https://github.com/thedaviddias/Front-End-Checklist |
| Web Security Checklist (Mozilla) | https://infosec.mozilla.org/guidelines/web_security |
| Hacking Cheat Sheet | https://github.com/ksanchezcld/Hacking_Cheat_Sheet |
| Payloads All The Things | https://github.com/swisskyrepo/PayloadsAllTheThings |
