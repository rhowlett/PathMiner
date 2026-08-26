# PCB point-to-point resistance report

**Board** `Symbol_Testing.kicad_pcb`  
**Generated** 2026-08-24T21:40:46 by pcb_trace_resistance v0.13

## Assumptions

| Setting | Value |
|---|---|
| Barrel plating | 18 um (0.517 oz-equivalent) |
| Hole value means | bit |
| Barrel length | centre |
| Outer-layer plating adds | True |
| Zone model | ladder |
| Ambient | 25 C |
| Default current | 1 A |
| Default signal voltage | 3.3 V |

DC only. No skin effect, no self-heating, no etch taper. Resistance is reported at 20 C and at ambient. Per-pair voltage or current overrides are marked in the summary.

## Stackup

| Layer | Finished | oz | z centre |
|---|---|---|---|
| F.Cu | 53 um | 1.523 | 0.0085 mm |
| In1.Cu | 70 um | 2.012 | 0.1700 mm |
| In2.Cu | 70 um | 2.012 | 1.4800 mm |
| B.Cu | 53 um | 1.523 | 1.6415 mm |

## Net selection

Reporting on 5 net(s): `Net-(Z1-RX)`, `/SDA`, `Net-(Z1-NRST)`, `/SCL`, `Net-(Z1-TX)`

## Summary

| Net | From | To | Zone | R @20 C | R @ambient | V in | I | Drop | V out | Parallel gain |
|---|---|---|---|---|---|---|---|---|---|---|
| `Net-(Z1-RX)` | Z1.RX | Z2.TX | ladder | 50.69 mohm | 51.69 mohm | 3.3 V | 1 A | 51.691 mV | 3.2483 V | 0.0% |
| `/SDA` | Z3.SDA | Z1.SDA | ladder | 64.16 mohm | 65.42 mohm | 3.3 V | 1 A | 65.419 mV | 3.2346 V | 3.3% |
| `/SDA` | Z3.SDA | Z2.SDA | ladder | 36.58 mohm | 37.3 mohm | 3.3 V | 1 A | 37.303 mV | 3.2627 V | 0.0% |
| `/SDA` | Z1.SDA | Z2.SDA | ladder | 41.13 mohm | 41.94 mohm | 3.3 V | 1 A | 41.938 mV | 3.2581 V | 5.1% |
| `Net-(Z1-NRST)` | Z3.NRST | Z1.NRST | ladder | 66.81 mohm | 68.13 mohm | 3.3 V | 1 A | 68.126 mV | 3.2319 V | 0.0% |
| `Net-(Z1-NRST)` | Z3.NRST | Z2.NRST | ladder | 36.49 mohm | 37.21 mohm | 3.3 V | 1 A | 37.207 mV | 3.2628 V | 0.0% |
| `Net-(Z1-NRST)` | Z1.NRST | Z2.NRST | ladder | 47.08 mohm | 48.01 mohm | 3.3 V | 1 A | 48.006 mV | 3.252 V | 0.0% |
| `/SCL` | Z3.SLC | Z1.SLC | ladder | 64.73 mohm | 66 mohm | 3.3 V | 1 A | 65.997 mV | 3.234 V | 18.9% |
| `/SCL` | Z3.SLC | Z2.SLC | ladder | 20.1 mohm | 20.5 mohm | 3.3 V | 1 A | 20.495 mV | 3.2795 V | 39.8% |
| `/SCL` | Z1.SLC | Z2.SLC | ladder | 56.7 mohm | 57.82 mohm | 3.3 V | 1 A | 57.815 mV | 3.2422 V | 0.1% |
| `Net-(Z1-TX)` | Z1.TX | Z2.RX | ladder | 49.49 mohm | 50.46 mohm | 3.3 V | 1 A | 50.457 mV | 3.2495 V | 0.0% |

Solved in 0.00 s total (scipy backend).

## Detail

### `Net-(Z1-RX)`  (net 1, 2 terminals)


**Z1.RX -> Z2.TX** - 3.3 V in at 1 A gives 3.2483 V out (51.691 mV drop, 51.691 mW). Zone model ladder, 6 nodes, solved in 0 ms. Least-resistance path 50.69 mohm, whole network 50.69 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 16.2% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 3 | trace | 14.0000 mm x 0.1016 mm on In1.Cu | 33.94 mohm | 66.9% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 5 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 16.2% |

### `/SDA`  (net 4, 3 terminals)

- Via array: 6 vias, centroid (163.5, 90.5), extent 5.000 mm
- _via at (173.5, 90.0) lands on 3 layers (F.Cu, In1.Cu, B.Cu) - barrel split into series sub-spans_
- _via array of 6 at centroid (163.5, 90.5) spanning 5.000 mm modelled as a 6-rung ladder over a 1.001 mm wide pour (6.7:1 aspect)_

