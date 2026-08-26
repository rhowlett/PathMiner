<!-- v0.6 -->
# PathMiner — path capture: KiCad plugin → JSON → analysis

Answering: is the proposed plugin/file/app split possible?
Short answer: **yes, and it is the right division.** The plugin does selection, where KiCad
has the live board and the UI. The app does analysis. The JSON is the contract between them,
and — importantly — the app never needs the plugin, because the file can equally be
hand-written, generated, or edited in the app.

This document proposes the schema and flags the four places where the obvious design breaks.

---

## 1. The one decision that makes or breaks re-runnability

You want to update the PCB and re-run the same paths from CLI or GUI. That requires the file
to be **re-resolvable against a board it was not captured on**. Which means it must contain
only identifiers that survive a re-route.

| Do **not** store | Why |
|---|---|
| Net numbers (`net 10`) | KiCad reassigns net codes on recompute. `PACK_P` was net 10 today and need not be tomorrow |
| Coordinates | Every re-route invalidates them; this is the whole point of re-running |
| Layer of a pad | May legitimately change |
| Track/via UUIDs | Deleted and recreated by routing |

| Store instead | Stability |
|---|---|
| `REF.PAD` (`U9.5`, `Q3.S`) | Stable unless the schematic is re-annotated |
| Net **name** (`/Reference Design/PACK_P`) | Derived from the schematic; stable |
| Pin function (`SDA`) | Stable, and human-checkable |

**Net names are recorded for validation only, never for lookup.** On re-run, the app asks the
board what net `U9.5` is on now. If that differs from the recorded name, it warns — the path
still resolves, but something moved and you should know.

## 2. The path is an alternating chain, and that makes it self-validating

A path is just an ordered list of `REF.PAD` nodes. Every consecutive pair is one of two
things, and the app can tell which without being told:

- **Same refdes** → a *bridge* through the component. Needs an R value.
- **Same net** → *copper*. Compute it with the existing p2p/ladder/mesh machinery.
- **Neither** → the path is broken. Name the break and stop.

So `JP1.3 → U9.5` is copper, `U9.5 → U9.1` is a bridge, `U9.1 → C44.1` is copper again. The
nets between hops are derived, never stored, which is exactly what makes the file survive a
re-route. It also means a stale path fails loudly at a named hop rather than producing a
plausible wrong number.

```jsonc
{
  "_meta": { "version": "0.1", "board": "Ref_PowerBank.kicad_pcb",
             "captured": "2026-08-24T21:00:00", "captured_by": "kicad-plugin v0.1" },

  "defaults": { "plating_um": 18.0, "zone_model": "ladder", "ambient_c": 25.0 },

  "paths": [
    {
      "id": "pack_to_usbc",
      "title": "Battery pack to USB-C VBUS",
      "source": { "at": "JP1.3", "voltage_v": 8.4 },
      "sink":   { "at": "J2.A4", "min_voltage_v": 4.75, "load": { "power_w": 27.0 } },
      "hops": [
        { "at": "JP1.3" },
        { "at": "U9.5" },
        { "at": "U9.1", "bridge": { "ohms": 0.0021, "source": "Rds_on @4.5V, datasheet" } },
        { "at": "R20.1" },
        { "at": "R20.2", "bridge": { "ohms": 0.001, "source": "shunt, Value field" } },
        { "at": "J2.A4" }
      ]
    }
  ]
}
```

`bridge` sits on the *arriving* node, so a hop reads "get to this pad, having crossed the
component from the previous one". Copper hops carry no bridge key at all.

## 3. Sinks: three ways to say "load", and they are not equivalent

You listed power, current, or resistance. Each needs different maths, and one of them has a
failure mode worth surfacing.

**Constant current** — one pass. `V_load = V_src − I·R`.

**Constant resistance** — closed form. `I = V_src / (R_path + R_load)`.

**Constant power** — the interesting one. `I = P / V_load` and `V_load = V_src − I·R`
substitute into a quadratic:

```
V_load² − V_src·V_load + P·R = 0
V_load = ( V_src + √(V_src² − 4·P·R) ) / 2        (take the upper root)
```

