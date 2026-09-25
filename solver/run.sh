#!/bin/zsh
# Launch a search in its OWN process group so stop.sh can kill parent AND spawned workers.
# macOS has no `setsid`; use a Python shim that calls os.setsid() then execs the command.
# usage: ./run.sh <name> <command...>   e.g. ./run.sh t21d env BLM_PATHS=n2 python3 -u gpu/hybrid.py t21d.txt
cd /Users/aom/Desktop/Workspace/claude/blm-btc/solver
name=$1; shift
: > logs/$name.log
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' "$@" > logs/$name.log 2>&1 &
pid=$!
echo $pid > logs/$name.pid
sleep 1
pgid=$(ps -o pgid= -p $pid 2>/dev/null | tr -d ' ')
echo "started '$name' pid $pid pgid ${pgid:-?} -> logs/$name.log"
