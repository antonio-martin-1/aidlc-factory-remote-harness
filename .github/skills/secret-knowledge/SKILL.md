---
name: secret-knowledge
description: Curated reference catalog of CLI tools, one-liners, security/hardening toolkits, web security scanners, performance diagnostics, and DevOps cheatsheets from the Book of Secret Knowledge. Use when agents need concrete tool recommendations, shell command patterns, or security tool references.
---

# Secret Knowledge — Tool & Reference Catalog

## Overview

A curated subset of [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) adapted for AIDLC stage agents. Provides concrete tool names, commands, and patterns — complementary to process/methodology skills from agent-skills.

**This skill is a REFERENCE CATALOG, not process instructions.** It answers "what tool should I use?" and "what command should I run?" — not "how should I think about this problem?"

---

## Routing — Which Sections to Load Per Stage

| Stage Agent | Load |
|-------------|------|
| `reviewer-security` | Section A (Security Toolkit) + Section D (Web Security) |
| `reviewer-performance` | Section C (Performance & Diagnostics) |
| `build-test-agent` | Section B (CLI Tools) + Section E (DevOps) + Section F (One-liners) |
| `code-generator` | Section F (One-liners) + Reference CLI one-liners doc |
| `ship-agent` | Section E (DevOps) + Section G (Systems) |
| `reviewer-code` | Section F (One-liners — build/test commands only) |
| `environment-detection` | Reference shell-tricks doc |

If the task does not match an agent above, load **only** Section F (One-liners) — universally useful.

---

## Step 1: Load this skill

```bash
# Path (auto-resolved by skill system):
#   .agents/custom-skills/secret-knowledge/SKILL.md
```

Log: `[Skill] Loaded: secret-knowledge — routing to <sections>`

---

## Step 2: Apply relevant sections

### Section A — Security & Hardening Toolkit

**Auditing & Hardening:**
| Tool | Use Case | Command |
|------|----------|---------|
| Lynis | System security audit | `lynis audit system` |
| OSSEC | File integrity monitoring | `/var/ossec/bin/ossec-control start` |
| auditd | Kernel audit daemon | `auditctl -w /etc/passwd -p wa -k passwd_changes` |
| Rkhunter | Rootkit scanner | `rkhunter --check --skip-keypress` |
| Tiger | Security audit / IDS | `tiger` |
| grapheneX | Automated system hardening | `graphenex --hardening` |
| DevSec Hardening | Ansible-based server hardening | `ansible-playbook hardening-playbook.yml` |

**Privilege Escalation Enumeration:**
| Tool | Use Case |
|------|----------|
| LinEnum | Local Linux enumeration & PE checks |
| PEASS (linpeas/winpeas) | Privilege escalation awesome scripts |
| SUDO_KILLER | Identify & exploit sudo rule misconfigurations |

**Vulnerability Scanning:**
| Tool | Use Case | Command |
|------|----------|---------|
| vuls | Agent-less vulnerability scanner | `vuls scan` |
| tsunami | Network security scanner (Google) | `java -jar tsunami.jar` |
| OWASP dependency-check | SCA for known CVEs | `dependency-check --scan .` |

**Password Security:**
| Tool | Use Case |
|------|----------|
| John The Ripper | Password cracking |
| hashcat | GPU-accelerated password recovery |
| Mentalist | Custom wordlist generation |

**Reverse Engineering:**
| Tool | Use Case |
|------|----------|
| Ghidra (NSA) | Software reverse engineering framework |
| radare2 | Binary analysis framework |
| IDA | Multi-processor disassembler |
| pwndbg | GDB exploit development |
| Cutter | RE platform (Ghidra decompiler) |

**Fuzzing:**
| Tool | Use Case |
|------|----------|
| AFL / AFL++ | Coverage-guided fuzzing |
| syzkaller | Kernel fuzzer (Google) |

---

### Section B — CLI Tools Reference

