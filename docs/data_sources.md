# Data Sources

Date: 2026-06-23

## Benchmark Files

Solomon 100-customer instances:

- Source page: `https://www.sintef.no/projectweb/top/vrptw/100-customers/`
- Download URL: `https://www.sintef.no/globalassets/project/top/vrptw/solomon/solomon-100.zip`
- Local zip: `data/raw/benchmark/solomon-100.zip`
- SHA256: `8A0A72CBE6B7F8F9988ACE4EBDE0378EC34943ACAAAC47F2C408915E41887747`
- Local extracted directory: `data/raw/benchmark/solomon_100/`
- EXP-02 selected instances: `c101`, `r101`, `rc101`

Gehring & Homberger 200-customer extended benchmark instances:

- Source page: `https://www.sintef.no/projectweb/top/vrptw/200-customers/`
- Download URL: `https://www.sintef.no/globalassets/project/top/vrptw/homberger/200/homberger_200_customer_instances.zip`
- Local zip: `data/raw/benchmark/homberger_200_customer_instances.zip`
- SHA256: `79092CC627135F370A6381B0C64AFC8403E4D4FF74AFA8808D28D208AC784571`
- Local extracted directory: `data/raw/benchmark/homberger_200/`
- EXP-02 selected instances: `C1_2_1`, `R1_2_1`, `RC1_2_1`

Earlier small-scale experiments used:

- `tests/fixtures/mini_solomon.txt` as a synthetic mini fixture.
- `data/raw/solomon/C101_25.txt` as a local C101 25-customer slice.
- `data/raw/solomon/C101_100.txt` as the local C101 source for 50-customer slices.

`data/raw/*` is intentionally ignored by git. Reproducible reports should commit
curated CSVs and figures under `reports/`, not raw benchmark archives.

## Objective And Measurement Convention

The SINTEF VRPTW benchmark pages use a hierarchical objective:

1. Minimize the number of vehicles.
2. Minimize total distance.

Distance is Euclidean. Travel time equals distance. Distance and time should be
calculated with double precision, and table distances are rounded to two
decimals.

The project also reports an internal `objective` value with a large vehicle
weight. That value is useful for solver optimization, but it must not be
described as route distance. Reports should show vehicles, distance, runtime,
feasible rate, and objective side by side.

## BKS Scope

The code includes a small verified BKS table for Solomon 100-customer `C101`,
`R101`, and `RC101` only. Missing BKS fields must remain blank. Do not invent
Gehring & Homberger 200-customer BKS entries unless they are explicitly added
from a verified source.

Solomon 25/50-customer slices and C101-derived truncated instances are useful
for smoke tests and small validation, but their distances should not be mixed
directly with full 100-customer BKS values.
