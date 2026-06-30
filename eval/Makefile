# eval/ — run wb-mqtt-voice system & CLI tests across two external axes.
# Design: ../../eval-commons/ARCHITECTURE.md (memory: test-run-axes).
#
#   make cli                                  # CLI contract tests — no service/key/fixtures (fastest)
#   make ws     TARGET=local                  # WS-audio system tests against a locally-running Irene
#   make ws     TARGET=wb7                     # ... against Irene on the WB7 controller (remote)
#   make ux     TARGET=local                   # only the DeepSeek-judged UX cases (needs DEEPSEEK_API_KEY)
#   make serve  CONFIG=embedded-armv7                 # bring Irene up LOCALLY with a chosen config (foreground)
#   make compare CONFIGS="embedded-armv7 standalone"    # run the WS suite against each config (LOCAL bring-up loop)
#   make view                                  # open the promptfoo results UI
#
# Two axes, both EXTERNAL to the test YAML:
#   TARGET — where the SUT is     → profiles/targets/<TARGET>.env  (WS_AUDIO_URL, HEALTH_URL, MQTT_*)
#   CONFIG — which config it runs  → profiles/configs/<CONFIG>.env  (IRENE_CONFIG_FILE), local bring-up only

TARGET    ?= local
CONFIG    ?= embedded-armv7
CONFIGS   ?= embedded-armv7 standalone
PROMPTFOO ?= promptfoo

# TEST-13 failure-trace capture (live WS). With TRACE=1, after the run the failing cases' traces are
# kept under FAILURES_DIR and the rest pruned — a failed case becomes replayable (`make replay`).
# The SUT must be launched with tracing writing into TRACES_DIR (e.g. `[trace] traces_dir`); on a
# remote TARGET, point TRACES_DIR at a path the SUT writes and you can read.
TRACE        ?= 0
TRACES_DIR   ?= traces/run
FAILURES_DIR ?= traces/failures

# uv-managed project venv: has irene + eval_commons, and its bin holds the console scripts.
# promptfoo shells out to PROMPTFOO_PYTHON for the Python providers/assertions; the cli_provider
# subprocess finds `irene-*` because we prepend the venv bin to PATH.
VENV_BIN := $(abspath ..)/.venv/bin
export PROMPTFOO_PYTHON := $(VENV_BIN)/python
export PATH := $(VENV_BIN):$(PATH)

# BUG-12: never serve cached results in this harness. Every surface here is a LIVE test — CLI
# contracts shell out to argparse, the WS suite hits a running SUT, the judge calls DeepSeek.
# promptfoo's response cache once captured a transient "ASR provider 'whisper' not available"
# (from a mis-launched SUT) and replayed it for every later run — masking the fixed SUT and never
# touching :6000. A test harness must always run live; correctness here beats cache speed.
export PROMPTFOO_CACHE_ENABLED := false

# Target profile (endpoint wiring) — always applied and exported to promptfoo's environment.
include profiles/targets/$(TARGET).env
export WS_AUDIO_URL HEALTH_URL MQTT_HOST MQTT_PORT
# Config profile (local bring-up only) — optional; ignored if absent.
-include profiles/configs/$(CONFIG).env
export IRENE_CONFIG_FILE

.DEFAULT_GOAL := help
.PHONY: help setup setup-record cli ws ux record record-list record-devices replay replay-judge serve compare view clean

RECORD := $(PROMPTFOO_PYTHON) -m eval_commons.record.cli --from-yaml ws.promptfooconfig.yaml --config profiles/recording.env

help:
	@sed -n 's/^#   //p' $(MAKEFILE_LIST) | head -8
	@echo ""
	@echo "TARGET=$(TARGET)  CONFIG=$(CONFIG)  ->  WS_AUDIO_URL=$(WS_AUDIO_URL)"

setup:                        ## install the shared providers into the project venv (uv)
	uv pip install --python $(PROMPTFOO_PYTHON) -e ../../eval-commons

setup-record:                 ## add the fixture recorder + mic deps (sounddevice, soxr) to the venv
	uv pip install --python $(PROMPTFOO_PYTHON) -e '../../eval-commons[record]'

cli:                          ## CLI contract tests (argparse console scripts) — no service needed
	$(PROMPTFOO) eval -c cli.promptfooconfig.yaml

ws:                           ## streaming-ASR system tests over /ws/audio (needs a running SUT; TRACE=1 keeps failing traces)
ifeq ($(TRACE),1)
	@$(PROMPTFOO) eval -c ws.promptfooconfig.yaml -o results-ws-$(TARGET).json; code=$$?; \
	  $(PROMPTFOO_PYTHON) -m eval_commons.failures --results results-ws-$(TARGET).json \
	    --traces-dir $(TRACES_DIR) --out $(FAILURES_DIR) --prune; \
	  exit $$code
else
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml -o results-ws-$(TARGET).json
endif

ux:                           ## only the DeepSeek-judged UX cases (needs DEEPSEEK_API_KEY)
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml --filter-metadata kind=ux

record:                       ## record missing voice fixtures interactively (mic; run `make setup-record` once first)
	$(RECORD) $(FIXTURE)      # e.g. make record  |  make record FIXTURE=timer_10min

record-list:                  ## show the fixture worklist (needed/missing + the line to read) — no mic
	$(RECORD) --list

record-devices:               ## list input devices to fill REC_INPUT_DEVICE in profiles/recording.env
	$(PROMPTFOO_PYTHON) -m eval_commons.record.cli --devices

replay:                       ## golden-trace regression — offline replay of recorded traces (needs models, no SUT)
	$(PROMPTFOO) eval -c trace.promptfooconfig.yaml -o results-replay.json

replay-judge:                 ## the trace-ux tier of the replay suite (DeepSeek-judged; needs DEEPSEEK_API_KEY)
	$(PROMPTFOO) eval -c trace.promptfooconfig.yaml --filter-metadata kind=trace-ux

serve:                        ## bring Irene up LOCALLY with CONFIG (foreground; Ctrl-C to stop)
	@echo ">> Irene local: IRENE_CONFIG_FILE=$(IRENE_CONFIG_FILE)  (serving for $(WS_AUDIO_URL))"
	cd .. && IRENE_CONFIG_FILE=$(IRENE_CONFIG_FILE) uv run irene-webapi --port 6000

# Local model/config comparison: bring the SUT up per config, run the WS suite, tear down.
# Writes results-ws-$(TARGET)-<config>.json per run. LOCAL only (remote = one TARGET=wb7 run).
compare:                      ## run the WS suite against each of CONFIGS (local bring-up loop)
	@for c in $(CONFIGS); do \
	  echo "=================  config: $$c  ================="; \
	  set -a; . profiles/configs/$$c.env; set +a; \
	  ( cd .. && IRENE_CONFIG_FILE=$$IRENE_CONFIG_FILE uv run irene-webapi --port 6000 ) & SUT=$$!; \
	  echo ">> waiting for $(HEALTH_URL) ..."; \
	  for i in $$(seq 1 40); do curl -sf "$(HEALTH_URL)" >/dev/null 2>&1 && break; sleep 1; done; \
	  $(PROMPTFOO) eval -c ws.promptfooconfig.yaml -o results-ws-$(TARGET)-$$c.json || true; \
	  kill $$SUT 2>/dev/null; wait $$SUT 2>/dev/null || true; \
	done

view:                         ## open the promptfoo results UI
	$(PROMPTFOO) view

clean:                        ## remove generated result files
	rm -f results-*.json
