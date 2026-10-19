from src.core.trajectory_manager import TrajectoryManager

def test_index_preserves_position_interpolation_and_order():
    m=TrajectoryManager(); m.add_move(1,5,6,20,1); m.add_move(1,1,3,0,1); m.add_move(1,3,5,10,1)
    assert [x.start_time for x in m.segments_for(1)] == [0,10,20]
    assert m.position_at(1,1) == 2
    assert m.position_at(1,15) == 5

def test_overlapping_is_local_and_revision_changes():
    m=TrajectoryManager()
    for i in range(100): m.add_move(1,i,i+1,i*10,1)
    assert [x.start_time for x in m.segments_overlapping(1,495,506)] == [500]
    assert m.revision == 100