Closed form, no iteration needed — I checked it against a 60-step fixed-point solve and they
agree to nine decimals. Two consequences worth putting in the report:

- **A constant-power load makes drop worse than a constant-current one.** As voltage sags the
  sink draws more. On the real `JP1.B → U9.D` path (5.287 mΩ, 8.4 V): 8 A constant current
  gives 42.30 mV of drop; 67.2 W constant power gives 42.51 mV and 8.041 A. Small here, but it
  grows with R and it is always in the unhelpful direction.
- **There is a maximum deliverable power**: `P_max = V_src² / (4·R)`, occurring at
  `V_load = V_src/2`. Above it the discriminant goes negative and there is no steady state.
  On that path `P_max` is 3336 W, so it is irrelevant; on a 0.9 Ω path from 8.4 V it is
  19.6 W, and asking for 30 W has *no solution*. That must be reported as "this path cannot
  deliver the requested power", not as a NaN or a silently clamped number.

The `min_voltage_v` on the sink then gives the report a pass/fail per path — which is really
what you are asking the tool, and it is a much better headline than a resistance.

### 3.1 Operating point vs budget — two different questions

Your 64 W / 50 W example is arithmetically exact: at 8 A a 50 W sink sits at 6.25 V with a
0.78125 Ω load. But note what it *implies*: 14 W lost in the interconnect, which is a
**218.75 mΩ path** — 41x the 5.287 mΩ actually measured on `JP1.B → U9.D`. The numbers are
self-consistent; they just describe a board nobody would ship.

That matters because it exposes an over-determination. You cannot state `V_src`, `P_src`,
`P_sink` **and** compute `R_path` from copper — the fourth value is fixed by the other three.
So the tool needs two distinct modes:

**Mode A — operating point (design verification).** Inputs: source voltage, one load spec
(I, P, or R_load), and `R_path` computed from the copper. Everything else is derived. Same
8 V / 8 A load:

| Computed `R_path` | `V_sink` | `P_sink` | `P_loss` |
|---|---|---|---|
| 5.287 mΩ (measured) | 7.9577 V | 63.66 W | 0.34 W |
| 50 mΩ | 7.6000 V | 60.80 W | 3.20 W |
| 218.75 mΩ | 6.2500 V | 50.00 W | 14.00 W |

**Mode B — budget (requirements check).** "Source 64 W, sink 50 W" is not an operating point,
it is an allowance. It inverts to a maximum tolerable path resistance, which the computed
value is then checked against:

```
R_allowed = (V_src − V_min) / I
```

At 8 A: `V_min` 7.90 V → 12.50 mΩ allowed; 7.50 V → 62.50 mΩ; 6.25 V → 218.75 mΩ. The measured
5.287 mΩ passes all three, with margin the report should state rather than a bare PASS.

`min_voltage_v` already expresses Mode B, so the schema needs no new field — but the report
should present both: the operating point *and* the margin against budget.

### 3.2 Flags

- **`P_sink ≥ P_src` → impossible.** Zero or negative loss. Your instinct is right: automatic
  flag, no calculation attempted.
- **Implied `R_path` below anything physical.** 63.99 W out of 64 W implies 0.156 mΩ; not
  impossible, but if it is far below the computed value the budget is meaningless and should
  say so.
- **Computed `R_path` > `R_allowed`** → FAIL, with the shortfall in mΩ and mV.
- **Constant-power sink above `V_src²/(4R)`** → no steady state (§3).

One framing point for the report's wording: a source is a *voltage*; "64 W" is a consequence of
the load drawing 8 A, not a property of the supply. KCL makes the current the same in every
series element, but it does not fix its value — the load spec and the path do.

## 3.2b A real source (OCV + internal resistance + current limit) — this SIMPLIFIES it

Modelling the source as OCV, `r_internal_ohms` and `max_current_a` is strictly better than a
stiff voltage, for four reasons.

**1. Internal resistance is just another series element.** `R_total = R_source + R_path`. No
solver change, no new maths — one more edge on the front of the chain. The 0.05 Ω source and
0.025 Ω of copper simply sum to 0.075 Ω.