**Network Scanning:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| nmap | Port scanning / OS detection | `nmap -sV -sC -O <target>` |
| masscan | Internet-wide scanning | `masscan <range> -p80,443 --rate=1000` |
| RustScan | Fast port discovery | `rustscan -a <target>` |
| zmap | Single-packet network scanner | `zmap -p 443 <range>` |
| netcat | Read/write network connections | `nc -lvnp <port>` |
| socat | Bidirectional data transfer | `socat TCP-LISTEN:<port>,fork,reuseaddr -` |

**Packet Analysis:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| tcpdump | CLI packet capture | `tcpdump -i eth0 -n host <ip>` |
| tshark | Wireshark CLI | `tshark -i eth0 -Y "http.request"` |
| ngrep | Network grep | `ngrep -d eth0 "pattern" port 80` |
| scapy | Packet manipulation (Python) | `scapy` |
| impacket | Network protocol toolkit (Python) | `impacket-smbexec <user>@<target>` |

**HTTP Tools:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| curl | Transfer data with URLs | `curl -vI https://example.com` |
| HTTPie | User-friendly HTTP client | `http https://api.example.com` |
| wuzz | Interactive HTTP inspector | `wuzz` |
| htrace.sh | HTTP(S) troubleshooting Swiss Army knife | `htrace.sh https://example.com` |
| httpstat | Visualize curl statistics | `httpstat https://example.com` |

**SSL/TLS:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| openssl | TLS/SSL toolkit | `openssl s_client -connect host:443 -servername host` |
| testssl.sh | TLS/SSL encryption testing | `testssl.sh https://example.com` |
| sslscan | Discover supported ciphers | `sslscan --targets=host:443` |
| sslyze | Fast SSL/TLS scanning | `sslyze --regular host:443` |

**System Diagnostics:**
| Tool | Use Case |
|------|----------|
| strace | Syscall tracer |
| DTrace | Dynamic tracing (macOS/Solaris) |
| bpftrace | eBPF high-level tracing |
| perf | Linux profiling with perf_events |
| valgrind | Memory debugging + profiling |
| sysdig | Container-aware system exploration |

**Log Analysis:**
| Tool | Use Case |
|------|----------|
| lnav | Log file navigator with search |
| GoAccess | Real-time web log analyzer |
| angle-grinder | Slice and dice log files on CLI |

---

### Section C — Performance & Diagnostics

**Benchmarking:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| wrk | HTTP benchmarking | `wrk -t12 -c400 -d30s https://example.com` |
| wrk2 | Constant-throughput variant | `wrk2 -t2 -c100 -d30s -R2000 https://example.com` |
| vegeta | HTTP load testing | `echo "GET https://example.com" \| vegeta attack -rate=100 -duration=30s` |
| hey | HTTP load generator (ab replacement) | `hey -n 10000 -c 100 https://example.com` |
| siege | HTTP load testing | `siege -c100 -t30s https://example.com` |
| ab | ApacheBench | `ab -n 10000 -c 100 https://example.com/` |
| bombadier | Fast cross-platform HTTP benchmarking | `bombardier -c 100 -n 10000 https://example.com` |

**Profiling & Tracing:**
| Tool | Use Case |
|------|----------|
| perf | CPU performance counters + stack traces |
| FlameGraph (Brendan Gregg) | Stack trace visualization (svg) |
| bpftrace | eBPF-based dynamic tracing |
| gperftools | CPU profiler + heap profiler |
| Valgrind (Callgrind) | Function-level profiling |
| rr | Record/replay debugging |
| Austin | Python frame stack sampler |

**System Monitoring:**
| Tool | Use Case | Command Pattern |
|------|----------|----------------|
| htop | Interactive process viewer | `htop` |
| glances | Cross-platform monitoring | `glances` |
| nmon | Performance monitoring + data analysis | `nmon` |
| atop | CPU, memory, disk, network, processes | `atop` |
| bmon | Network bandwidth monitoring | `bmon` |
| vnstat | Network traffic monitor | `vnstat -i eth0` |
| iptraf-ng | IP traffic monitoring | `iptraf-ng` |

