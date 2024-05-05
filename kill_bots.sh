#!/bin/bash

# Find all running python processes with "demo_bot.py" as an argument
pids=$(ps -ef | grep -E "python.*demo_bot.py" | grep -v grep | awk '{print $2}')

# Terminate each process found
for pid in $pids; do
  echo "Terminating process with PID: $pid"
  kill $pid
done