#!/bin/bash
source .venv/bin/activate
nohup python demo_bot.py secret.json &
nohup python demo_bot.py secret2.json &