**Disk & Filesystem:**
| Tool | Use Case |
|------|----------|
| iostat | CPU + I/O statistics |
| iotop | Per-process I/O monitoring |
| ncdu | Disk usage analyzer (ncurses) |
| du + sort | Classic disk usage: `du -sh /* \| sort -rh \| head -10` |

---

### Section D — Web Security

**SSL/TLS Testing (Web):**
| Tool | URL |
|------|-----|
| SSL Labs Server Test | `ssllabs.com/ssltest` |
| ImmuniWeb SSLScan | `immuniweb.com/ssl` |
| Mozilla Observatory | `observatory.mozilla.org` |
| Hardenize | `hardenize.com` |
| CryptCheck | `cryptcheck.fr` |

**HTTP Headers:**
| Tool | URL |
|------|-----|
| Security Headers | `securityheaders.com` |
| CSP Evaluator | `csp-evaluator.withgoogle.com` |
| Report URI | `report-uri.com` |
| webhint | `webhint.io` |

**Reference Standards:**
| Resource | URL |
|----------|-----|
| OWASP ASVS 4.0 | `owasp.org/ASVS` |
| OWASP WSTG | `owasp.org/wstg` |
| OWASP API Security Top 10 | `owasp.org/API-Security` |
| Mozilla Web Security Guidelines | `infosec.mozilla.org/guidelines` |
| API Security Checklist | `github.com/shieldfy/API-Security-Checklist` |
| OWASP Cheat Sheet Series | `cheatsheetseries.owasp.org` |
| Mozilla SSL Config Generator | `github.com/mozilla/ssl-config-generator` |
| cipherli.st | Strong ciphers for Apache, Nginx, Lighttpd |

---

### Section E — DevOps & Containers

**Containers:**
| Tool | Use Case |
|------|----------|
| gvisor (Google) | Container runtime sandbox |
| ctop | Top-like container metrics |
| hadolint | Dockerfile linter: `hadolint Dockerfile` |

**Reverse Proxy / Load Balancer:**
| Tool | Use Case |
|------|----------|
| Nginx | Web server + reverse proxy |
| HAProxy | TCP/HTTP load balancer |
| Traefik | Docker-aware reverse proxy with auto TLS |
| Caddy | HTTP/2 web server with HTTPS by default |
| Varnish Cache | HTTP accelerator |

**DNS:**
| Tool | Use Case |
|------|----------|
| Unbound | Validating, recursive, caching DNS resolver |
| dnsperf | DNS performance testing |
| dnscrypt-proxy | Encrypted DNS proxy |
| massdns | High-performance DNS stub resolver for bulk lookups |

**System Services:**
| Tool | Use Case |
|------|----------|
| pi-hole | DNS sinkhole (network-wide ad blocking) |
| maltrail | Malicious traffic detection |
| Security Monkey (Netflix) | AWS/GCP asset monitoring |
| Firecracker (AWS) | Secure microVMs for serverless |

---

### Section F — Shell One-liners (Top 40)

Organized by tool. See `reference/cli-one-liners.md` for the full catalog.

**find:**
```bash
find / -mmin 60 -type f                              # Files modified in last 60 min
find / -type f -size +20M                             # Files larger than 20MB
find / -type f -exec md5sum '{}' ';' | sort | uniq --all-repeated=separate -w 33 # Duplicate files
find / \( -perm -4000 -o -perm -2000 \) -type f -exec ls -la {} \;  # SUID/SGID executables
find . -type f -mtime +60 -delete                     # Delete files older than 60 days
```

**lsof:**
```bash
lsof -i :<port>                                       # Process listening on port
lsof -u <user> -a +D /etc                            # Open files by user in a directory
lsof / | awk '{ if($7 > 1048576) print $7/1048576 "MB" " " $9 " " $1 }' | sort -n -u | tail | column -t  # 10 largest open files
```

**ps:**
```bash
ps awwfux | less -S                                  # 4-way scrollable process tree
ps hax -o user | sort | uniq -c | sort -r            # Processes per user counter
ps -lfC nginx                                         # All processes by name
top -p $(pgrep -d , nginx)                            # Monitor only specific processes
```

