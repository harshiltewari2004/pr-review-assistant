"""Every threshold in the retrieval pipeline. No magic numbers in logic.

Values sourced from 03_retrieval_engine.md. Weights are starting points only —
tuned on the tune split per 01_evaluation_protocol.md §13, then locked here
with the date.
"""

EMBEDDING_DIM       = 384
MAX_MODEL_TOKENS    = 256      # all-MiniLM-L6-v2 truncates silently past this

WEIGHT_VECTOR       = 0.50     # tuned on tune split, locked <date>
WEIGHT_FILE_OVERLAP = 0.30
WEIGHT_BM25         = 0.20

REASON_HIGH_VECTOR  = 0.70     # reason template rules 1 and 3
REASON_HIGH_BM25    = 0.70     # rule 4

CANDIDATE_TOP_N     = 50
RESULTS_RETURNED    = 3