**Z3.SDA -> Z1.SDA** - 3.3 V in at 1 A gives 3.2346 V out (65.419 mV drop, 65.419 mW). Zone model ladder, 42 nodes, solved in 1 ms. Least-resistance path 66.37 mohm, whole network 64.16 mohm (3.3% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.0625 mm x 0.1016 mm on F.Cu | 6.603 mohm | 9.9% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 3 | trace | 9.5000 mm x 0.1016 mm on In1.Cu | 23.03 mohm | 34.7% |
| 4 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.591 mohm | 2.4% |
| 5 | trace | 6.9571 mm x 0.1016 mm on B.Cu | 22.27 mohm | 33.6% |
| 6 | pour | 0.7500 mm x 1.00058 mm on B.Cu (pour) | 243.8 uohm | 0.4% |
| 7 | via | In2.Cu -> B.Cu, hole 0.3 mm (in pour) | 174.6 uohm | 0.3% |
| 8 | pour | 5.0000 mm x 1.00058 mm on In2.Cu (pour) | 1.231 mohm | 1.9% |
| 9 | via | In1.Cu -> In2.Cu, hole 0.3 mm (in pour) | 1.416 mohm | 2.1% |
| 10 | via | F.Cu -> In1.Cu, hole 0.3 mm (in pour) | 174.6 uohm | 0.3% |
| 11 | pour | 0.2409 mm x 1.00058 mm on F.Cu (pour) | 78.31 uohm | 0.1% |
| 12 | trace | 2.9289 mm x 0.1016 mm on F.Cu | 9.377 mohm | 14.1% |

> branch at pour copper on In2.Cu at +1.279 mm along the pour axis (and 9 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**Z3.SDA -> Z2.SDA** - 3.3 V in at 1 A gives 3.2627 V out (37.303 mV drop, 37.303 mW). Zone model ladder, 42 nodes, solved in 1 ms. Least-resistance path 36.58 mohm, whole network 36.58 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.0625 mm x 0.1016 mm on F.Cu | 6.603 mohm | 18.0% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 3 | trace | 9.5000 mm x 0.1016 mm on In1.Cu | 23.03 mohm | 62.9% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 5 | trace | 2.0625 mm x 0.1016 mm on F.Cu | 6.603 mohm | 18.0% |

> branch at In1.Cu (173.5, 90.0): the other copper is a stub that carries no current between these two pads, so it does not change the result

**Z1.SDA -> Z2.SDA** - 3.3 V in at 1 A gives 3.2581 V out (41.938 mV drop, 41.938 mW). Zone model ladder, 42 nodes, solved in 1 ms. Least-resistance path 43.34 mohm, whole network 41.13 mohm (5.1% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.9289 mm x 0.1016 mm on F.Cu | 9.377 mohm | 21.6% |
| 2 | pour | 0.2409 mm x 1.00058 mm on F.Cu (pour) | 78.31 uohm | 0.2% |
| 3 | via | F.Cu -> In1.Cu, hole 0.3 mm (in pour) | 174.6 uohm | 0.4% |
| 4 | pour | 5.0000 mm x 1.00058 mm on In1.Cu (pour) | 1.231 mohm | 2.8% |
| 5 | via | In1.Cu -> In2.Cu, hole 0.3 mm (in pour) | 1.416 mohm | 3.3% |
| 6 | via | In2.Cu -> B.Cu, hole 0.3 mm (in pour) | 174.6 uohm | 0.4% |
| 7 | pour | 0.7500 mm x 1.00058 mm on B.Cu (pour) | 243.8 uohm | 0.6% |
| 8 | trace | 6.9571 mm x 0.1016 mm on B.Cu | 22.27 mohm | 51.4% |
| 9 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.591 mohm | 3.7% |
| 10 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.4% |
| 11 | trace | 2.0625 mm x 0.1016 mm on F.Cu | 6.603 mohm | 15.2% |

> branch at pour copper on In1.Cu at +2.279 mm along the pour axis (and 9 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

### `Net-(Z1-NRST)`  (net 7, 3 terminals)


**Z3.NRST -> Z1.NRST** - 3.3 V in at 1 A gives 3.2319 V out (68.126 mV drop, 68.126 mW). Zone model ladder, 13 nodes, solved in 0 ms. Least-resistance path 66.81 mohm, whole network 66.81 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.0625 mm x 0.1016 mm on F.Cu | 3.402 mohm | 5.1% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 3 | trace | 16.6213 mm x 0.1016 mm on In1.Cu | 40.29 mohm | 60.3% |
| 4 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.591 mohm | 2.4% |
| 5 | trace | 7.0000 mm x 0.2 mm on B.Cu | 11.38 mohm | 17.0% |
| 6 | via | F.Cu -> B.Cu, hole 0.3 mm | 1.765 mohm | 2.6% |
| 7 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 12.3% |

> branch at In1.Cu (169.5, 86.0): the other copper is a stub that carries no current between these two pads, so it does not change the result

**Z3.NRST -> Z2.NRST** - 3.3 V in at 1 A gives 3.2628 V out (37.207 mV drop, 37.207 mW). Zone model ladder, 13 nodes, solved in 0 ms. Least-resistance path 36.49 mohm, whole network 36.49 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.0625 mm x 0.1016 mm on F.Cu | 3.402 mohm | 9.3% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 3 | trace | 10.1213 mm x 0.1016 mm on In1.Cu | 24.53 mohm | 67.2% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 5 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 22.5% |

> branch at In1.Cu (169.5, 86.0): the other copper is a stub that carries no current between these two pads, so it does not change the result

**Z1.NRST -> Z2.NRST** - 3.3 V in at 1 A gives 3.252 V out (48.006 mV drop, 48.006 mW). Zone model ladder, 13 nodes, solved in 0 ms. Least-resistance path 47.08 mohm, whole network 47.08 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 17.4% |
| 2 | via | F.Cu -> B.Cu, hole 0.3 mm | 1.765 mohm | 3.7% |
| 3 | trace | 7.0000 mm x 0.2 mm on B.Cu | 11.38 mohm | 24.2% |
| 4 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.591 mohm | 3.4% |
| 5 | trace | 6.5000 mm x 0.1016 mm on In1.Cu | 15.76 mohm | 33.5% |
| 6 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.4% |
| 7 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 17.4% |

> branch at In1.Cu (169.5, 86.0): the other copper is a stub that carries no current between these two pads, so it does not change the result

### `/SCL`  (net 8, 3 terminals)

- _via at (173.0, 89.5) lands on 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu) - barrel split into series sub-spans_
- _via at (182.5, 89.5) lands on 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu) - barrel split into series sub-spans_

**Z3.SLC -> Z1.SLC** - 3.3 V in at 1 A gives 3.234 V out (65.997 mV drop, 65.997 mW). Zone model ladder, 17 nodes, solved in 0 ms. Least-resistance path 79.79 mohm, whole network 64.73 mohm (18.9% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.5625 mm x 0.1016 mm on F.Cu | 5.003 mohm | 6.3% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.2% |
| 3 | trace | 9.5000 mm x 0.1016 mm on In1.Cu | 23.03 mohm | 28.9% |
| 4 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.416 mohm | 1.8% |
| 5 | via | In2.Cu -> B.Cu, hole 0.3 mm | 174.6 uohm | 0.2% |
| 6 | trace | 12.5000 mm x 0.1016 mm on B.Cu | 40.02 mohm | 50.2% |
| 7 | via | F.Cu -> B.Cu, hole 0.3 mm | 1.765 mohm | 2.2% |
| 8 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 10.3% |

> branch at In1.Cu (173.0, 89.5) (and 3 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**Z3.SLC -> Z2.SLC** - 3.3 V in at 1 A gives 3.2795 V out (20.495 mV drop, 20.495 mW). Zone model ladder, 17 nodes, solved in 0 ms. Least-resistance path 33.38 mohm, whole network 20.1 mohm (39.8% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.5625 mm x 0.1016 mm on F.Cu | 5.003 mohm | 15.0% |
| 2 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 3 | trace | 9.5000 mm x 0.1016 mm on In1.Cu | 23.03 mohm | 69.0% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.5% |
| 5 | trace | 1.5625 mm x 0.1016 mm on F.Cu | 5.003 mohm | 15.0% |

> branch at In1.Cu (173.0, 89.5) (and 1 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**Z1.SLC -> Z2.SLC** - 3.3 V in at 1 A gives 3.2422 V out (57.815 mV drop, 57.815 mW). Zone model ladder, 17 nodes, solved in 0 ms. Least-resistance path 56.76 mohm, whole network 56.7 mohm (0.1% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.5625 mm x 0.1016 mm on F.Cu | 8.204 mohm | 14.5% |
| 2 | via | F.Cu -> B.Cu, hole 0.3 mm | 1.765 mohm | 3.1% |
| 3 | trace | 12.5000 mm x 0.1016 mm on B.Cu | 40.02 mohm | 70.5% |
| 4 | via | In2.Cu -> B.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 5 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.416 mohm | 2.5% |
| 6 | via | F.Cu -> In1.Cu, hole 0.3 mm | 174.6 uohm | 0.3% |
| 7 | trace | 1.5625 mm x 0.1016 mm on F.Cu | 5.003 mohm | 8.8% |

> branch at In1.Cu (173.0, 89.5) (and 2 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

### `Net-(Z1-TX)`  (net 12, 2 terminals)


**Z1.TX -> Z2.RX** - 3.3 V in at 1 A gives 3.2495 V out (50.457 mV drop, 50.457 mW). Zone model ladder, 9 nodes, solved in 0 ms. Least-resistance path 49.49 mohm, whole network 49.49 mohm (no parallel copper in play)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 2.4767 mm x 0.1016 mm on F.Cu | 7.929 mohm | 16.0% |
| 2 | via | F.Cu -> B.Cu, hole 0.3 mm | 1.765 mohm | 3.6% |
| 3 | trace | 3.0000 mm x 0.1016 mm on B.Cu | 9.605 mohm | 19.4% |
| 4 | via | In2.Cu -> B.Cu, hole 0.3 mm | 174.6 uohm | 0.4% |
| 5 | trace | 9.0000 mm x 0.1016 mm on In2.Cu | 21.82 mohm | 44.1% |
| 6 | via | F.Cu -> In2.Cu, hole 0.3 mm | 1.591 mohm | 3.2% |
| 7 | trace | 2.0625 mm x 0.1016 mm on F.Cu | 6.603 mohm | 13.3% |
