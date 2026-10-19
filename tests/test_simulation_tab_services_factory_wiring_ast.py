import ast
from pathlib import Path


def test_simulation_tab_passes_stations_to_factory():
    tree=ast.parse(Path('src/gui/simulation_tab.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func,'attr',None)=='create':
            if getattr(node.func.value,'id',None)=='SimulationServicesFactory':
                assert len(node.args) >= 2
                return
    raise AssertionError('Factory.create call not found')
