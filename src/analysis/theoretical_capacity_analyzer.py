from __future__ import annotations

from dataclasses import dataclass, field
from math import inf
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CapacityBound:
    name: str
    throughput_per_hour: float
    limiting_resource: str
    mode: str
    category: str
    certifying: bool = True
    assumptions: tuple[str, ...] = ()
    details: dict = field(default_factory=dict)

    @property
    def finite(self):
        return self.throughput_per_hour != inf


@dataclass(frozen=True)
class TheoreticalCapacityReport:
    nominal_bounds: tuple[CapacityBound, ...]
    possible_bounds: tuple[CapacityBound, ...]
    nominal_upper_bound: float
    possible_upper_bound: float
    nominal_limiting_resource: str | None
    possible_limiting_resource: str | None
    best_simulated_throughput: float | None = None
    ideal_process_nominal_throughput: float = inf
    ideal_process_possible_throughput: float = inf
    ideal_path_nominal_seconds: float = 0.0
    ideal_path_possible_seconds: float = 0.0
    ideal_path_details: dict = field(default_factory=dict)
    pieces_per_transport: int = 1

    @property
    def nominal_gap(self):
        if self.best_simulated_throughput is None:
            return None
        return max(0.0, self.nominal_upper_bound - self.best_simulated_throughput)

    @property
    def possible_gap(self):
        if self.best_simulated_throughput is None:
            return None
        return max(0.0, self.possible_upper_bound - self.best_simulated_throughput)

    @staticmethod
    def _relative(bound, achieved):
        if achieved is None or bound <= 0.0 or bound == inf:
            return None
        return max(0.0, bound - achieved) / bound * 100.0

    @property
    def nominal_relative_gap_percent(self):
        return self._relative(self.nominal_upper_bound, self.best_simulated_throughput)

    @property
    def possible_relative_gap_percent(self):
        return self._relative(self.possible_upper_bound, self.best_simulated_throughput)

    @property
    def nominal_diagnostics(self):
        return tuple(item for item in self.nominal_bounds if not item.certifying)


