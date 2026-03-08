#!/bin/bash
# Start the Discord bot in the background
python -m bot.main &

# Start Streamlit dashboard on port 7860 (required by HF Spaces)
streamlit run dashboard/app.py \
  --server.port=7860 \
  --server.address=0.0.0.0 \
  --server.headless=true
