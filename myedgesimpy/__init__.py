"""MyEdgeSimPy: MEC service-state migration simulator built on top of EdgeSimPy.

The package is organised around the four questions of the study:

1. How do vehicles move across cells and hand over between edge nodes?
   -> :mod:`myedgesimpy.mobility`, :mod:`myedgesimpy.topology`
2. What do the MEC services do, what data moves, and what state must follow the user?
   -> :mod:`myedgesimpy.services`
3. Which metrics capture the cost/continuity trade-off, and how does mobility speed change it?
   -> :mod:`myedgesimpy.metrics`, :mod:`myedgesimpy.runner`
4. How can migration be optimised (when to migrate, how much state to move, how to keep the
   service alive while state is transferred)?
   -> :mod:`myedgesimpy.migration`
"""

__version__ = "0.1.0"

__all__ = ["__version__"]