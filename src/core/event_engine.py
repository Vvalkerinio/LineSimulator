import heapq
class EventEngine:
    def __init__(self): self.q=[]
    def schedule(self,e): heapq.heappush(self.q,e)
    def has_events(self): return bool(self.q)
    def pop(self): return heapq.heappop(self.q)
