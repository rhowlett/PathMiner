# PCB point-to-point resistance report

**Board** `Ref_PowerBank_injoinic_IP5385_v0_8.kicad_pcb`  
**Generated** 2026-08-24T21:40:45 by pcb_trace_resistance v0.13

## Assumptions

| Setting | Value |
|---|---|
| Barrel plating | 18 um (0.517 oz-equivalent) |
| Hole value means | bit |
| Barrel length | centre |
| Outer-layer plating adds | True |
| Zone model | ladder |
| Ambient | 25 C |
| Default current | 8 A |
| Default signal voltage | 8.4 V |

DC only. No skin effect, no self-heating, no etch taper. Resistance is reported at 20 C and at ambient. Per-pair voltage or current overrides are marked in the summary.

## Stackup

| Layer | Finished | oz | z centre |
|---|---|---|---|
| F.Cu | 53 um | 1.523 | 0.0085 mm |
| In1.Cu | 35 um | 1.006 | 0.1525 mm |
| In2.Cu | 35 um | 1.006 | 1.4275 mm |
| B.Cu | 53 um | 1.523 | 1.5715 mm |

## Net selection

Reporting on 1 net(s): `/Reference Design/PACK_P`

## Summary

| Net | From | To | Zone | R @20 C | R @ambient | V in | I | Drop | V out | Parallel gain |
|---|---|---|---|---|---|---|---|---|---|---|
| `/Reference Design/PACK_P` | JP1.B | U9.D | ladder | 5.287 mohm | 5.391 mohm | 8.4 V | 8 A | 43.126 mV | 8.3569 V | 23.3% |
| `/Reference Design/PACK_P` | JP1.B | C17.1 | ladder | 5.285 mohm | 5.389 mohm | 8.4 V | 8 A | 43.114 mV | 8.3569 V | 23.3% |
| `/Reference Design/PACK_P` | JP1.B | C16.1 | ladder | 5.255 mohm | 5.359 mohm | 8.4 V | 8 A | 42.868 mV | 8.3571 V | 23.2% |
| `/Reference Design/PACK_P` | JP1.B | R8.1 | ladder | 6.391 mohm | 6.516 mohm | 8.4 V | 8 A | 52.131 mV | 8.3479 V | 20.3% |
| `/Reference Design/PACK_P` | JP1.B | C44.1 | ladder | 5.129 mohm | 5.23 mohm | 8.4 V | 8 A | 41.839 mV | 8.3582 V | 23.6% |
| `/Reference Design/PACK_P` | JP1.B | CP2.1 | ladder | 5.184 mohm | 5.286 mohm | 8.4 V | 8 A | 42.289 mV | 8.3577 V | 23.4% |
| `/Reference Design/PACK_P` | JP1.B | U2.CSP2 | mesh 0.25mm | 195.5 mohm | 199.4 mohm | 8.4 V* | 0.001 A* | 0.199 mV | 8.3998 V | 14.9% |
| `/Reference Design/PACK_P` | JP1.B | U2.BAT | mesh 0.25mm | 96.9 mohm | 98.8 mohm | 8.4 V* | 0.001 A* | 0.099 mV | 8.3999 V | 25.5% |
| `/Reference Design/PACK_P` | JP1.B | U11.D | ladder | 5.36 mohm | 5.465 mohm | 8.4 V | 8 A | 43.720 mV | 8.3563 V | 37.5% |
| `/Reference Design/PACK_P` | JP1.B | C15.1 | ladder | 189.5 mohm | 193.2 mohm | 8.4 V* | 0.05 A* | 9.661 mV | 8.3903 V | 0.9% |
| `/Reference Design/PACK_P` | JP1.B | C39.2 | ladder | 90.57 mohm | 92.35 mohm | 8.4 V* | 0.05 A* | 4.618 mV | 8.3954 V | 1.8% |

`*` marks a value overridden for that pair rather than taken from the operating-condition defaults.

Solved in 0.44 s total (scipy backend).

## Detail

### `/Reference Design/PACK_P`  (net 10, 12 terminals)

- Via array: 13 vias, centroid (117.3462, 94.8077), extent 5.630 mm
- Via array: 7 vias, centroid (117.3, 99.1), extent 4.200 mm
- _pour aspect ratio is only 1.9:1 - a 1-D strip model is questionable on copper this square; consider the mesh model_
- _pad C17.1 on F.Cu has no track and sits 0.150 mm outside the filled copper (zone clearance / thermal relief); connected to the pour. The relief spokes themselves are not modelled, so this pad reads slightly optimistic_
- _pad C16.1 on F.Cu has no track and sits 0.150 mm outside the filled copper (zone clearance / thermal relief); connected to the pour. The relief spokes themselves are not modelled, so this pad reads slightly optimistic_
- _pad C44.1 on F.Cu has no track and sits 0.120 mm outside the filled copper (zone clearance / thermal relief); connected to the pour. The relief spokes themselves are not modelled, so this pad reads slightly optimistic_
- _via at (102.8, 98.1) lands on 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu) - barrel split into series sub-spans_
- _via at (103.5, 98.1) lands on 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu) - barrel split into series sub-spans_
- _via at (102.1, 98.1) lands on 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu) - barrel split into series sub-spans_
- _via array of 13 at centroid (117.3462, 94.8077) spanning 5.630 mm modelled as a 20-rung ladder over a 13.652 mm wide pour (1.9:1 aspect)_
- _via array of 7 at centroid (117.3, 99.1) spanning 4.200 mm modelled as a 20-rung ladder over a 13.652 mm wide pour (1.9:1 aspect)_
- _U9.D appears on 3 pads (also 5, 5); treated as one terminal, computed once_
- _U11.D appears on 3 pads (also 5, 5); treated as one terminal, computed once_

