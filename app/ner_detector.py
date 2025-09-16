"""
Model 1: NER PII/PHI Detector (inference)
-----------------------------------------
• Loads a fine-tuned Hugging Face token-classification model
• Exposes PiiNer.predict(text) → span list [{start,end,label,score,text}]
• Also includes a simple masker for quick redaction

Train a model with scripts/train_ner.py, then point model_dir to it.
"""

from dataclasses import dataclass
from typing import List, Optional

from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification


@dataclass
class Entity:
    start: int
    end: int
    label: str
    score: float
    text: str


class PiiNer:
    def __init__(
        self,
        model_dir: str = "models/pii_ner_distilbert",
        aggregation_strategy: str = "simple",  # "none" | "simple" | "first" | "average" | "max"
        device: Optional[int] = None,  # set to 0 for GPU, or leave None for auto
    ):
        # Load tokenizer & model from a local directory (produced by train_ner.py)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir)
        self.pipe = pipeline(
            task="token-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy=aggregation_strategy,
            device=device,
        )

    def predict(self, text: str, score_threshold: float = 0.5) -> List[Entity]:
        """Run NER and return a list of Entity spans."""
        raw = self.pipe(text)
        ents: List[Entity] = []
        for r in raw:
            if float(r.get("score", 0.0)) < score_threshold:
                continue
            label = str(r.get("entity_group") or r.get("entity"))
            start, end = int(r["start"]), int(r["end"])
            ents.append(
                Entity(
                    start=start,
                    end=end,
                    label=label,
                    score=float(r["score"]),
                    text=text[start:end],
                )
            )
        return ents

    # ---------- Optional helpers for quick masking ----------

    def mask(self, text: str, entities: List[Entity], mode: str = "redact") -> str:
        """
        mode = "redact" → replace span with [REDACTED:<LABEL>]
             = "partial" → keep last 4 digits for numbers, keep email domains
        """
        s = text
        for e in sorted(entities, key=lambda x: x.start, reverse=True):
            repl = (
                f"[REDACTED:{e.label}]"
                if mode == "redact"
                else self._partial_mask(text[e.start : e.end], e.label)
            )
            s = s[: e.start] + repl + s[e.end :]
        return s

    def _partial_mask(self, value: str, label: str) -> str:
        v = value
        if "EMAIL" in label.upper() and "@" in v:
            user, dom = v.split("@", 1)
            return "[REDACTED_EMAIL]@" + dom
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 4:
            return "[REDACTED]****" + digits[-4:]
        return "[REDACTED]"


if __name__ == "__main__":
    # Simple smoke test (requires a trained model at models/pii_ner_distilbert)
    try:
        ner = PiiNer()
        txt = "I am John jha, my email is john.smith@example.com and  is 123-45-6789."
        ents = ner.predict(txt, score_threshold=0.3)
        for e in ents:
            print(e)
        print("Masked:", ner.mask(txt, ents, mode="partial"))
    except Exception as e:
        print("Load a trained model first (see scripts/train_ner.py). Error:", e)
