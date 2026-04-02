#!/usr/bin/env bash
# Run backend and frontend in parallel; Ctrl+C kills both cleanly.

# Recursively collect all descendant PIDs
descendants() {
    local children
    children=$(pgrep -P "$1" 2>/dev/null)
    for child in $children; do
        descendants "$child"
    done
    echo "$children"
}

cleanup() {
    local pids
    pids=$(descendants $$)
    [ -n "$pids" ] && kill $pids 2>/dev/null
    # Give processes time for graceful shutdown
    sleep 1
    # Force-kill any survivors
    pids=$(descendants $$)
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null
    wait 2>/dev/null
    exit 0
}

trap cleanup INT TERM

(cd "${BACKEND:-backend}" && exec uvicorn app.main:app --reload) &
(cd "${FRONTEND:-frontend}" && exec npm run dev) &
wait