class TheoreticalCapacityAnalyzer:
    """Optimistic capacity bounds and explicitly-labelled track diagnostics."""

    EPSILON = 1e-9

    def analyze(self, configuration, route: Sequence[int] | None = None,
                best_simulated_throughput: float | None = None):
        stations = tuple(
            s for s in getattr(configuration, "stations", ())
            if bool(getattr(s, "enabled", True))
        )
        manipulators = tuple(sorted(
            getattr(configuration, "manipulators", ()), key=lambda m: int(m.id)
        ))
        resolved_route = tuple(route or self._resolve_route(stations))

        nominal = self._bounds(configuration, stations, manipulators,
                               resolved_route, "nominal")
        possible = self._bounds(configuration, stations, manipulators,
                                resolved_route, "possible")
        nominal_limit, nominal_resource = self._minimum(nominal)
        possible_limit, possible_resource = self._minimum(possible)
        ideal_nominal, ideal_possible, ideal_details = self._ideal_process_model(
            stations, manipulators, resolved_route
        )
        return TheoreticalCapacityReport(
            nominal_bounds=tuple(sorted(nominal, key=self._sort_key)),
            possible_bounds=tuple(sorted(possible, key=self._sort_key)),
            nominal_upper_bound=nominal_limit,
            possible_upper_bound=possible_limit,
            nominal_limiting_resource=nominal_resource,
            possible_limiting_resource=possible_resource,
            best_simulated_throughput=(None if best_simulated_throughput is None
                                       else float(best_simulated_throughput)),
            ideal_process_nominal_throughput=ideal_nominal["pipeline_throughput"],
            ideal_process_possible_throughput=ideal_possible["pipeline_throughput"],
            ideal_path_nominal_seconds=ideal_nominal["path_seconds"],
            ideal_path_possible_seconds=ideal_possible["path_seconds"],
            ideal_path_details=ideal_details,
            pieces_per_transport=max(1, int(getattr(configuration, "pieces_per_transport", 1))),
        )


    def _ideal_process_model(self, stations, manipulators, route):
        """Ideal conflict-free cyclic pipeline with real handling times.

        Every route stage retains residence and the physical outbound transfer:
        lift, source drip, loaded travel and drop. A suitable manipulator is
        immediately available, so empty approach, conflicts, queues, parking,
        spacing and passing are ignored. Parallel shared-bath members add their
        capacities.
        """
        station_map = {int(station.id): station for station in stations}

        def transition_seconds(source, target):
            source_station = station_map.get(int(source))
            eligible = [
                manipulator for manipulator in manipulators
                if self._can_cover(manipulator, source, target)
            ]
            if not eligible:
                return None, None, 0.0
            drip = float(getattr(source_station, "drip_time", 0.0) or 0.0)
            options = []
            for manipulator in eligible:
                seconds = (
                    float(manipulator.lift_time)
                    + drip
                    + abs(int(target) - int(source))
                    * float(manipulator.travel_time_per_position)
                    + float(manipulator.drop_time)
                )
                options.append((seconds, int(manipulator.id)))
            seconds, manipulator_id = min(options)
            return seconds, manipulator_id, drip

        transition_map = {}
        transitions = []
        for source, target in zip(route, route[1:]):
            seconds, manipulator_id, drip = transition_seconds(source, target)
            transition_map[int(source)] = seconds
            transitions.append({
                "source": int(source),
                "target": int(target),
                "ideal_manipulator": manipulator_id,
                "seconds": seconds,
                "drip_seconds": drip,
                "feasible": seconds is not None,
            })

        def calculate(mode):
            residence_total = 0.0
            handling_total = 0.0
            resources = {}
            stage_details = []
            for station_id in route:
                station = station_map.get(int(station_id))
                if station is None:
                    continue
                residence = 0.0
                if bool(getattr(station, "is_process_bath", True)):
                    residence = self._minimum_process_time(station, mode)
                    residence_total += residence
                handling = transition_map.get(int(station_id))
                handling = 0.0 if handling is None else float(handling)
                handling_total += handling
                cycle = residence + handling
                if cycle <= self.EPSILON:
                    continue
                group = str(getattr(station, "shared_bath_group", "") or "").strip()
                resource = f"shared_bath:{group}" if group else f"station:{station.id}"
                rate = 3600.0 / cycle
                resources[resource] = resources.get(resource, 0.0) + rate
                stage_details.append({
                    "station_id": int(station.id),
                    "resource": resource,
                    "residence_seconds": residence,
                    "outbound_handling_seconds": handling,
                    "ideal_stage_cycle_seconds": cycle,
                    "capacity_per_hour": rate,
                })
            if not resources:
                throughput = inf
                limiting = None
            else:
                limiting, throughput = min(resources.items(), key=lambda item: item[1])
            return {
                "pipeline_throughput": throughput,
                "path_seconds": residence_total + handling_total,
                "residence_seconds": residence_total,
                "handling_seconds": handling_total,
                "limiting_resource": limiting,
                "resource_capacities": resources,
                "stages": stage_details,
            }

        nominal = calculate("nominal")
        possible = calculate("possible")
        details = {
            "route": list(route),
            "nominal_residence_seconds": nominal["residence_seconds"],
            "nominal_handling_seconds": nominal["handling_seconds"],
            "possible_residence_seconds": possible["residence_seconds"],
            "possible_handling_seconds": possible["handling_seconds"],
            "nominal_limiting_resource": nominal["limiting_resource"],
            "possible_limiting_resource": possible["limiting_resource"],
            "nominal_resource_capacities": nominal["resource_capacities"],
            "possible_resource_capacities": possible["resource_capacities"],
            "nominal_stages": nominal["stages"],
            "possible_stages": possible["stages"],
            "transitions": transitions,
            "assumptions": [
                "a suitable manipulator is always immediately available",
                "empty approach, collisions, passing, spacing, queues, parking and reservations are ignored",
                "each stage retains residence plus outbound lift, source drip, loaded travel and drop",
                "parallel members of a shared bath add their ideal stage capacities",
            ],
        }
        return nominal, possible, details

    def _bounds(self, configuration, stations, manipulators, route, mode):
        bounds = list(self._process_bounds(stations, mode))
        transitions = self._transition_options(route, manipulators)
        pooled = self._pooled_bound(transitions, manipulators, route, mode)
        if pooled:
            bounds.append(pooled)
        bounds.extend(self._mandatory_manipulator_bounds(transitions, manipulators, mode))
        bounds.extend(self._interface_diagnostics(
            transitions, manipulators,
            float(getattr(configuration, "minimum_manipulator_spacing", 0.0)),
            mode,
        ))
        return bounds

    def _process_bounds(self, stations: Iterable, mode):
        resources = {}
        for station in stations:
            if not bool(getattr(station, "is_process_bath", True)):
                continue
            group = str(getattr(station, "shared_bath_group", "") or "").strip()
            key = f"shared_bath:{group}" if group else f"station:{station.id}"
            resources.setdefault(key, []).append(station)
        for resource, members in resources.items():
            details, capacity = [], 0.0
            for station in members:
                minimum = self._minimum_process_time(station, mode)
                member_capacity = inf if minimum <= self.EPSILON else 3600.0 / minimum
                capacity += member_capacity
                details.append({
                    "station_id": int(station.id),
                    "minimum_residence_seconds": minimum,
                    "capacity_per_hour": member_capacity,
                })
            yield CapacityBound(
                "Process bath capacity", capacity, resource, mode,
                category="technology", certifying=True,
                assumptions=("minimum residence is optimistic bath occupation",
                             "downstream blocking is ignored"),
                details={"members": details},
            )

    def _transition_options(self, route, manipulators):
        output = []
        for source, target in zip(route, route[1:]):
            options = []
            for manipulator in manipulators:
                if not self._can_cover(manipulator, source, target):
                    continue
                loaded = abs(target - source) * float(manipulator.travel_time_per_position)
                work = float(manipulator.lift_time) + loaded + float(manipulator.drop_time)
                options.append({"manipulator_id": int(manipulator.id), "work": work,
                                "loaded": loaded})
            output.append({"source": int(source), "target": int(target),
                           "options": options})
        return output

    def _pooled_bound(self, transitions, manipulators, route, mode):
        total, details = 0.0, []
        for transition in transitions:
            if not transition["options"]:
                return CapacityBound(
                    "Pooled manipulator workload", 0.0,
                    f"unreachable_transition:{transition['source']}->{transition['target']}",
                    mode, "transport", True,
                    assumptions=("each transition must have an eligible manipulator",),
                    details=transition,
                )
            option = min(transition["options"], key=lambda item: item["work"])
            total += option["work"]
            details.append({**transition, "best_option": option})
        capacity = inf if total <= self.EPSILON else 3600.0 * len(manipulators) / total
        return CapacityBound(
            "Pooled manipulator workload", capacity, "manipulator_pool", mode,
            "transport", True,
            assumptions=("empty repositioning is ignored",
                         "work is perfectly divisible between manipulators",
                         "track conflicts and YIELD are relaxed"),
            details={"route": list(route), "minimum_work_seconds_per_part": total,
                     "transitions": details},
        )

    def _mandatory_manipulator_bounds(self, transitions, manipulators, mode):
        mandatory = {int(m.id): [] for m in manipulators}
        for transition in transitions:
            if len(transition["options"]) == 1:
                option = transition["options"][0]
                mandatory[option["manipulator_id"]].append((transition, option))
        for manipulator in manipulators:
            items = mandatory[int(manipulator.id)]
            work = sum(option["work"] for _, option in items)
            if work <= self.EPSILON:
                continue
            yield CapacityBound(
                "Mandatory manipulator workload", 3600.0 / work,
                f"manipulator:M{manipulator.id}", mode, "manipulator", True,
                assumptions=("only transitions with exactly one eligible manipulator are counted",
                             "empty repositioning is ignored"),
                details={"mandatory_work_seconds_per_part": work,
                         "transitions": [{"source": t["source"], "target": t["target"],
                                          "work": o["work"]} for t, o in items]},
            )

    def _interface_diagnostics(self, transitions, manipulators, spacing, mode):
        for left, right in zip(manipulators, manipulators[1:]):
            left_end = float(left.work_zone_end)
            right_start = float(right.work_zone_start)
            interface = (left_end + right_start) / 2.0
            crossing = []
            service = 0.0
            for transition in transitions:
                source, target = transition["source"], transition["target"]
                if (source - interface) * (target - interface) >= 0:
                    continue
                eligible = [o for o in transition["options"]
                            if o["manipulator_id"] in (int(left.id), int(right.id))]
                if not eligible:
                    continue
                fastest = min(eligible, key=lambda item: item["loaded"])
                critical_distance = max(spacing, 1.0)
                speed = min(
                    float(m.travel_time_per_position) for m in (left, right)
                    if float(m.travel_time_per_position) > self.EPSILON
                )
                critical_time = critical_distance * speed
                service += critical_time
                crossing.append({"source": source, "target": target,
                                 "critical_track_seconds": critical_time,
                                 "best_loaded_option": fastest})
            if not crossing:
                continue
            yield CapacityBound(
                "Zone-interface track relaxation", 3600.0 / service,
                f"interface:M{left.id}/M{right.id}", mode, "track_interface", False,
                assumptions=("diagnostic relaxation, not a certified upper bound",
                             "critical corridor width equals max(spacing, one station)",
                             "empty moves and YIELD are excluded"),
                details={"interface_position": interface,
                         "crossings_per_part": len(crossing),
                         "critical_seconds_per_part": service,
                         "crossings": crossing},
            )

    @staticmethod
    def _can_cover(manipulator, source, target):
        low = min(int(manipulator.work_zone_start), int(manipulator.work_zone_end))
        high = max(int(manipulator.work_zone_start), int(manipulator.work_zone_end))
        return low <= int(source) <= high and low <= int(target) <= high

    @staticmethod
    def _minimum_process_time(station, mode):
        nominal = float(station.min_process_time)
        if mode == "possible":
            value = getattr(station, "possible_min_process_time", None)
            return nominal if value is None else float(value)
        return nominal

    @staticmethod
    def _resolve_route(stations):
        route, seen = [], set()
        for station in stations:
            group = str(getattr(station, "shared_bath_group", "") or "").strip()
            if group and group.lower() != "none":
                if group in seen:
                    continue
                seen.add(group)
            route.append(int(station.id))
        return route

    @staticmethod
    def _sort_key(bound):
        return (not bound.certifying, bound.throughput_per_hour, bound.limiting_resource)

    @staticmethod
    def _minimum(bounds):
        certified = [b for b in bounds if b.certifying and b.finite]
        if not certified:
            return inf, None
        limiting = min(certified, key=lambda b: b.throughput_per_hour)
        return limiting.throughput_per_hour, limiting.limiting_resource
