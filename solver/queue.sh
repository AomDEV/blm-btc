#!/bin/zsh
# Run a list of searches one after another, inside ONE run.sh job (so stop.sh <name> kills it all).
#   ./run.sh q3 ./queue.sh queue3.lst
# Each non-blank, non-# line of the list is a shell command run from the solver dir, e.g.
#   BLM_BLMC_ARGS="--paths ext" python3 -u gpu/cgpu.py t21f.txt
#   python3 -u gpu/cgpu.py t21f.txt@passlist.txt
# After every entry the log shows the wall time and HIT.txt (if any). A hit does not stop the queue:
# later frames may hold a second solution and the log line is what you read anyway.
cd "${0:A:h}"
list=$1
[ -r "$list" ] || { echo "queue.sh: cannot read '$list'"; exit 2; }
n=0
while IFS= read -r line || [ -n "$line" ]; do
  [[ -z "${line// /}" || "$line" == \#* ]] && continue
  n=$((n + 1)); t0=$(date +%s)
  echo "=== [$n] $(date '+%F %T') START: $line"
  eval "$line"; rc=$?
  echo "=== [$n] $(date '+%F %T') END rc=$rc after $(( $(date +%s) - t0 ))s: $line"
  [ -s HIT.txt ] && { echo "=== HIT.txt now:"; cat HIT.txt; }
done < "$list"
echo "=== queue '$list' finished: $n entries, $(date '+%F %T')"
