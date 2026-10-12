# How dropcurve measures things

Every number in the output comes from one of the definitions below. The
thresholds are defaults, and most can be changed on the command line.

## Events and views

Players send progress pings: user, series, episode, position in seconds, and
a timestamp. Pings for the same (series, user, episode) collapse into one
**view**, which keeps the furthest position reached and the first and last
time seen. Replays and seeks backwards don't count twice.

**Completion** of a view is the furthest position divided by the episode
length, capped at 1. Lengths come from the `duration` column, or from
`--catalog` when the player doesn't send it (the catalog wins). Views of an
episode with no known length are left out of anything that needs completion.

A listener **finished** an episode at 90% or more, so skipping the credits
and the next-episode teaser still counts. A **bounce** is a view that ended
before 30 seconds.

## Inside an episode

The **retention curve** is the share of starters who reached each 1% of the
episode. A **hotspot** is a run of 1% steps where the curve falls more than 3
times faster than its median step. The first 2% and last 10% are skipped,
because people bounce early and skip credits in every episode. A hotspot
must lose at least 1% of starters and at least 10 people, so that a deep
episode with 40 listeners doesn't flag every single person who left.

## Across the season

The **funnel** counts who started each episode, as a share of those who
started episode 1. **Continuation** is, of the people who finished episode
k, the share who started episode k+1 at any point.

An ending's **pull** is narrower: of those who finished episode k, the share
who started k+1 within 24 hours. That is the cliffhanger doing its job.
Each ending is compared with the median pull of the season, using a
one-sample z-test. Endings with |z| of 2.58 or more (about 1 in 100 by
chance) are called weak or strong. Endings with fewer than 30 finishers are
not judged. The median is used rather than the season average so that one
very weak ending can't make every other ending look strong.

**Odd episodes** are found from completion. Each episode's completion is
compared with the average of its two neighbours, and the gap is divided by a
robust spread of all the gaps (1.4826 times the median absolute gap, with a
floor of 1 point). Episodes 3.5 or more of those below their neighbours are
flagged. Episodes with fewer than 50 starters are left out.

## Survival

The funnel undercounts how far people get in a fresh dataset, because people
who arrived last week haven't had time to go far. **Survival** uses
Kaplan-Meier: a listener counts as lost after their deepest episode only if
they haven't been seen for 7 days (`--active-days`) and there were newer
episodes they could have played. Everyone else is censored: counted while
they were listening, not counted as lost. The 95% band uses Greenwood's
formula. The **median depth** is the first episode after which survival is
at or below 50%.

## Sessions and cohorts

A **session** is a run of episode plays with gaps under 30 minutes. A binge
session has 3 or more episodes. **Time to next episode** runs from the last
ping of episode k to the first ping of k+1.

**Cohorts** group listeners by the ISO week of their first ping and show the
share of each cohort who started episodes 2, 3, 5 and 10.

## Paywall tests

Each listener's free episode count comes from the `free_episodes` column (or
`--free` for everyone). Paid unlocks are rows with kind `unlock` and the
coins spent. For each variant:

- **met the wall**: finished the last free episode, or paid for one
- **conversion**: of those who met the wall, the share who paid (with a
  Wilson 95% range)
- **coins per starter**: coins spent by the variant's listeners divided by
  how many started episode 1. This is the number to decide on, because it
  counts the people a wall loses as well as the ones it converts.

The best two variants are compared with a z-test on coins per starter, and
the result is only called when z is 1.96 or more.

`paywall --project` goes further, and says so in its output: it models wall
positions that were not tested, using the reach measured in the most
generous variant, the conversion of the best variant, the observed chance
that a payer unlocks the next episode too, and the average price. It assumes
conversion would not change with the wall position, which real data usually
contradicts (deeper walls convert better, because the people who reach them
are already hooked). Treat it as a way to pick the next variant to test, not
as a result.

## Synthetic data

`dropcurve synth` writes a log with known problems planted in it: an ad
break 41% into episode 6 that loses 12% of listeners, a weak ending on
episode 9, and a slow episode 14. With `--walls` it also assigns paywall
variants, with conversion planted at 6% per free episode. The tests check
that the analysis finds each one. Episode 6 also shows up as an odd episode,
which is right: the people lost at its ad break never finish it.
