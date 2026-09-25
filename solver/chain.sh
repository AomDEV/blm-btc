#!/bin/zsh
cd /Users/aom/Desktop/Workspace/claude/blm-btc/solver
# wait for the corrected 479M permutation to finish
while pgrep -f "solve.py permute" > /dev/null; do sleep 20; done
echo "=== permute finished, resuming two-slot 15-word sweep ===" >> logs/chain.log
python3 batch.py hyp3_two.txt >> logs/batch3b.log 2>&1
echo "=== batch3b finished ===" >> logs/chain.log