**2. It removes the over-determination from §3.1.** Source power stops being an input and
becomes derived. The inputs become entirely physical — OCV, `Rs`, `Imax`, and one load spec —
and everything else falls out. The "you can't state all four" problem disappears because you
no longer *want* to state source power.

**3. `Imax` is a clamp, not a solve.** One comparison and a branch, not another equation.

**4. The root ambiguity resolves consistently.** For a 50 W sink the quadratic gives
I = 100 A (V = 0.5 V) and I = 6.6667 A (V = 7.5 V). The physical root is 6.6667 A at 7.5 V.
This is the same rule as §3 — **the high-voltage root is the low-current root** — so the two
statements agree rather than conflict.

**Two ceilings now exist, and the report should name whichever binds first:**

| Ceiling | Value in this example |
|---|---|
| Source current limit: `(OCV − Imax·R_total)·Imax` | **59.20 W** at 8 A, 7.4 V |
| Quadratic discriminant: `OCV²/(4·R_total)` | 213.3 W at 53.3 A |

Here `Imax` binds 3.6x earlier, so it is the one that matters. Above it the source
current-limits and the sink is under-served — a distinct, reportable regime:

| Sink spec | I | V_sink | P delivered | Regime |
|---|---|---|---|---|
| P = 20 W | 2.5615 A | 7.8079 V | 20.00 W | ok |
| P = 50 W | 6.6667 A | 7.5000 V | 50.00 W | ok |
| P = 59.2 W | 8.0000 A | 7.4000 V | 59.20 W | ok, exactly at the limit |
| P = 70 W | 8.0000 A | 7.4000 V | **59.20 W** | source current-limited, load wants 70 W |
| I = 12 A | 8.0000 A | 7.4000 V | 59.20 W | clamped from 12 A |

**Implementation trap:** the `Imax` clamp must apply to *all three* sink specs, not just the
current one. A 0.5 Ω resistive load on this source draws 13.9 A unclamped — the clamp belongs
after the operating point is solved, whichever way it was specified, not inside the
constant-current branch.

Schema addition is small; `voltage_v` stays valid as shorthand for OCV with `Rs = 0`:

```jsonc
"source": { "at": "JP1.3", "ocv_v": 8.0, "r_internal_ohms": 0.05, "max_current_a": 8.0,
            "source_note": "2S pack, DCIR at 50% SoC, 25 C" }
```

Worth recording where `r_internal_ohms` came from — a cell's DCIR moves with state of charge,
temperature and age, and a stale 0.05 Ω is the same class of silent assumption as a guessed
`Rds_on`.

## 3.3 Component values: parse, show, allow override

Yes — and the parsing is the awkward part, so it should be explicit rather than clever.

A resistor's value lives in the footprint's `Value` field, but as free text with no single
convention: `0.005`, `5m`, `R005`, `0R005`, `5 mR`, `0.005 1%`. A shunt is exactly where this
matters and exactly where the notations proliferate. Worse, for a FET the `Value` field holds
the *part number*, which tells you nothing about `Rds_on`.

Proposed order of precedence, highest first:

1. **Override in the app or plugin** — always wins, recorded as `"source": "overridden"`.
2. **A dedicated footprint field** — `R_bridge`, or `Rds_on` for actives. Explicit and stable.
3. **Parsed `Value`**, only for parts whose value *is* a resistance (a resistor footprint or a
   `R*` refdes), using a documented grammar: optional `R`/`k`/`M` as decimal point, optional
   SI suffix, tolerance and rating stripped. Record the parsed result *and the source string*
   so the report shows `0.005 Ω (from Value "R005")`.
4. **Nothing** — then it is a missing value, handled per Q2.

The grammar should be small, documented, and testable, and anything it cannot parse
unambiguously should fail to the override rather than guess. A shunt misread by 1000x is not a
subtle error, but it is a silent one.

## 4. Plugin flow, with the one UI trap called out

Your sequence works. One practical problem: **KiCad's selection has no order.** Multi-selecting
five footprints gives you a set, not a sequence, so "pick the footprints in order" cannot be
read from selection state.

The fix is a modeless wx dialog that builds the list explicitly:

1. **Source** — user selects a footprint in KiCad, clicks *Set source*, picks the pad from a
   list showing each pad's net name. Enter source voltage.
