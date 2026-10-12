"""Visualisation of finished cases with ParaView (separate image, re-runnable).

Pure-Python parts (this package, `study`, `geom`) import without ParaView;
`pvlib` and `render_case` need it and run inside the iom-cfd-viz image.
"""


class Skip(Exception):
    """Raised by a view function when the case lacks the data it needs."""
