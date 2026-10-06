#!/bin/bash
# Serve Ollama's qwen3.5:9b (Apache-2.0 GGUF, Q4_K_M) with 4 parallel slots through llama.cpp's server, which Ollama bundles. Ollama itself cannot batch this architecture
# ("model architecture does not currently support parallel requests: qwen35"), so a plain `ollama serve` is limited to one request at a time (~46 tok/s; 4 slots here give ~86).
# GGML_BACKEND_PATH is required: without it llama-server silently runs on the CPU (7 tok/s). Thinking is switched off in the chat-template arguments.
#   scripts/serve_llm.sh            -> http://127.0.0.1:11600/v1   (stop it with: kill <pid>)
set -euo pipefail
L="$HOME/.local/ollama/lib/ollama"
BLOB="${BLOB:-$HOME/.ollama/models/blobs/sha256-dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c}"
CTX="${CTX:-65536}"          # total; each of the 4 slots gets CTX/4 tokens
GGML_BACKEND_PATH="$L/cuda_v13/libggml-cuda.so" LD_LIBRARY_PATH="$L:$L/cuda_v13" exec "$L/llama-server" \
  -m "$BLOB" -ngl 99 -c "$CTX" -np 4 -fa on -ctk q8_0 -ctv q8_0 --host 127.0.0.1 --port 11600 --jinja \
  --chat-template-kwargs '{"enable_thinking": false}'