2. **Add hop** — select the next footprint in KiCad, click *Add*. The dialog appends it in
   click order, which is the ordering you need.
3. **Fanout** — if the footprint has more than one pad on the relevant nets, the dialog asks
   for **in** and **out** pads. For a FET the user picks Drain in, Source out; the dialog then
   asks for the bridge resistance and prefills from a footprint field if one exists
   (`Rds_on`, or `Value` for a shunt), recording where the number came from.
4. **Validate as you go** — after each hop, check that the previous out-pad and this in-pad
   share a net. If not, say so immediately. Catching it at capture time is far better than at
   analysis time.
5. **Sink** — last component, its in-pad, plus min voltage and the load spec.
6. **Save / append** — write a new path into the file, or add to the existing `paths` array.

Multiple paths per file falls out naturally, and is what makes the CLI regression you want
possible: one file, N paths, run it against every board revision.

## 5. Overrides in the main app

The file is the captured intent; the app may override. Keep both, and keep provenance:

- Bridge R values become editable in the app (a table much like the per-pair overrides).
- An overridden value records `"source": "overridden in app"` and the report marks it, exactly
  as `*` already marks per-pair voltage and current.
- Analysis settings (`plating_um`, `zone_model`, per-pair models) live in the *existing*
  net-selection file, not here. This file holds **topology and component values only** — the
  `defaults` block is a hint the app may adopt, not an instruction.

Two files, two lifecycles: paths change when the design changes; analysis settings change when
you change your mind about modelling. Conflating them would mean re-capturing paths to change
a plating assumption.

## 6. What this needs from the refactor

This is the concrete case for the `BoardSource` protocol (R4 in the architecture review). The
plugin resolves `REF.PAD` against a **live** `pcbnew` board; the app resolves the same string
against a **parsed file**. Same code above that line. Without the protocol, the resolver gets
written twice and drifts.

It also needs `REF.PAD` resolution to be a first-class function — `board.pad("U9.5") → Pad` —
which does not exist yet. Terminals are currently discovered per-net, not looked up by name.
That is a small addition to `kicad/board.py`, and both consumers need it.

## 7. Decisions (closed)

| ID | Decision | Consequence |
|---|---|---|
| **D1** | Same pad in and out = a zero-ohm bridge | Legal hop, contributes 0 Ω. No special case; the hop list stays uniform |
| **D2** | A missing bridge value is an **error**, not a warning | Analysis refuses to run. See §7.1 for what the message must contain |
| **D3** | Parallel branches supported, and **labelled parallel vs series** | The hop list becomes a shallow graph. See §7.2 |
| **D4** | Sink reports a **% pass**, not a bare PASS/FAIL | See §7.3 for the definition |
| **D5** | Files live in `<project>/.pathminer/` | Beside the design, version-controlled, auto-discoverable. `_meta.board` becomes project-relative, closing the old Q5 |
| **D6** | A changed net on re-run **warns and asks** fix-or-continue | GUI prompts; CLI cannot ask, so see §7.4 |
| **D7** | Source current limit binding is a **reportable fail** | Fails, but as a distinct reason from a voltage fail. See §7.5 |
| **D8** | Parallel imbalance is always reported as a %; warn at 10%, flag at 20%, both overridable | See §7.6 for the definition |
| **D9** | Project renamed **PathMiner**; files live in `<project>/.pathminer/` | Package `pathminer`, directory `.pathminer`. Supersedes the working name in the architecture review |
| **D10** | Failures are **reported together**, not short-circuited | A source limit and the under-voltage it causes both appear. See §7.5 |

### 7.1 What a missing-value error must say (D2)

"Cannot run" is only useful if the user can act on it immediately. The message needs five
things, and it must list **every** missing value at once, not fail on the first one — otherwise
fixing five bridges means five run-fix cycles.

```
Path "pack_to_usbc" cannot run: 2 bridge resistances are missing.

  hop 3   Q3  D -> S    no value
          tried: override (none), footprint field Rds_on (absent),
                 Value "CSD18540Q5B" (not a resistance)
          fix:   set Rds_on on the footprint, or enter a value in the
                 Bridges table, or add "ohms" to hop 3 in pack_paths.json

  hop 7   F1  1 -> 2    no value
          tried: override (none), footprint field R_bridge (absent),
                 Value "5A" (not a resistance)
          fix:   as above
```

