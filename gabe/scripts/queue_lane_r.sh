#!/bin/bash
# Lane R: the evaluations lost on Nov 8 (PROGRESS 38), one at a time: lane O (x0.7 with true friction),
# lane P (relaxed opponent check), then the rest of lane M (stress tests). Each lane skips finished outputs.
cd "$(dirname "$0")/.."
echo "$(date +%H:%M) start" >> runs/_lane_r.log
bash scripts/queue_lane_o.sh; bash scripts/queue_lane_p.sh; bash scripts/queue_lane_m.sh
echo "$(date +%H:%M) all done" >> runs/_lane_r.log
