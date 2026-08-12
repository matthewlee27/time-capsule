Iteration 1: Setup (8/11): Algorithm to assess steepness/spikes

Setup:
Our data is represented by an array, where {song_id: [(day, count), ...]} allows
us to conduct a binary search for a specified date range a, b and find the number
of plays in that range for a specific song.

Optimization: range-sum cost
Two binary searches locate the boundary indices for a, b, but summing counts
between them is still O(range size) per query. If spike detection ends up
running many overlapping-window queries per song (a sliding window rather
than one-off lookups), keep a prefix-sum array alongside each song's day
array — same shape, prefix[i] = sum of counts[0..i]. A range sum then becomes
prefix[hi] - prefix[lo], O(1) after the two binary searches, at the cost of
one extra array per song.