Naming what was *tried* is what makes it fixable — otherwise the user does not know which of
the three sources to populate.

### 7.2 Parallel branches (D3)

A branch group splits at the preceding node and rejoins at the following one. Each branch is
itself a hop list, so the structure nests without new concepts:

```jsonc
{ "parallel": [
    { "id": "Q1", "hops": [ {"at": "Q1.D"}, {"at": "Q1.S", "bridge": {"ohms": 0.0021}} ] },
    { "id": "Q2", "hops": [ {"at": "Q2.D"}, {"at": "Q2.S", "bridge": {"ohms": 0.0030}} ] }
] }
```

Validation: every branch must begin on the same net as the preceding hop and end on the same
net as the following one. That is checkable at capture time and at run time.

**Solve it through the existing nodal solver, not by a parallel formula.** The solver already
handles arbitrary topology, so a group that is not strictly series-parallel still works. The
`parallel` key is for readability and reporting, not for the maths.

**Report the current division — this is the point of supporting it.** Two nominally identical
FETs rarely share evenly:

| Branch | R | Current at 6.6667 A | Share | Dissipation |
|---|---|---|---|---|
| Q1 | 2.10 mΩ | 3.9216 A | 58.8% | 32.3 mW |
| Q2 | 3.00 mΩ | 2.7451 A | 41.2% | 22.6 mW |
| **combined** | **1.2353 mΩ** | 6.6667 A | | |

Q1 carries **1.43x** Q2 and runs 43% hotter, from a 0.9 mΩ difference. That is a derating and
thermal finding a combined resistance alone would hide, so the report should flag imbalance
past a threshold. (Equal resistances split exactly evenly — worth an assertion.)

### 7.3 Percentage pass (D4)

```
budget = V_source_ocv − V_sink_min
used   = V_source_ocv − V_sink_actual
margin% = (budget − used) / budget × 100
```

100% means no drop at all, 0% means exactly at the limit, negative means FAIL by that
proportion. For the running example — OCV 8 V, `V_min` 4.75 V, 50 W sink — budget is 3.250 V,
used is 0.500 V, **margin 84.6%**. Raise `V_min` to 7.6 V and the same path reads **−25.0%**,
which states how badly it fails rather than just that it did.

**Break down where the budget went.** This is more actionable than the headline:

| | Drop | % of budget |
|---|---|---|
| Source internal resistance | 333.3 mV | 10.3% |
| Copper + bridges | 166.7 mV | 5.1% |
| Margin remaining | 2750.0 mV | 84.6% |

Here the cell eats twice what the copper does — so widening traces is the wrong place to spend
effort, and the report says so without the user having to work it out.

### 7.4 Net drift on re-run (D6)

GUI: list every hop whose net name changed, with old and new, and offer Continue / Abort /
Update file.

CLI cannot ask, so it must **fail by default** — a regression tool that silently accepts drift
is not doing its job — with `--accept-net-changes` to proceed and `--update-paths` to rewrite
the recorded names. The failure lists the same detail the GUI dialog would show.

### 7.5 Failure is not one thing (D7)

A single PASS/FAIL flag would hide the most useful part of the answer. There are now five
distinct outcomes, and they send you to different parts of the design:

| Reason | Meaning | Where to fix it |
|---|---|---|
| `PASS` | Delivers the demand above `V_min` | — |
| `FAIL_VOLTAGE` | `V_sink` below `V_min` | Copper, vias, bridge components |
| `FAIL_SOURCE_LIMIT` | Source cannot supply the demanded current | The source. The path may be perfect |
| `FAIL_NO_STEADY_STATE` | `P > OCV²/(4·R_total)` | Fundamentally impossible at this voltage |
| `ERROR_INCOMPLETE` | Missing bridge value or unresolved hop (D2) | The data, before anything can run |

**This is why the report needs two margins, not one.** Voltage margin (§7.3) and *delivery*
margin — the fraction of the demanded current or power actually supplied:

