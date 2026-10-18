R0 Empty or vague description?
   judge from the TITLE only; no shown shared concern -> 0
R1 Same issue (Resolves #) as query, or one it mentions?
   yes + merged          -> 2  "same issue fixed by earlier PR"
   yes + closed unmerged -> 1  "same issue, closed, reason unknown"
   no                    -> R2
R2 Open PR making the same change?
   yes -> 2  "competing open PR, same change"
   no  -> R3
R3 Same function / same behaviour changed?  (same FILE alone = no)
   must be SHOWN in the candidate's title/description, not imagined
   shared words only (e.g. "alignment", "GIF") = no
   no  -> 0
   yes -> R4
R4 Candidate fixed a bug in that code the query could break again?
   yes (can name it) -> 2  "could reintroduce <bug> fixed earlier"
   no                -> R5
R5 Candidate set the pattern/design the query must follow or changes?
   yes (can name it) -> 2  "<pattern> set earlier, must match"
   no                -> 1  reason = shared area

Overrides (apply after R1-R5):
   closed unmerged, same mechanism, reason unknown -> 1
     ...unless plainly the SAME change as query    -> 2
   relevant part is a side note in a big PR        -> max 1
   trivial change (typo, docs, style) to shared file -> 0

Torn -> LOWER.  Reason > 6 words -> not a 2.
Grade-0 lines: no reason.