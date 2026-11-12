#!/bin/sh
# POSIX bootstrap; also supports Git Bash (MSYS/MINGW), distinct from WSL.
runtime_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
runtime_root=$(dirname -- "$runtime_dir")
probe_code='import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'

probe_python() {
    "$@" -c "$probe_code" </dev/null >/dev/null 2>&1 &
    probe_pid=$!
    # A watchdog bounds aliases/shims even on systems without GNU timeout.
    (sleep 5; kill "$probe_pid" 2>/dev/null) >/dev/null 2>&1 &
    watchdog_pid=$!
    wait "$probe_pid"
    probe_status=$?
    kill "$watchdog_pid" 2>/dev/null
    wait "$watchdog_pid" 2>/dev/null
    return "$probe_status"
}

launch_if_valid() {
    bootstrap=$1
    shift
    if probe_python "$bootstrap"; then
        exec "$bootstrap" "$runtime_dir/factory_python.py" "$@"
    fi
}

if [ -n "${AIDLC_PYTHON:-}" ]; then
    launch_if_valid "$AIDLC_PYTHON" "$@"
fi
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) native_windows=yes; venv_suffix=Scripts/python.exe ;;
    *) native_windows=no; venv_suffix=bin/python ;;
esac
launch_if_valid "$runtime_root/.venv/$venv_suffix" "$@"
if [ -n "${VIRTUAL_ENV:-}" ]; then
    launch_if_valid "$VIRTUAL_ENV/$venv_suffix" "$@"
fi
if [ "$native_windows" = yes ]; then
    launch_if_valid python "$@"
    if probe_python py -3; then
        exec py -3 "$runtime_dir/factory_python.py" "$@"
    fi
    launch_if_valid python3 "$@"
else
    launch_if_valid python3 "$@"
    launch_if_valid python "$@"
fi
echo '[AIDLC Python] Python >=3.10 not found. Install Python or set AIDLC_PYTHON to its executable path.' >&2
exit 1