| Demand | I | V_sink | V margin | Delivered | Verdict |
|---|---|---|---|---|---|
| 20.0 W | 2.5615 A | 7.8079 V | 94.1% | 100.0% | PASS |
| 50.0 W | 6.6667 A | 7.5000 V | 84.6% | 100.0% | PASS |
| 59.2 W | 8.0000 A | 7.4000 V | 81.5% | 100.0% | PASS, exactly at the limit |
| 70.0 W | 8.0000 A | 7.4000 V | **81.5%** | **84.6%** | FAIL: source current limit |
| 250.0 W | — | — | — | — | FAIL: no steady state |

The 70 W row is the one that makes the case. **Voltage margin 81.5% — the copper is fine, it
passes on voltage. Delivery 84.6% — the source cannot supply the demand.** A single FAIL flag
would send someone off to widen traces that were never the problem.

**Failures co-occur, and the order is causal (D10).** A source limit is a *cause*; the
under-voltage it produces is its *consequence*. Reporting only one loses half the story. With
a stiffer requirement — a boost input needing 7.0 V, 0.10 Ω of path, 1.0 V of budget:

| Demand | I | V_sink | V margin | Delivered | Flags |
|---|---|---|---|---|---|
| 40.0 W | 5.5848 A | 7.1623 V | +16.2% | 100.0% | PASS |
| 54.4 W | 8.0000 A | 6.8000 V | −20.0% | 100.0% | `FAIL_VOLTAGE` |
| 70.0 W | 8.0000 A | 6.8000 V | −20.0% | 77.7% | `FAIL_SOURCE_LIMIT`, `FAIL_VOLTAGE` |

The middle row is worth noting: the source is *exactly* at its limit and still delivers full
power, yet the voltage has already failed. The two conditions are genuinely independent, so
the verdict is a **list of reason codes**, ordered cause-first, not a single value.

**One physical caveat the report should state.** When the limit binds, the clamped answer
(`I = Imax`, `V = OCV − Imax·R_total`) describes a supply in constant-current mode with a load
that tolerates being starved. A *true* constant-power load has no stable operating point here:
as voltage sags it demands more current, the source cannot give it, and the rail collapses or
hiccups. So `FAIL_SOURCE_LIMIT` on a constant-power sink should say the operating point shown
is the CC-mode idealisation, not a prediction that the system sits there quietly.

### 7.6 Parallel imbalance (D8)

**Definition**: the largest deviation of any branch from its equal share, as a percentage of
that equal share. For two branches this reduces to `(I_max − I_min) / I_total`, and it
generalises to N without changing meaning.

| Branch resistances | Current shares | Imbalance | Band |
|---|---|---|---|
| 2.10, 2.10 mΩ | 50.0 / 50.0 | 0.0% | balanced |
| 2.10, 2.30 mΩ | 52.3 / 47.7 | 4.5% | balanced |
| 2.10, 2.50 mΩ | 54.3 / 45.7 | 8.7% | acceptable |
| 2.10, 3.00 mΩ | 58.8 / 41.2 | **17.6%** | WARN |
| 2.10, 4.20 mΩ | 66.7 / 33.3 | 33.3% | FLAG |
| 2.10, 2.10, 3.00 mΩ | 37.0 / 37.0 / 25.9 | 22.2% | FLAG |

Bands: balanced below 5%, acceptable to 10%, **warn 10–20%, flag above 20%** — every threshold
overridable, and **the percentage is always printed** whether or not it trips a band. A 4.5%
imbalance is fine but is still worth seeing, because it moves with temperature: the hotter
branch rises in resistance and sheds current, which is self-correcting for FETs in linear
regions but not for everything.

The three-branch row is a reminder that N > 2 does not average away — two matched parts and one
outlier still flags.

## 8. Remaining questions


**Q11** — Within `.pathminer/`, should generated reports live alongside the inputs or in a
`reports/` subfolder that can be gitignored? Inputs are worth committing; reports are
regenerable.

**Q12** — Does the rename to PathMiner extend to the existing single-file tool, or does
`pcb_trace_resistance.py` keep its name and become one component of PathMiner? The change log
and version tags carry across either way.
