# eval/ — run wb-mqtt-voice system & CLI tests across two external axes.
# Design: ../../eval-commons/ARCHITECTURE.md (memory: test-run-axes).
#
#   make cli                                  # CLI contract tests — no service/key/fixtures (fastest)
#   make ws     TARGET=local                  # WS-audio system tests against a locally-running Irene
#   make ws     TARGET=wb7                     # ... against Irene on the WB7 controller (remote)
#   make ux     TARGET=local                   # only the DeepSeek-judged UX cases (needs DEEPSEEK_API_KEY)
#   make serve  CONFIG=voice                   # bring Irene up LOCALLY with a chosen config (foreground)
#   make compare CONFIGS="voice standalone"    # run the WS suite against each config (LOCAL bring-up loop)
#   make view                                  # open the promptfoo results UI
#
# Two axes, both EXTERNAL to the test YAML:
#   TARGET — where the SUT is     → profiles/targets/<TARGET>.env  (WS_AUDIO_URL, HEALTH_URL, MQTT_*)
#   CONFIG — which config it runs  → profiles/configs/<CONFIG>.env  (IRENE_CONFIG_FILE), local bring-up only

TARGET    ?= local
CONFIG    ?= voice
CONFIGS   ?= voice standalone
PROMPTFOO ?= promptfoo

# uv-managed project venv: has irene + eval_commons, and its bin holds the console scripts.
# promptfoo shells out to PROMPTFOO_PYTHON for the Python providers/assertions; the cli_provider
# subprocess finds `irene-*` because we prepend the venv bin to PATH.
VENV_BIN := $(abspath ..)/.venv/bin
export PROMPTFOO_PYTHON := $(VENV_BIN)/python
export PATH := $(VENV_BIN):$(PATH)

# Target profile (endpoint wiring) — always applied and exported to promptfoo's environment.
include profiles/targets/$(TARGET).env
export WS_AUDIO_URL HEALTH_URL MQTT_HOST MQTT_PORT
# Config profile (local bring-up only) — optional; ignored if absent.
-include profiles/configs/$(CONFIG).env
export IRENE_CONFIG_FILE

.DEFAULT_GOAL := help
.PHONY: help setup cli ws ux serve compare view clean

help:
	@sed -n 's/^#   //p' $(MAKEFILE_LIST) | head -8
	@echo ""
	@echo "TARGET=$(TARGET)  CONFIG=$(CONFIG)  ->  WS_AUDIO_URL=$(WS_AUDIO_URL)"

setup:                        ## install the shared providers into the project venv (uv)
	uv pip install --python $(PROMPTFOO_PYTHON) -e ../../eval-commons

cli:                          ## CLI contract tests (argparse console scripts) — no service needed
	$(PROMPTFOO) eval -c cli.promptfooconfig.yaml

ws:                           ## streaming-ASR system tests over /ws/audio (needs a running SUT)
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml -o results-ws-$(TARGET).json

ux:                           ## only the DeepSeek-judged UX cases (needs DEEPSEEK_API_KEY)
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml --filter-metadata kind=ux

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
