# eval/ — run locveil-voice system & CLI tests across two external axes.
# Design: ../../locveil-commons/eval/ARCHITECTURE.md (memory: test-run-axes).
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

# EVAL_LANG (I18N-5) — which language's fixtures/traces/cases a run uses. Test cases are duplicated
# per language (tagged metadata.language) and reference fixtures/{{env.EVAL_LANG}}/… so a run selects
# one language via the case filter + the fixture subdir. Derived from the CONFIG name (`*-en` → en)
# so it tracks the SUT config automatically; override explicitly for a remote (wb7) SUT.
# NOT named LANG: that is the POSIX locale var and would leak into the SUT/promptfoo environment.
EVAL_LANG ?= $(if $(filter %-en,$(CONFIG)),en,ru)
# Room name for the WS registration — echoed in the "no devices in session <room>" failure reply, so
# it must match the run language (else an English reply carries a Russian room word and fails the rubric).
EVAL_ROOM ?= $(if $(filter en,$(EVAL_LANG)),Kitchen,Кухня)

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
export WS_AUDIO_URL HEALTH_URL MQTT_HOST MQTT_PORT EXECUTE_URL BRIDGE_CAPTURE_URL
# Config profile (local bring-up only) — optional; ignored if absent.
-include profiles/configs/$(CONFIG).env
export IRENE_CONFIG_FILE
# EVAL_LANG is read by the test YAML as {{env.EVAL_LANG}} (fixture/trace subdir) and drives the
# per-language case filter below; EVAL_ROOM is read as {{env.EVAL_ROOM}}.
export EVAL_LANG EVAL_ROOM

.DEFAULT_GOAL := help
.PHONY: help setup setup-record cli device device-tests device-sut-config device-auto ws ux record record-list record-devices replay replay-judge serve compare view clean

RECORD := $(PROMPTFOO_PYTHON) -m eval_commons.record.cli --from-yaml ws.promptfooconfig.yaml --config profiles/recording.env

help:
	@sed -n 's/^#   //p' $(MAKEFILE_LIST) | head -8
	@echo ""
	@echo "TARGET=$(TARGET)  CONFIG=$(CONFIG)  EVAL_LANG=$(EVAL_LANG)  ->  WS_AUDIO_URL=$(WS_AUDIO_URL)"

setup:                        ## install the shared providers into the project venv (uv)
	uv pip install --python $(PROMPTFOO_PYTHON) -e ../../locveil-commons/eval

setup-record:                 ## add the fixture recorder + mic deps (sounddevice, soxr) to the venv
	uv pip install --python $(PROMPTFOO_PYTHON) -e '../../locveil-commons/eval[record]'

cli:                          ## CLI contract tests (argparse console scripts) — no service needed
	$(PROMPTFOO) eval -c cli.promptfooconfig.yaml

# TEST-18 Slice B — producer contract tests: utterance → captured canonical DeviceCommand,
# asserted against the PINNED crossover fixtures (../../locveil-commons/contracts/pins/). The SUT must
# point [outputs.bridge] at the mock bridge; `device-auto` wires everything for one local run.
FIXTURES_JSON := ../../locveil-commons/contracts/pins/crossover-fixtures/crossover_fixtures.json
MOCK_BRIDGE_PORT ?= 8010

device-tests:                 ## regenerate device.tests.yaml from the pinned crossover fixtures
	$(PROMPTFOO_PYTHON) -m eval_commons.fixtures_to_tests $(FIXTURES_JSON) > device.tests.yaml

# -j 1: cases share per-room SUT sessions (room_alias → one session per room), so parallel
# runs interleave turns of the same conversation — inherent cross-talk, not a flake.
# TIER=1 (default) is the green gate; TIER=2 is the QUAL-35 Slice-3 hard-phrasing scoreboard
# (red until built); TIER=all runs both. Result files carry the tier so runs don't clobber.
TIER ?= 1
DEVICE_TIER_FILTER := $(if $(filter all,$(TIER)),,--filter-metadata tier=$(TIER))
device: device-tests          ## producer contract suite (needs SUT + mock bridge running; see device-auto)
	$(PROMPTFOO) eval -c device.promptfooconfig.yaml -j 1 $(DEVICE_TIER_FILTER) -o results-device-$(TARGET)-t$(TIER).json

# The SUT config is DERIVED from config-master at run time (env can't override nested TOML
# sections — pydantic-settings gives init kwargs priority), flipping [outputs.bridge] at the mock.
DEVICE_SUT_CONFIG := /tmp/irene-device-sut.toml

