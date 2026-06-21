# Statistical Testing Protocol

The experiment statistics module compares solvers over matched runs. A matched
run is identified by the same instance and seed. This supports paired tests,
which are more appropriate than comparing unrelated samples when every solver
is run under the same seed budget.

## What Is Reported

For each solver, the summary table reports:

- total runs, valid runs, failed runs
- feasible rate
- mean, standard deviation, median, and best value for the chosen metric
- mean runtime

For each solver pair, the pairwise table reports:

- number of matched instance/seed pairs
- mean and median metric difference
- Wilcoxon signed-rank p-value
- Holm-adjusted p-value for multiple comparisons
- rank-biserial effect size
- lower-mean solver for the selected metric

By convention, lower cost or distance is better. The reported difference is
`solver_a - solver_b`, so a negative effect favors `solver_a`.

## Interpretation

These tests do not prove that a solver is globally optimal. They estimate
whether observed improvements are stable across the chosen benchmark slice and
random seeds. A small p-value with a meaningful effect size is evidence of a
repeatable gain under this protocol, not a universal claim about all VRPTW
instances.

Failed or infeasible runs are excluded from paired metric tests but remain
visible in the solver summary through failed-run counts and feasible rates.
