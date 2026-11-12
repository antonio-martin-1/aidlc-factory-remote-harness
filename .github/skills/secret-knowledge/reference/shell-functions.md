# Shell Functions & Tricks

Curated from [the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge).

---

## Shell Tricks

### Clean up a dirty shell

When you get a shell that's not clean (e.g., reverse shell):

```bash
script /dev/null -c bash
# Ctrl-Z (send to background)
stty raw -echo; fg
reset
# xterm (when asked for terminal type)
export TERM=xterm
export SHELL=bash
```

### Reload shell without exit

```bash
exec $SHELL -l
```

### Close shell keeping all subprocesses running

```bash
disown -a && exit
```

### Exit without saving shell history

```bash
kill -9 $$
unset HISTFILE && exit
```

### Pipe stdout and stderr to separate commands

```bash
some_command > >(/bin/cmd_for_stdout) 2> >(/bin/cmd_for_stderr)
```

### Redirect stdout and stderr to separate files AND print to screen

```bash
(some_command 2>&1 1>&3 | tee errorlog) 3>&1 1>&2 | tee stdoutlog
```

### Most used commands

```bash
history | awk '{CMD[$2]++;count++;}END { for (a in CMD)print CMD[a] " " CMD[a]/count*100 "% " a;}' \
  | grep -v "./" | column -c3 -s " " -t | sort -nr | nl | head -n 20
```

### Find your most-used commands (alternative)

```bash
fc -l 1 | awk '{CMD[$2]++; count++;} END { for (a in CMD) print CMD[a] " " CMD[a]/count*100 "% " a; }' \
  | grep -v "./" | column -c3 -s " " -t | sort -nr | nl | head -n 20
```

---

## Shell Functions

### DomainResolve — resolve domain to IP via Google DNS-over-HTTPS

```bash
# Dependencies: curl, jq
DomainResolve() {
  local _host="$1"
  local _curl_base="curl --request GET"
  local _timeout="15"
  _host_ip=$($_curl_base -ks -m "$_timeout" \
    "https://dns.google.com/resolve?name=${_host}&type=A" \
    | jq '.Answer[0].data' | tr -d "\"" 2>/dev/null)
  if [[ -z "$_host_ip" ]] || [[ "$_host_ip" == "null" ]]; then
    echo "Unsuccessful domain name resolution."
  else
    echo "$_host > $_host_ip"
  fi
}
```

Usage: `DomainResolve example.com`

---

### GetASN — get ASN for an IP address

```bash
# Dependencies: curl
GetASN() {
  local _ip="$1"
  local _curl_base="curl --request GET"
  local _timeout="15"
  _asn=$($_curl_base -ks -m "$_timeout" "http://ip-api.com/line/${_ip}?fields=as")
  _state=$(echo $?)
  if [[ -z "$_ip" ]] || [[ "$_ip" == "null" ]] || [[ "$_state" -ne 0 ]]; then
    echo "Unsuccessful ASN gathering."
  else
    echo "$_ip > $_asn"
  fi
}
```

Usage: `GetASN 1.1.1.1` → `1.1.1.1 > AS13335 Cloudflare, Inc.`

---

### Extract — smart archive extractor

```bash
# Single function to extract any archive type
extract() {
  if [ -f "$1" ]; then
    case "$1" in
      *.tar.bz2)   tar xjf "$1"     ;;
      *.tar.gz)    tar xzf "$1"     ;;
      *.bz2)       bunzip2 "$1"     ;;
      *.rar)       unrar e "$1"     ;;
      *.gz)        gunzip "$1"      ;;
      *.tar)       tar xf "$1"      ;;
      *.tbz2)      tar xjf "$1"     ;;
      *.tgz)       tar xzf "$1"     ;;
      *.zip)       unzip "$1"       ;;
      *.Z)         uncompress "$1"  ;;
      *.7z)        7z x "$1"        ;;
      *)           echo "'$1' cannot be extracted" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}
```

---

### myip — show public IP

```bash
myip() {
  curl -s https://api.ipify.org && echo
  # Alternative: curl -s https://ifconfig.me
}
```

---

### httpdebug — debug HTTP response with full timing

```bash
httpdebug() {
  curl -s -w "\n=== TIMING ===\n\
  Connect: %{time_connect}s\n\
  TTFB:    %{time_starttransfer}s\n\
  Total:   %{time_total}s\n\
  Speed:   %{speed_download} B/s\n\
  Size:    %{size_download} bytes\n\
  === RESPONSE ===\n" -o /dev/null "$1"
}
```

---

### killport — kill process on a port

```bash
killport() {
  local pid=$(lsof -ti:$1)
  if [ -n "$pid" ]; then
    kill -9 $pid
    echo "Killed process $pid on port $1"
  else
    echo "No process on port $1"
  fi
}
```

---

### docker-clean — remove all stopped containers, dangling images, unused networks

```bash
docker-clean() {
  echo "Removing stopped containers..."
  docker container prune -f
  echo "Removing dangling images..."
  docker image prune -f
  echo "Removing unused networks..."
  docker network prune -f
  echo "Removing build cache..."
  docker builder prune -f
}
```

---

### weather — quick weather from terminal

```bash
weather() {
  local city="${1:-}"
  if [ -n "$city" ]; then
    curl -s "wttr.in/$city?format=3"
  else
    curl -s "wttr.in?format=3"
  fi
}
```

---

### cheat — quick cheatsheet for a command

```bash
cheat() {
  curl -s "https://cheat.sh/$1"
}
```

---

## One-liner Functions (inline)

```bash
# Serve current directory via HTTP
python3 -m http.server 8000

# Quick JSON pretty-print
echo '{"foo":"bar"}' | python3 -m json.tool

# Watch a command every 2 seconds
watch -n 2 'ss -tulpn | grep 80'

# Monitor log in real-time with filter
tail -f /var/log/nginx/access.log | grep -E "500|502|503"

# Show disk usage summary
du -sh /* 2>/dev/null | sort -rh | head -10

# Backup file with timestamp
cp file.txt{,.bak.$(date +%Y%m%d_%H%M%S)}

# SSH with keepalive
ssh -o ServerAliveInterval=60 user@host

# Find large directories
du -h --max-depth=1 /var 2>/dev/null | sort -rh

# Colourised terminal (enable colours)
export CLICOLOR=1
export LSCOLORS=ExFxCxDxBxegedabagacad
```
