#!/bin/zsh
cd /Users/aom/Desktop/Workspace/claude/blm-btc/solver
while pgrep -f "batch.py t21c.txt" > /dev/null; do sleep 15; done
echo "=== $(date +%H:%M) narrow t21c finished; starting WIDE re-runs (101 paths/seed) ===" >> logs/wide.log
echo "--- t21c WIDE: 60-pool, 5 free slots, 777.6M ---" >> logs/wide.log
BLM_WIDE=1 python3 batch.py t21c.txt 2>&1 | tr '\r' '\n' | grep -E "combos|done in|HIT|BATCH DONE|Traceback" >> logs/wide.log
echo "--- t21b WIDE: 20-pool, 7 free slots, 1.28B ---" >> logs/wide.log
BLM_WIDE=1 python3 batch.py t21b.txt 2>&1 | tr '\r' '\n' | grep -E "combos|done in|HIT|BATCH DONE|Traceback" >> logs/wide.log
echo "=== $(date +%H:%M) ALL WIDE RE-RUNS FINISHED ===" >> logs/wide.log