**JP1.B -> U9.D** - 8.4 V in at 8 A gives 8.3569 V out (43.126 mV drop, 345.011 mW). Zone model ladder, 200 nodes, solved in 31 ms. Least-resistance path 6.891 mohm, whole network 5.287 mohm (23.3% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 11.2% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 20.0% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 61.6% |
| 6 | pour | 7.5397 mm x 13.652 mm on F.Cu (pour) | 179.6 uohm | 2.6% |

> branch at pour copper on F.Cu at -9.357 mm along the pour axis (and 16 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> C17.1** - 8.4 V in at 8 A gives 8.3569 V out (43.114 mV drop, 344.912 mW). Zone model ladder, 200 nodes, solved in 33 ms. Least-resistance path 6.888 mohm, whole network 5.285 mohm (23.3% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 11.2% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 20.0% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 61.7% |
| 6 | pour | 7.4350 mm x 13.652 mm on F.Cu (pour) | 177.2 uohm | 2.6% |

> branch at pour copper on F.Cu at -9.357 mm along the pour axis (and 15 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> C16.1** - 8.4 V in at 8 A gives 8.3571 V out (42.868 mV drop, 342.945 mW). Zone model ladder, 200 nodes, solved in 32 ms. Least-resistance path 6.841 mohm, whole network 5.255 mohm (23.2% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 11.3% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 20.1% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 62.1% |
| 6 | pour | 5.4708 mm x 13.652 mm on F.Cu (pour) | 130.4 uohm | 1.9% |

> branch at F.Cu (103.5, 98.1) (and 10 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> R8.1** - 8.4 V in at 8 A gives 8.3479 V out (52.131 mV drop, 417.050 mW). Zone model ladder, 200 nodes, solved in 31 ms. Least-resistance path 8.019 mohm, whole network 6.391 mohm (20.3% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 9.7% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 1.9% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 17.2% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 1.9% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 53.0% |
| 6 | pour | 25.4531 mm x 13.652 mm on F.Cu (pour) | 606.5 uohm | 7.6% |
| 7 | trace | 0.5480 mm x 0.254 mm on F.Cu | 701.8 uohm | 8.8% |

> branch at pour copper on F.Cu at -6.607 mm along the pour axis (and 26 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> C44.1** - 8.4 V in at 8 A gives 8.3582 V out (41.839 mV drop, 334.714 mW). Zone model ladder, 200 nodes, solved in 33 ms. Least-resistance path 6.713 mohm, whole network 5.129 mohm (23.6% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 11.5% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 20.5% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 63.3% |
| 6 | pour | 0.0853 mm x 13.652 mm on F.Cu (pour) | 2.032 uohm | 0.0% |

> branch at F.Cu (103.5, 98.1) (and 5 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> CP2.1** - 8.4 V in at 8 A gives 8.3577 V out (42.289 mV drop, 338.313 mW). Zone model ladder, 200 nodes, solved in 31 ms. Least-resistance path 6.768 mohm, whole network 5.184 mohm (23.4% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 11.4% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 20.4% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 2.3% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 62.8% |
| 6 | pour | 2.3996 mm x 13.652 mm on F.Cu (pour) | 57.17 uohm | 0.8% |

> branch at F.Cu (103.5, 98.1) (and 5 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> U2.CSP2** - 8.4 V in at 0.001 A gives 8.3998 V out (0.199 mV drop, 0.000 mW). Zone model mesh, 4193 nodes, solved in 103 ms. Least-resistance path 229.7 mohm, whole network 195.5 mohm (14.9% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 0.3% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 0.6% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 1.8% |
| 6 | mesh | meshed pour, 108 cells | 34.88 mohm | 15.2% |
| 7 | trace | 0.5480 mm x 0.254 mm on F.Cu | 701.8 uohm | 0.3% |
| 8 | trace | 5.0870 mm x 0.1524 mm on F.Cu | 10.86 mohm | 4.7% |
| 9 | via | F.Cu -> In2.Cu, hole 0.3 mm | 1.534 mohm | 0.7% |
| 10 | trace | 6.7153 mm x 0.1524 mm on In2.Cu | 21.7 mohm | 9.5% |
| 11 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 0.6% |
| 12 | trace | 43.7937 mm x 0.1524 mm on In1.Cu | 141.5 mohm | 61.6% |
| 13 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.534 mohm | 0.7% |
| 14 | trace | 5.5081 mm x 0.2032 mm on B.Cu | 8.817 mohm | 3.8% |

> branch at ('F.Cu', 68, 24) (and 113 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> U2.BAT** - 8.4 V in at 0.001 A gives 8.3999 V out (0.099 mV drop, 0.000 mW). Zone model mesh, 4193 nodes, solved in 55 ms. Least-resistance path 130 mohm, whole network 96.9 mohm (25.5% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 0.6% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 1.1% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 3.3% |
| 6 | mesh | meshed pour, 105 cells | 33.9 mohm | 26.1% |
| 7 | trace | 5.2213 mm x 0.254 mm on F.Cu | 6.687 mohm | 5.1% |
| 8 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 9 | trace | 38.9583 mm x 0.254 mm on In1.Cu | 75.55 mohm | 58.1% |
| 10 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.534 mohm | 1.2% |
| 11 | trace | 3.4278 mm x 0.2032 mm on B.Cu | 5.487 mohm | 4.2% |

> branch at ('F.Cu', 49, 29) (and 110 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> U11.D** - 8.4 V in at 8 A gives 8.3563 V out (43.720 mV drop, 349.763 mW). Zone model ladder, 200 nodes, solved in 32 ms. Least-resistance path 8.581 mohm, whole network 5.36 mohm (37.5% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 9.0% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 1.8% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 16.1% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 1.8% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 49.5% |
| 6 | pour | 6.7490 mm x 13.652 mm on F.Cu (pour) | 160.8 uohm | 1.9% |
| 7 | via | F.Cu -> In1.Cu, hole 0.3 mm (in pour) | 155.7 uohm | 1.8% |
| 8 | via | In1.Cu -> In2.Cu, hole 0.3 mm (in pour) | 1.378 mohm | 16.1% |
| 9 | via | In2.Cu -> B.Cu, hole 0.3 mm (in pour) | 155.7 uohm | 1.8% |
| 10 | pour | 0.8142 mm x 13.652 mm on B.Cu (pour) | 19.4 uohm | 0.2% |

> branch at pour copper on F.Cu at -9.357 mm along the pour axis (and 19 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> C15.1** - 8.4 V in at 0.05 A gives 8.3903 V out (9.661 mV drop, 0.483 mW). Zone model ladder, 200 nodes, solved in 31 ms. Least-resistance path 191.1 mohm, whole network 189.5 mohm (0.9% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 0.4% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 0.7% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.1% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 2.2% |
| 6 | pour | 25.4531 mm x 13.652 mm on F.Cu (pour) | 606.5 uohm | 0.3% |
| 7 | trace | 0.5480 mm x 0.254 mm on F.Cu | 701.8 uohm | 0.4% |
| 8 | trace | 5.0870 mm x 0.1524 mm on F.Cu | 10.86 mohm | 5.7% |
| 9 | via | F.Cu -> In2.Cu, hole 0.3 mm | 1.534 mohm | 0.8% |
| 10 | trace | 6.7153 mm x 0.1524 mm on In2.Cu | 21.7 mohm | 11.4% |
| 11 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 0.7% |
| 12 | trace | 43.7937 mm x 0.1524 mm on In1.Cu | 141.5 mohm | 74.1% |
| 13 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.534 mohm | 0.8% |
| 14 | trace | 2.8427 mm x 0.2032 mm on B.Cu | 4.551 mohm | 2.4% |

> branch at pour copper on F.Cu at -6.607 mm along the pour axis (and 26 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper

**JP1.B -> C39.2** - 8.4 V in at 0.05 A gives 8.3954 V out (4.618 mV drop, 0.231 mW). Zone model ladder, 200 nodes, solved in 31 ms. Least-resistance path 92.2 mohm, whole network 90.57 mohm (1.8% lower - parallel copper carries current)

| # | Element | Detail | R @20 C | % of path |
|---|---|---|---|---|
| 1 | trace | 1.1899 mm x 0.5 mm on B.Cu | 774.1 uohm | 0.8% |
| 2 | via | In2.Cu -> B.Cu, hole 0.3 mm | 155.7 uohm | 0.2% |
| 3 | via | In1.Cu -> In2.Cu, hole 0.3 mm | 1.378 mohm | 1.5% |
| 4 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.2% |
| 5 | trace | 6.5284 mm x 0.5 mm on F.Cu | 4.247 mohm | 4.6% |
| 6 | pour | 25.6627 mm x 13.652 mm on F.Cu (pour) | 611.5 uohm | 0.7% |
| 7 | trace | 5.2213 mm x 0.254 mm on F.Cu | 6.687 mohm | 7.3% |
| 8 | via | F.Cu -> In1.Cu, hole 0.3 mm | 155.7 uohm | 0.2% |
| 9 | trace | 38.9583 mm x 0.254 mm on In1.Cu | 75.55 mohm | 81.9% |
| 10 | via | In1.Cu -> B.Cu, hole 0.3 mm | 1.534 mohm | 1.7% |
| 11 | trace | 0.7325 mm x 0.25 mm on B.Cu | 953.1 uohm | 1.0% |

> branch at pour copper on F.Cu at -6.607 mm along the pour axis (and 27 more): the net is not a simple series chain - see the network figure for the effect of the parallel copper
