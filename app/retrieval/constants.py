"""Every threshold in the retrieval pipeline. No magic numbers in logic.

Values sourced from 03_retrieval_engine.md. Weights are starting points only —
tuned on the tune split per 01_evaluation_protocol.md §13, then locked here
with the date.
"""

EMBEDDING_DIM = 384
MAX_MODEL_TOKENS = 256  # all-MiniLM-L6-v2 truncates silently past this

WEIGHT_VECTOR = 0.50  # tuned on tune split, locked <date>
WEIGHT_FILE_OVERLAP = 0.30
WEIGHT_BM25 = 0.20

REASON_HIGH_VECTOR = 0.70  # reason template rules 1 and 3
REASON_HIGH_BM25 = 0.70  # rule 4

CANDIDATE_TOP_N = 50
RESULTS_RETURNED = 3

# 03 §3. The model is part of the evaluation methodology: a version bump
# changes the embeddings and invalidates every published number (06 §11)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# 06 §9: batch always. One encode call per hunk is roughly an order of
# magnitude slower and turns the Day-19 index run into an overnight job.
EMBED_BATCH_SIZE = 32

# 03 §4 step 2 — the vector signal's contribution to the candidate set.
# Not the display count: 09's "top 10" for Day 17 is a parameter, not this.
VECTOR_TOP_K = 50

# Chunk → PR aggregation across the query PR's chunks (03 §5).
# "max" is v1; "mean_top_k" is the flagged alternative. Both are compared on
# the tune split at Day 34 — do not pick a winner here.
VECTOR_AGGREGATION = "max"
MEAN_TOP_K = 3
