"""Sampler for Apify's generative Bayesian networks.

This is a Python port of the sampling half of ``generative-bayesian-network``
(``bayesian-network.ts`` / ``bayesian-node.ts``) from
https://github.com/apify/fingerprint-suite (Apache-2.0). Only sampling is
ported; the training code that produces the network files is not needed here.

A network file is a zip holding ``network.json``::

    {"nodes": [{"name": ..., "parentNames": [...], "possibleValues": [...],
                "conditionalProbabilities": {"deeper": {parentValue: {...}},
                                             "skip": {...}}}, ...]}

Nodes are stored in sampling order, so every parent precedes its children.
``conditionalProbabilities`` is a tree with one level per parent; the leaves
map each possible value of the node to its probability. ``skip`` is the
fallback used when a parent value never occurred in the training data.
"""
from __future__ import annotations

import json
import random
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

Sample = Dict[str, str]


class BayesianNetwork:
    def __init__(self, path: Union[str, Path]):
        with zipfile.ZipFile(path) as zf:
            definition = json.loads(zf.read(zf.namelist()[0]))
        self.nodes: List[Dict[str, Any]] = definition["nodes"]
        self.by_name: Dict[str, Dict[str, Any]] = {n["name"]: n for n in self.nodes}
        # id(distribution) -> (values, weights); distributions live as long as the network
        self._cache: Dict[int, Tuple[List[str], List[float]]] = {}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _distribution(node: Mapping[str, Any], sample: Mapping[str, str]) -> Dict[str, float]:
        dist = node["conditionalProbabilities"]
        for parent in node["parentNames"]:
            deeper = dist.get("deeper", {})
            value = sample.get(parent)
            if value in deeper:
                dist = deeper[value]
            elif "skip" in dist:
                dist = dist["skip"]
            else:
                raise KeyError(
                    "no distribution for node %r given %s=%r" % (node["name"], parent, value)
                )
        return dist

    def _pick(self, rng: random.Random, dist: Dict[str, float]) -> str:
        key = id(dist)
        cached = self._cache.get(key)
        if cached is None:
            values = list(dist.keys())
            cached = (values, [dist[v] for v in values])
            self._cache[key] = cached
        return rng.choices(cached[0], weights=cached[1])[0]

    # ----------------------------------------------------------------- sampling
    def generate_sample(
        self, rng: random.Random, input_values: Optional[Mapping[str, str]] = None
    ) -> Sample:
        """Forward-sample every node, keeping any values passed in ``input_values``."""
        sample: Sample = dict(input_values or {})
        for node in self.nodes:
            if node["name"] not in sample:
                sample[node["name"]] = self._pick(rng, self._distribution(node, sample))
        return sample

    def generate_consistent_sample(
        self, rng: random.Random, value_possibilities: Mapping[str, Sequence[str]]
    ) -> Optional[Sample]:
        """Sample while restricting chosen nodes to lists of allowed values.

        Mirrors ``generateConsistentSampleWhenPossible``: if a choice leads to a
        dead end deeper in the network, that value is banned and another is
        tried. Returns ``None`` when no consistent sample exists.
        """
        return self._recurse(rng, {}, value_possibilities, 0)

    def _recurse(
        self,
        rng: random.Random,
        sample: Sample,
        possibilities: Mapping[str, Sequence[str]],
        depth: int,
    ) -> Optional[Sample]:
        node = self.nodes[depth]
        name = node["name"]
        dist = self._distribution(node, sample)
        allowed = possibilities.get(name)
        banned: Set[str] = set()
        last = depth + 1 == len(self.nodes)

        while True:
            if allowed is None and not banned:
                value = self._pick(rng, dist)
            else:
                pool = allowed if allowed is not None else list(dist.keys())
                candidates = [v for v in pool if v in dist and v not in banned]
                if not candidates:
                    return None
                value = rng.choices(candidates, weights=[dist[v] for v in candidates])[0]

            sample[name] = value
            if last:
                return sample
            result = self._recurse(rng, sample, possibilities, depth + 1)
            if result is not None:
                return result
            banned.add(value)
            del sample[name]
