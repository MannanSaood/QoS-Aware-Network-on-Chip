# BookSim traffic parameter correction

During visual inspection of the first full-load preview, mixed-hotspot locations
produced almost identical saturated curves and bursty injection plateaued too
early. The experiment configuration used the wrong parameter-list syntax.

BookSim's `tokenize_str` requires braces around an argument list, including the
outer list containing the hotspot-node and weight lists. Correct forms are
`hotspot({{nodes...},{weights...}})` and `on_off({0.02,0.02,-1})`.
The previous hotspot expression was interpreted as a single target, router 0;
the previous on/off expression used the default beta of 0.5 instead of 0.02.
Successful process exits and numeric range checks could not detect this error.

Affected BookSim cases: `bursty`, `hotspot_corner`, `hotspot_edge`, and
`hotspot_center`. Uniform, transpose, the separate 100%-center `hotspot` case,
and NS-2's generated arrival schedules are unaffected. Original affected raw
outputs are archived under `results/development/invalid_parameter_format` when
rerun. The invalid preview was archived there as well. Do not cite earlier
bursty/mixed-hotspot BookSim figures from the legacy report or traffic smoke runs.

`booksim_parameter_lists_v3` identifies corrected affected runs. Resume refuses
older profiles, and primary report preparation rejects obsolete rows. No valid
uniform/transpose or NS-2 measurements need to be discarded.

`scripts/validate_booksim_traffic.py` compiles against the actual pinned BookSim
configuration parser and traffic/injection generator objects. Its 28 checks
cover all four mesh sizes, all six traffic cases, correct hotspot identities
and probabilities, offered injection means, and adjacent-cycle burst event
probabilities at loads 0.1 and 1.0. These passed after the correction.
The earlier Python traffic test covered NS-2's generator only; it was insufficient
to verify that BookSim interpreted its configuration in the same way.

This correction addresses the experiment setup. It does not justify modifying
measured data to make a particular routing algorithm win. Equal curves may
remain where the actual routes, traffic conditions or bottlenecks are similar.
