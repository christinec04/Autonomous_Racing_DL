#!/bin/bash
# usage: run_and_capture.sh <world name> <shots dir> <hires dir> <last movie name>
# Runs the world in Webots, waits for the supervisor to finish, saves the window and one frame per movie.
P=/c/Users/shore/robotics/racing_proposal
WEBOTS="/c/Users/shore/AppData/Local/Programs/Webots/msys64/mingw64/bin/webots.exe"
cd "$P" || exit 1
mkdir -p "$3"
touch "$P/$2/stay.flag"
mv -f "$P/$2/$4.mp4" "$P/$2/$4.prev.mp4" 2>/dev/null
("$WEBOTS" --batch --fullscreen --mode=realtime "C:/Users/shore/robotics/racing_proposal/worlds/$1.wbt" >/dev/null 2>&1 &)
for i in $(seq 1 70); do
  if [ -f "$P/$2/$4.mp4" ]; then break; fi
  timeout 5 ping -n 4 127.0.0.1 >/dev/null
done
timeout 14 ping -n 12 127.0.0.1 >/dev/null
powershell -NoProfile -ExecutionPolicy Bypass -File "$P/tools/grab_window.ps1" "C:\\Users\\shore\\robotics\\racing_proposal\\$3\\00_webots_window.png"
rm -f "$P/$2/stay.flag"
for f in "$P/$2"/0*.mp4; do
  n=$(basename "$f" .mp4)
  case "$n" in *.prev) continue;; esac
  ffmpeg -y -loglevel error -sseof -0.2 -i "$f" -frames:v 1 -update 1 "$P/$3/$n.png"
done
ls "$P/$3"
