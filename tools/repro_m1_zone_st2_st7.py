import contextlib, json
from src.io.configuration_serializer import load_configuration
from src.core.event_driven_simulator import EventDrivenSimulator
from src.core.simulation_services_factory import SimulationServicesFactory
from src.analysis.kpi_engine import KPIEngine
from src.analysis.manipulator_separation_report import ManipulatorSeparationReport
from src.core.simulation_debug import debug_mode
c=load_configuration('configs/default.json')
c.infinite_feed=True;c.feed_duration=3600.0;c.warmup_time=1800.0;c.steady_state_window=300.0;c.pieces_per_transport=7;c.minimum_manipulator_spacing=2.0
c.manipulators[0].work_zone_start=1;c.manipulators[0].work_zone_end=6
for st in c.stations:
    if getattr(st,'shared_bath_group',None)=='ODT':
        st.shared_bath_stagger_mode='alternate';st.shared_bath_stagger_value=80.0
services=SimulationServicesFactory.create(c.manipulators,c.stations)
with open('/mnt/data/a850_debug.log','w',encoding='utf-8') as out, contextlib.redirect_stdout(out):
    with debug_mode(True):
        result=EventDrivenSimulator(c,services=services).run();kpi=KPIEngine().calculate(result,7)
sep=ManipulatorSeparationReport().analyze(result,c)
hard=sum(getattr(x,'compliance_status','') in ('HARD_MIN_VIOLATION','HARD_MAX_VIOLATION') for x in result.process_compliance)
summary={'events':result.processed_events,'tasks':len(result.manipulator_tasks),'deadlocks':len(result.deadlocks),'hard_violations':hard,'throughput_transport_h':kpi.transports_per_hour,'throughput_szt_h':kpi.parts_per_hour,'minimum_distance':sep.minimum_distance,'separation':sep.status,'deferred':len(getattr(result,'deferred_transports',[]))}
print(json.dumps(summary,indent=2))
assert summary['deadlocks']==0 and summary['separation']=='OK' and summary['deferred']==0
