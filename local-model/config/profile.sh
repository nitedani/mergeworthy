# The model, sourced by serve.sh, claude-local and the sandbox. Sizes and speeds were measured on one 16 GB GPU with the
# desktop using ~1.2 GB, leaving 1 GB of VRAM free at peak (prompt processing included); re-measure for yours.
_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LLM_PROFILE=gsq  # the name serve.sh uses to notice a changed setup
# Qwen3.8-27B, GSQ-RCO IQ3_XXS (ISTA-DASLab) with its MTP head: 160K at 4-bit KV peaks at 15.05 GB, 132 tok/s.
# K and V must have the same type: mixed types lose the fast kernels (68 tok/s decode, ~40 tok/s prompt).
LLM_MODEL="Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf"
LLM_ARGS=(-ctk q4_0 -ctv q4_0 --spec-type draft-mtp --mmproj "$_dir/weights/mmproj-gsq-Qwen3.8-27B-BF16.gguf")
# Vision (screenshots the agent takes and reads): the projector runs on the CPU, so it costs no VRAM.
LLM_ARGS+=(--no-mmproj-offload)
LLM_CTX="${LLM_CTX:-163840}"