**Network:**
```bash
ss -tulpn                                            # All listening TCP/UDP ports with process
ss -tup state established                             # Active connections
tcpdump -i eth0 -nn -s0 -w capture.pcap              # Capture traffic to file
curl -w "@<format>" -o /dev/null -s https://example.com  # HTTP timing breakdown
nc -zv <host> <port>                                 # Port connectivity test
```

**strace:**
```bash
strace -f -p $(pidof nginx)                          # Trace with child processes
timeout 30 strace -p $(< /var/run/daemon.pid)         # Trace with 30s limit
strace -f -e trace=network nc -l 80                   # Trace network syscalls
```

**Performance:**
```bash
perf top -p <pid>                                     # Live profiling
perf record -g -p <pid> && perf report                # Record + report call graph
vmstat 2 20 -t -w                                     # System utilization (2s intervals, 20 samples)
iostat 2 10 -t -m -c                                  # CPU utilization (2s intervals, 10 samples)
```

**Disk:**
```bash
du -sh /* | sort -rh | head -20                       # Top 20 disk consumers
df -h                                                 # Filesystem usage
ncdu                                                  # Interactive disk analyzer
```

**HTTP:**
```bash
curl -vI https://example.com                          # Full response headers
http -v https://api.example.com                       # HTTPie verbose request
wrk -t12 -c400 -d30s https://example.com             # HTTP benchmark
vegeta attack -rate=100 -duration=30s | vegeta report  # Load test + report
```

---

### Section G — Systems Reference

**OS Hardening:**
| Technology | Description |
|------------|-------------|
| SELinux | Mandatory Access Control (MAC) for Linux |
| AppArmor | Proactive OS/application protection |
| grsecurity | Security patches for Linux kernel |

**Network Services:**
| Service | Use Case |
|---------|----------|
| HAProxy | TCP/HTTP load balancer |
| Nginx | Reverse proxy, web server |
| Varnish | HTTP accelerator / cache |
| Unbound | Recursive DNS resolver with TLS |
| PowerDNS | Authoritative DNS server |

**Security Services:**
| Service | Use Case |
|---------|----------|
| Streisand | Auto-setup WireGuard, OpenSSH, OpenVPN |
| Security Onion | Linux distro for IDS, security monitoring, log management |
| OSSEC | Host-based IDS with FIM |

---

## Step 3: Verification Gates

Every command or tool name emitted MUST pass:

- [ ] **Tool exists** — do not invent tool names; only recommend tools listed in this skill or its reference docs
- [ ] **Command syntax correct** — if you adapt a command, verify the flags are real (check with `--help` if possible)
- [ ] **Security-appropriate** — do not suggest offensive/penetration tools for production hardening workflows (use auditing tools instead, e.g. Lynis over Metasploit)
- [ ] **Platform-aware** — consider whether the tool is Linux-only (bpftrace, perf) vs cross-platform (htop, glances)
- [ ] **No hallucinated URLs** — the URLs in Section D reference real services; do not invent similar URLs

After emitting tool recommendations, log:
```
[Skill] secret-knowledge: emitted <N> tool references (sections: <A-G>)
```

---

## Common Rationalizations to Reject

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "I'll just use a generic `apt-get install` for this" | The Book lists specific tools with known quality — use them |
| "I can invent a reasonable command" | Many tools have non-obvious flags; use the patterns from this skill |
| "This is common knowledge, I don't need to look it up" | The Book organizes *curated* tool lists; common != correct |
| "I'll just use `curl` for everything" | Dedicated tools (wrk, hey, vegeta) exist for benchmarking for a reason |

---

## Red Flags

- **Hallucinated tool names** — if a tool is not in this skill or its reference docs, do NOT recommend it; use the standard OS tooling instead
- **Offensive tools in production hardening** — Metasploit, hashcat, mimikatz are pentest tools; do not suggest them for production security hardening
- **Outdated commands** — e.g., `netstat` is deprecated in favor of `ss`; prefer `ss` in new recommendations
