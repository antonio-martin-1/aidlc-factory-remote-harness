# DevOps & Systems Cheatsheet

Curated from [the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge).

---

## Containers

```bash
# Top-like container metrics
ctop

# Dockerfile linter
hadolint Dockerfile

# Container runtime sandbox (gVisor)
# Used as: docker run --runtime=runsc <image>

# View container resource usage
docker stats <container>

# Show container processes
docker top <container>

# Image layer information
docker history <image>

# Inspect container details
docker inspect <container>

# Cleanup all unused
docker system prune -af
```

---

## Reverse Proxy / Web Server

**Nginx:**
```bash
# Test configuration
nginx -t

# Graceful reload
nginx -s reload

# Access log tail + filter
tail -f /var/log/nginx/access.log | grep "500"
```

**HAProxy:**
```bash
# Check config
haproxy -f /etc/haproxy/haproxy.cfg -c

# Show stats
echo "show stat" | socat /var/run/haproxy.sock stdio
```

**Varnish:**
```bash
# View cache hit ratio
varnishstat -1 | grep -E "MAIN.(cache_hit|cache_miss)"

# Purge URL
varnishadm ban req.url ~ "^/path"
```

---

## HTTP Load Testing

| Tool | Command | Notes |
|------|---------|-------|
| wrk | `wrk -t12 -c400 -d30s https://example.com` | Multi-threaded, good for latency |
| wrk2 | `wrk2 -t2 -c100 -d30s -R2000 https://example.com` | Constant throughput variant |
| vegeta | `echo "GET https://example.com" \| vegeta attack -rate=100 -duration=30s \| vegeta report` | Produces latency distributions |
| hey | `hey -n 10000 -c 100 https://example.com` | ab replacement, simple |
| siege | `siege -c100 -t30s https://example.com` | Concurrent users simulation |
| ab | `ab -n 10000 -c 100 https://example.com/` | ApacheBench, single-threaded |
| bombardier | `bombardier -c 100 -n 10000 https://example.com` | Fast, cross-platform Go tool |

---

## DNS

```bash
# Quick lookup
dig +short example.com

# Full trace
dig +trace example.com

# Query specific NS
dig @8.8.8.8 example.com

# Reverse lookup
dig -x 8.8.8.8

# Check propagation
dig +short example.com A
dig +short example.com AAAA
dig +short example.com MX

# Bulk resolve (massdns)
massdns -r resolvers.txt -t A -o S domains.txt

# DNS performance test
dnsperf -s 8.8.8.8 -d queries.txt

# DNSSEC validation
dig example.com +dnssec
```

---

## SSL/TLS

```bash
# Full analysis (testssl.sh)
testssl.sh https://example.com

# Quick cipher check
openssl s_client -connect example.com:443 -servername example.com

# Check supported ciphers
sslscan --targets=example.com:443

# Comprehensive scan
sslyze --regular example.com:443

# Certificate chain check
openssl s_client -showcerts -connect example.com:443 </dev/null

# Check cert expiry
openssl s_client -connect example.com:443 </dev/null 2>&1 | openssl x509 -noout -dates

# Generate Let's Encrypt cert
certbot certonly --nginx -d example.com

# Test OCSP stapling
openssl s_client -connect example.com:443 -status </dev/null

# Check HSTS
curl -sI https://example.com | grep -i strict-transport
```

---

## Network

```bash
# All open ports and listening processes
ss -tulpn

# Active connections (established)
ss -tup state established

# Connection tracking count
cat /proc/sys/net/netfilter/nf_conntrack_count

# Trace path to host
mtr example.com

# Interface throughput
bmon -p eth0

# Network bandwidth test (server mode)
iperf3 -s

# Network bandwidth test (client mode)
iperf3 -c <server-ip> -t 30

# Packet capture filter by host
tcpdump -i eth0 -n host 10.0.0.1

# Show interface metrics
ip -s link show eth0

# Routing table
ip route show
```

---

## System Monitoring

```bash
# CPU + memory + disk overview
glances

# CPU + I/O statistics
iostat -x 2

# Per-process I/O
iotop

# Memory details
free -h
cat /proc/meminfo | grep -E "MemTotal|MemFree|Cached|Swap"

# Disk usage overview
df -hT

# Interactive disk analyzer
ncdu /

# Top disk consumers
du -sh /* | sort -rh | head -20

# Processes sorted by memory
ps aux --sort=-%mem | head -20

# Processes sorted by CPU
ps aux --sort=-%cpu | head -20

# Network traffic per interface
vnstat -i eth0 -m
```

---

## Performance Tuning (sysctl)

```bash
# View all current settings
sysctl -a

# Apply optimized network buffer
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# TCP optimization
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# Connection tracking limits
sysctl -w net.netfilter.nf_conntrack_max=1048576

# Save to /etc/sysctl.conf for persistence
sysctl -p
```

---

## Log Analysis

```bash
# Real-time log viewer with search
lnav /var/log/

# Web log analysis (real-time)
goaccess /var/log/nginx/access.log

# Parse JSON logs
cat app.log | jq '.level == "error"' | jq -c '{time, message}'

# Tail multiple logs
tail -f /var/log/nginx/*.log

# Extract 5xx errors
grep -E 'HTTP/[12]\.[01]" 5[0-9]{2}' /var/log/nginx/access.log

# Request count per IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Requests per second (approx)
tail -n 1000 /var/log/nginx/access.log | awk '{print $4}' | sort | uniq -c | tail
```
