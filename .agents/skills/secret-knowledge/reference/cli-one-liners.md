# CLI One-liners Reference

Curated from [the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge).

---

## find

```bash
# Files modified in last 60 minutes
find / -mmin 60 -type f

# Files larger than 20MB
find / -type f -size +20M

# Duplicate files (by MD5 hash)
find -type f -exec md5sum '{}' ';' | sort | uniq --all-repeated=separate -w 33

# SUID/SGID executables
find / \( -perm -4000 -o -perm -2000 \) -type f -exec ls -la {} \;

# Delete files older than 60 days
find . -type f -mtime +60 -delete

# Recursively remove all empty directories
find . -depth -type d -empty -exec rmdir {} \;

# Recursively find/replace in files (skip .git)
find . -not -path '*/\.git*' -type f -print0 | xargs -0 sed -i 's/foo/bar/g'

# Change permission only for files
find . -type f -exec chmod 664 {} +

# Change permission only for directories
find . -type d -exec chmod 755 {} +

# Latest modified files, top 10
find . -type f -exec stat --format '%Y :%y %n' "{}" \; | sort -nr | cut -d: -f2- | head

# All hard links to a file
find /path -xdev -samefile filename
```

---

## lsof

```bash
# Process listening on a specific port
lsof -i :<port>

# Open files by user in a directory
lsof -u <username> -a +D /etc

# 10 largest open files
lsof / | awk '{ if($7 > 1048576) print $7/1048576 "MB" " " $9 " " $1 }' | sort -n -u | tail | column -t

# Current working directory of a process
lsof -p <PID> | grep cwd
```

---

## ps / top

```bash
# 4-way scrollable process tree
ps awwfux | less -S

# Processes per user counter
ps hax -o user | sort | uniq -c | sort -r

# All processes by name
ps -lfC nginx

# Monitor only specific processes
top -p $(pgrep -d , <str>)
```

---

## Network (ss / netstat / nc / tcpdump)

```bash
# All listening TCP/UDP ports with process
ss -tulpn

# Active connections
ss -tup state established

# Port connectivity test
nc -zv <host> <port>

# Capture traffic to file
tcpdump -i eth0 -nn -s0 -w capture.pcap

# Filter by host
tcpdump -i eth0 -n host 10.0.0.1

# Filter by port
tcpdump -i eth0 -n port 80 or port 443

# HTTP traffic only
tcpdump -i eth0 -n -A 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'

# Show interface throughput
bmon -p eth0

# Network bandwidth test
iperf3 -c <server> -t 30
```

---

## curl / HTTP

```bash
# Full response headers + timing
curl -vI https://example.com

# HTTP timing breakdown
curl -w "@format.txt" -o /dev/null -s https://example.com

# Follow redirects + show final URL
curl -Ls -o /dev/null -w "%{url_effective}" https://bit.ly/something

# Test HTTP/2 support
curl -v --http2 https://example.com

# Check SSL cert details
curl -vI https://example.com 2>&1 | grep -E "SSL|TLS|certificate"

# Download with resume
curl -C - -O https://example.com/largefile.zip

# Measure total time
curl -s -w "Connect: %{time_connect}s, TTFB: %{time_starttransfer}s, Total: %{time_total}s\n" -o /dev/null https://example.com
```

---

## strace (diagnostics)

```bash
# Trace process with children
strace -f -p $(pidof nginx)

# Trace with 30s timeout
timeout 30 strace -p $(< /var/run/daemon.pid)

# Trace network syscalls only
strace -f -e trace=network nc -l 80

# Trace file operations
strace -f -e trace=open,openat,read,write -p <PID>

# Trace with timestamps + output to file
strace -f -T -o /tmp/trace.out -p <PID>

# Summarize syscalls
strace -c -p <PID>
```

---

## Performance & Profiling

```bash
# Live profiling with perf
perf top -p <PID>

# Record + report call graph
perf record -g -p <PID> && perf report

# System utilization (vmstat)
vmstat 2 20 -t -w

# CPU utilization only (iostat)
iostat 2 10 -t -m -c

# Disk utilization only (iostat)
iostat 2 10 -t -m -d

# Memory info
free -h
cat /proc/meminfo
vmstat -s

# Disk usage
du -sh /* | sort -rh | head -20
df -h

# Interactive process viewer
htop

# Cross-platform monitoring
glances
```

---

## Process Management

```bash
# Kill process on port
kill -9 $(lsof -i :<port> | awk '{l=$2} END {print l}')

# Kill by name
pkill -f <process_name>

# Find PID by port
fuser <port>/tcp

# Process priority
renice -n -10 -p <PID>

# Run command with timeout
timeout 30 command_here
```

---

## File Operations

```bash
# Compare two directory trees
diff -rq dir1/ dir2/

# Find files containing text
grep -rn "pattern" --include="*.py" .

# Search within compressed files
zgrep "pattern" file.gz

# Watch file changes
tail -f /var/log/syslog

# Follow + filter log
tail -f /var/log/nginx/access.log | grep "500"

# Large files in current directory
find . -type f -exec du -Sh {} + | sort -rh | head -20
```

---

## Disk Operations

```bash
# Disk I/O stats per device
iostat -x 2

# Per-process I/O
iotop

# Filesystem usage (human-readable)
df -hT

# Inode usage
df -i

# Mount options
mount | column -t
```

---

## Memory

```bash
# Process memory usage (RSS sorted)
ps aux --sort=-%mem | head -20

# Top memory consumers
ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -20

# Shared memory segments
ipcs -m

# Hugepages info
grep Huge /proc/meminfo

# Slab cache info
vmstat -m
```

---

## Docker

```bash
# Container metrics (top-like)
ctop

# Dockerfile lint
hadolint Dockerfile

# Inspect container resources
docker stats <container>

# Show container processes
docker top <container>

# Layer info
docker history <image>
```

---

## Git (misc)

```bash
# Compact log graph
git log --oneline --graph --decorate --all

# Search commits by content
git log -S "pattern" --all

# Show file from another branch
git show <branch>:path/to/file

# Interactive staging
git add -p

# Who changed each line
git blame <file>
```

---

## Misc Useful

```bash
# JSON pretty-print
cat file.json | python -m json.tool

# Better JSON grep
gron file.json | grep "pattern"

# Colorized man pages
man ls | less -R

# Find command, type `fzf`
<ctrl-r> in bash  # Reverse search history

# Quick HTTP server (Python 3)
python3 -m http.server 8000

# Quick HTTP server (netcat)
while true; do nc -l -p 8080 -e /bin/cat index.html; done

# Generate random password
openssl rand -base64 32

# Watch directory for changes
inotifywait -m -r -e modify,create,delete .
```
