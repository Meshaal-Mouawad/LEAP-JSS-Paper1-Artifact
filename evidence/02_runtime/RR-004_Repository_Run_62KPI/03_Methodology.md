# Methodology

The original execution document is preserved without modification. Summary values are transcribed from four complete run blocks in that source. A run is classified as deterministic-only when the optional AI stage reports 0.00 s or negligible 0.01 s total latency and no substantive model contribution is recorded.

The legacy logger printed a generic AI-phase line even for these deterministic-only executions. That wording is retained only inside the immutable raw document. It is not used to classify the run, and execution-worker wording is omitted from processed summaries. The current backend behavior reported by the project owner no longer emits that line when AI is disabled.