device-sut-config:
	@sed -e '/^\[outputs.bridge\]/,/^\[/{s|^enabled = false|enabled = true|;s|^base_url = .*|base_url = "http://localhost:$(MOCK_BRIDGE_PORT)"|;}' \
	  ../configs/config-master.toml > $(DEVICE_SUT_CONFIG)
ifeq ($(NLU),llm)
# QUAL-35 Slice-3 measurement leg: append the QUAL-50 LLM tier to the cascade (deterministic
# tiers still run first; needs DEEPSEEK_API_KEY in the environment for the tier to answer).
	@sed -i -e 's|^provider_cascade_order = .*|provider_cascade_order = ["hybrid_keyword_matcher", "spacy_nlu", "llm"]|' \
	  -e '/^\[nlu.providers.llm\]/,/^\[/{s|^enabled = false|enabled = true|;}' $(DEVICE_SUT_CONFIG)
	@grep -n '^provider_cascade_order' $(DEVICE_SUT_CONFIG)
endif
	@grep -A3 '^\[outputs.bridge\]' $(DEVICE_SUT_CONFIG) | head -4

device-auto: device-tests device-sut-config  ## one-shot local run: mock bridge + SUT up → suite → teardown
	@pkill -f "[e]val_commons.mock_bridge" 2>/dev/null; sleep 0.5; true  # stale mock on the port = stale golden served silently ([e] keeps pkill from matching THIS shell)
	@$(PROMPTFOO_PYTHON) -m eval_commons.mock_bridge --catalog ../../locveil-commons/contracts/pins/catalog/catalog.golden.json --port $(MOCK_BRIDGE_PORT) & MOCK=$$!; \
	( cd .. && .venv/bin/irene-webapi -c $(DEVICE_SUT_CONFIG) --port 6000 >/tmp/irene-device-eval.log 2>&1 ) & SUT=$$!; \
	echo ">> waiting for $(HEALTH_URL) ..."; \
	for i in $$(seq 1 60); do curl -sf "$(HEALTH_URL)" >/dev/null 2>&1 && break; sleep 1; done; \
	$(PROMPTFOO) eval -c device.promptfooconfig.yaml -j 1 $(DEVICE_TIER_FILTER) -o results-device-$(TARGET)-t$(TIER).json; code=$$?; \
	kill $$SUT $$MOCK 2>/dev/null; wait $$SUT $$MOCK 2>/dev/null; exit $$code

ws:                           ## streaming-ASR system tests over /ws/audio (needs a running SUT; TRACE=1 keeps failing traces)
ifeq ($(TRACE),1)
	@$(PROMPTFOO) eval -c ws.promptfooconfig.yaml --filter-metadata language=$(EVAL_LANG) -o results-ws-$(TARGET)-$(EVAL_LANG).json; code=$$?; \
	  $(PROMPTFOO_PYTHON) -m eval_commons.failures --results results-ws-$(TARGET)-$(EVAL_LANG).json \
	    --traces-dir $(TRACES_DIR) --out $(FAILURES_DIR) --prune; \
	  exit $$code
else
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml --filter-metadata language=$(EVAL_LANG) -o results-ws-$(TARGET)-$(EVAL_LANG).json
endif

ux:                           ## only the DeepSeek-judged UX cases (needs DEEPSEEK_API_KEY)
	$(PROMPTFOO) eval -c ws.promptfooconfig.yaml --filter-metadata kind=ux --filter-metadata language=$(EVAL_LANG)

record:                       ## record missing voice fixtures interactively (mic; run `make setup-record` once first)
	$(RECORD) $(FIXTURE)      # e.g. make record  |  make record FIXTURE=timer_10min

record-list:                  ## show the fixture worklist (needed/missing + the line to read) — no mic
	$(RECORD) --list

record-devices:               ## list input devices to fill REC_INPUT_DEVICE in profiles/recording.env
	$(PROMPTFOO_PYTHON) -m eval_commons.record.cli --devices

replay:                       ## golden-trace regression — offline replay of recorded traces (needs models, no SUT)
	$(PROMPTFOO) eval -c trace.promptfooconfig.yaml --filter-metadata language=$(EVAL_LANG) -o results-replay-$(EVAL_LANG).json

replay-judge:                 ## the trace-ux tier of the replay suite (DeepSeek-judged; needs DEEPSEEK_API_KEY)
	$(PROMPTFOO) eval -c trace.promptfooconfig.yaml --filter-metadata kind=trace-ux --filter-metadata language=$(EVAL_LANG)

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
