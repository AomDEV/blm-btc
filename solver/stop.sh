#!/bin/zsh
# Stop a search launched by run.sh: kills the whole process group, so no orphaned Pool workers.
# usage: ./stop.sh <name>     or   ./stop.sh --orphans   (kill any ppid-1 worker burning cpu)
cd "${0:A:h}"                       # the solver dir this script lives in - never hardcode it
if [ "$1" = "--orphans" ]; then
  # match blmc too, not just Python: the C engine is spawned by cgpu.py and outlives a killed parent
  ps -eo pid,ppid,pcpu,command | grep -E "[P]ython|[p]ython3|[b]lmc" | awk '$2==1 && $3>5 {print $1}' \
    | while read p; do kill -9 $p && echo "killed orphan $p"; done
  exit 0
fi
name=$1; pid=$(cat logs/$name.pid 2>/dev/null)
[ -z "$pid" ] && { echo "no pid file for '$name'"; exit 1; }
pgid=$(ps -o pgid= -p $pid | tr -d ' ')
if [ -n "$pgid" ]; then kill -TERM -- -$pgid 2>/dev/null; sleep 2; kill -KILL -- -$pgid 2>/dev/null; echo "stopped '$name' (process group $pgid)"; else echo "'$name' not running"; fi
rm -f logs/$name.pid
