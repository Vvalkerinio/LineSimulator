import contextlib, json
from src.io.configuration_serializer import load_configuration
from src.core.event_driven_simulator import EventDrivenSimulator
from src.core.simulation_services_factory import SimulationServicesFactory
from src.analysis.kpi_engine import KPIEngine
from src.analysis.manipulator_separation_report import ManipulatorSeparationReport
from src.core.simulation_debug import debug_mode

c=load_configuration('configs/default.json')
c.manipulators[0].work_zone_start=1
c.manipulators[0].work_zone_end=6
c.manipulators[0].preferred_parking_position=5
for st in c.stations:
    if getattr(st, 'shared_bath_group', None) == 'ODT':
        st.shared_bath_stagger_mode='percent'
        st.shared_bath_stagger_value=50.0
services=SimulationServicesFactory.create(c.manipulators,c.stations)
with open('/mnt/data/a855_acceptance_debug.log','w',encoding='utf-8') as out, contextlib.redirect_stdout(out):
    with debug_mode(True):
        result=EventDrivenSimulator(c,services=services).run()
kpi=KPIEngine().calculate(result,getattr(c,'pieces_per_transport',7))
sep=ManipulatorSeparationReport().analyze(result,c)
unique_hangers=sorted({int(t.hanger_id) for t in result.manipulator_tasks})
hard=sum(getattr(x,'compliance_status','') in ('HARD_MIN_VIOLATION','HARD_MAX_VIOLATION') for x in result.process_compliance)
summary={'generated_hangers_with_tasks':len(unique_hangers),'first_hanger':unique_hangers[0] if unique_hangers else None,'last_hanger':unique_hangers[-1] if unique_hangers else None,'events':result.processed_events,'tasks':len(result.manipulator_tasks),'deadlocks':len(result.deadlocks),'hard_violations':hard,'throughput_transport_h':kpi.transports_per_hour,'throughput_szt_h':kpi.parts_per_hour,'minimum_distance':sep.minimum_distance,'separation':sep.status,'deferred':len(getattr(result,'deferred_transports',[]))}
print(json.dumps(summary,indent=2))
assert summary['generated_hangers_with_tasks'] > 0
assert summary['tasks'] > 0
assert summary['deadlocks'] == 0
assert summary['separation'] == 'OK'
assert summary['deferred'] == 0
