from vrptw_hybrid.solvers import (
    BaseSolver,
    CPSATVRPTWSolver,
    GreedySolver,
    ORToolsRoutingSolver,
)


def test_existing_solvers_are_base_solver_instances() -> None:
    assert isinstance(GreedySolver(), BaseSolver)
    assert isinstance(CPSATVRPTWSolver(), BaseSolver)
    assert isinstance(ORToolsRoutingSolver(), BaseSolver)
