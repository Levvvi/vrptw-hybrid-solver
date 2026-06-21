# MOSADE-Inspired Adaptive Operator Selection

This project uses Adaptive Large Neighborhood Search (ALNS) for larger VRPTW
instances. The MOSADE-inspired part is the operator selection layer: instead of
claiming a new VRPTW metaheuristic, the implementation transfers the strategy
selection idea from adaptive differential evolution into ALNS destroy-repair
choice.

## Strategy Unit

Classical ALNS often scores destroy operators and repair operators separately.
Here, a strategy is one destroy-repair pair:

```text
strategy = (destroy_operator, repair_operator)
```

This mirrors MOSADE-style strategy adaptation more closely than independent
operator weights, because the useful behavior can come from the interaction
between the removal pattern and the insertion rule.

## Feedback Signal

After each ALNS iteration, the selector receives an `OperatorEvent` with:

- selected destroy and repair names
- whether the candidate was feasible
- whether it was accepted
- whether it produced a new global best
- candidate cost change versus the current solution

The reward combines qualitative search outcomes and a bounded improvement term:

```text
reward =
  5.0 * new_best
  + 3.0 * accepted_improvement
  + 1.0 * accepted
  + 0.2 * feasible
  + diversity_bonus
  + normalized_improvement
```

The constants are intentionally simple. They make new best solutions dominate,
still credit accepted improving moves, and keep feasible exploratory moves from
being treated as pure failures.

## Credit Memory

The selector keeps a sliding memory of recent pair rewards. Pair credit is
updated by exponential smoothing:

```text
credit[pair] = decay * old_credit[pair] + (1 - decay) * recent_mean_reward[pair]
```

This gives the mechanism short-term adaptivity without letting one early lucky
pair dominate the whole run.

## Probability Model

Credits are converted into probabilities with a temperature-scaled softmax and
an exploration floor:

```text
softmax[pair] = exp(credit[pair] / temperature) / sum(exp(...))
prob[pair] = (1 - exploration_floor) * softmax[pair]
             + exploration_floor / number_of_pairs
```

Lower temperature makes the selector exploit high-credit pairs more sharply.
The exploration floor keeps every pair reachable, which matters because VRPTW
neighborhood quality can vary by instance region and search phase.

## Interview Narrative

The interview claim should be precise:

```text
I transferred the adaptive strategy-selection idea from MOSADE into the ALNS
operator-selection layer. In this project, the adaptive unit is a destroy-repair
pair, reward is based on accepted improvement and new-best discovery, and the
selector exposes credit/probability snapshots for convergence analysis.
```

This is not presented as a full MOSADE implementation for VRPTW. It is a
controlled engineering adaptation of one idea: online strategy selection under
feedback.

## Logged Outputs

The selector snapshot includes:

- `pair_credit`: current smoothed credit per destroy-repair pair
- `pair_probabilities`: current sampling probability per pair
- `pair_heatmap`: row-style data suitable for plotting
- `pair_stats`: selected count, accepted count, new-best count, total reward,
  and improvement sum per pair

These fields are stored in ALNS solution metadata and can later feed benchmark
plots or Streamlit/Folium diagnostics.
