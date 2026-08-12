(8/11) propLiftEngineAlgorithm:

Lives in: ./propLiftEngine.py

1. We query the top 30 unique played songs from time a to b
2. For each of these top 30 songs, we return a lift_i score for song i
3. Lift_i is defined as [(S_i) / (T_i)] / [(b-a) / N] where S_i is the # of plays in the window, T_i is the # of plays in its lifetime, (b - a) is the length of the window, and N is the full timeline length.
4. We take the top 10 songs with the lift score

Comments: this currently sigificantly penalizes songs that have been played outside, essentially only
rewarding songs that have been played only in this range.
