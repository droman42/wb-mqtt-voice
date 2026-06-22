"""
Unified Text Processor Provider (QUAL-13)

The single config-driven text processor. Replaces the 4 stage-specific providers
(asr/general/tts/number), which were an over-engineered shell around one number-normalizing
call (the stage routing was decorative; only `general` ever ran; TTS got no normalization).

Stages are now DATA, not classes: per-normalizer stage lists are read from config
(`[text_processor.normalizers.<name>].stages`). `process_pipeline(text, stage)` applies, in a
fixed order (numbers → prepare → runorm), each *enabled* normalizer whose stage list includes
the requested stage. So `asr_output` and `tts_input` are real chains, configurable per deployment.
"""

import logging
from typing import Dict, Any, List, Set

from .base import TextProcessingProvider
from ...utils.text_normalizers import NumberNormalizer, PrepareNormalizer, RunormNormalizer

logger = logging.getLogger(__name__)

# Fixed application order — numbers first (so symbols/Latin see words), then prepare, then the
# heavy RUNorm last (TTS-only). A normalizer only runs if it's enabled AND maps to the stage.
NORMALIZER_ORDER = ["numbers", "prepare", "runorm"]


class UnifiedTextProcessor(TextProcessingProvider):
    """One processor, config-driven per-stage normalizer chains (QUAL-13)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enabled = config.get("enabled", True)
        self._normalizers_cfg: Dict[str, Dict[str, Any]] = config.get("normalizers", {})
        self.normalizers: Dict[str, Any] = {}          # name -> normalizer instance (enabled only)
        self.stage_map: Dict[str, Set[str]] = {}        # name -> {stages it applies to}
        self._built = False

    def get_provider_name(self) -> str:
        return "unified_text_processor"

    def _build_normalizers(self) -> None:
        """Instantiate the enabled normalizers + record their stage lists (once)."""
        if self._built:
            return
        for name in NORMALIZER_ORDER:
            nc = self._normalizers_cfg.get(name, {})
            if not nc.get("enabled", False):
                continue
            try:
                inst = self._build_one(name, nc)
            except Exception as e:
                logger.error(f"UnifiedTextProcessor: failed to build normalizer '{name}': {e}")
                continue
            if inst is None:
                continue
            self.normalizers[name] = inst
            self.stage_map[name] = set(nc.get("stages", []))
        self._built = True
        logger.info(f"UnifiedTextProcessor: enabled normalizers {list(self.normalizers)} "
                    f"with stage map { {k: sorted(v) for k, v in self.stage_map.items()} }")

    def _build_one(self, name: str, nc: Dict[str, Any]):
        # QUAL-38: a normalizer's language is the DEPLOYMENT/audio-model language (which language's
        # number-spelling rules to apply), config-driven per normalizer — NOT the session language.
        # (Spelling numbers in the session language but synthesizing with a different-language voice
        # would mismatch.) The "ru" fallback is the Russian-first deployment default. The normalizer
        # routes ru through the dependency-free pure-Python path and non-ru through ovos-number-parser.
        norm_language = nc.get("language", "ru")
        if name == "numbers":
            return NumberNormalizer(language=norm_language)
        if name == "prepare":
            opts = {
                "changeNumbers": nc.get("change_numbers", "process"),
                "changeLatin": "process" if nc.get("latin_to_cyrillic", True) else "no_process",
                "changeSymbols": nc.get("change_symbols", r"#$%&*+-/<=>@~[\]_`{|}№"),
                "keepSymbols": nc.get("keep_symbols", r",.?!;:() "),
                "deleteUnknownSymbols": nc.get("delete_unknown_symbols", True),
            }
            return PrepareNormalizer(options=opts, language=norm_language)
        if name == "runorm":
            return RunormNormalizer(options={"modelSize": nc.get("model_size", "small"),
                                             "device": nc.get("device", "cpu")})
        logger.warning(f"UnifiedTextProcessor: unknown normalizer '{name}' in config, ignoring")
        return None

    async def is_available(self) -> bool:
        if not self.enabled:
            self._set_status(self.status.__class__.UNAVAILABLE, "Text processor disabled in config")
            return False
        self._build_normalizers()
        self._set_status(self.status.__class__.AVAILABLE)
        return True

    async def process_pipeline(self, text: str, stage: str) -> str:
        """Apply the configured normalizer chain for `stage`, in NORMALIZER_ORDER."""
        if not text:
            return text
        self._build_normalizers()
        out = text
        for name in NORMALIZER_ORDER:
            if name in self.normalizers and stage in self.stage_map.get(name, set()):
                try:
                    out = await self.normalizers[name].normalize(out)
                except Exception as e:
                    logger.warning(f"UnifiedTextProcessor: normalizer '{name}' failed at stage "
                                   f"'{stage}': {e}")
        return out

    def get_supported_stages(self) -> List[str]:
        self._build_normalizers()
        stages: Set[str] = set()
        for s in self.stage_map.values():
            stages |= s
        return sorted(stages)

    def normalizers_for_stage(self, stage: str) -> List[str]:
        """The ordered normalizer names that run for `stage` (introspection for the WebAPI)."""
        self._build_normalizers()
        return [n for n in NORMALIZER_ORDER
                if n in self.normalizers and stage in self.stage_map.get(n, set())]

    def get_capabilities(self) -> Dict[str, Any]:
        self._build_normalizers()
        return {
            "supported_stages": self.get_supported_stages(),
            "normalizers": list(self.normalizers),
            "stage_map": {k: sorted(v) for k, v in self.stage_map.items()},
        }

    def validate_config(self) -> bool:
        if not isinstance(self._normalizers_cfg, dict):
            self.logger.error("text_processor.normalizers must be a table")
            return False
        return True

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        # All optional: ru number-normalization is dependency-free (pure-Python fallback). The extras
        # add ovos-number-parser (non-ru numbers), eng-to-ipa (Latin→Cyrillic), runorm (TTS RUNorm).
        return []

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
    async def cleanup(self) -> None:
        runorm = self.normalizers.get("runorm")
        if runorm is not None and hasattr(runorm, "cleanup"):
            await runorm.cleanup()
        self.normalizers.clear()
        self.stage_map.clear()
        self._built = False
        self._set_status(self.status.__class__.UNKNOWN)
