R1 Same issue (Resolves #) as query, or one it mentions?
   yes + merged          -> 2  "same issue fixed by earlier PR"
   yes + closed unmerged -> 1  "same issue, closed, reason unknown"
   no                    -> R2
R2 Open PR making the same change?
   yes -> 2  "competing open PR, same change"
   no  -> R3
R3 Same function / same behaviour changed?  (same FILE alone = no)
   no  -> 0
   yes -> R4
R4 Candidate fixed a bug in that code the query could break again?
   yes (can name it) -> 2  "could reintroduce <bug> fixed earlier"
   no                -> R5
R5 Candidate set the pattern/design the query must follow or changes?
   yes (can name it) -> 2  "<pattern> set earlier, must match"
   no                -> 1  reason = shared area

Torn -> LOWER.  Reason > 6 words -> not a 2.
