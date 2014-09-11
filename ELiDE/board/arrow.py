# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
"""That which displays a one-way connection between two places.

An arrow connects two spots, the origin and the destination, and it
points from the origin to the destination, regardless of where on the
screen they are at the moment.

"""
from math import cos, sin, hypot, atan
from LiSE.util import (
    wedge_offsets_rise_run,
    truncated_line,
    fortyfive)
from kivy.graphics import Line, Color
from kivy.uix.widget import Widget
from kivy.properties import (
    ObjectProperty,
    NumericProperty,
    ListProperty,
    AliasProperty,
    BooleanProperty
)
from kivy.clock import Clock


def get_points(ox, orx, oy, ory, dx, drx, dy, dry, taillen):
    """Return points to use for an arrow from ``ox,oy`` to ``dx,dy`` where
    the origin has dimensions ``2*orx,2*ory``, the destination has
    dimensions ``2*drx,2*dry``, and the bits of the arrow not actually
    connecting the ends of it--the edges of the arrowhead--have length
    ``taillen``.

    """
    ox += orx
    oy += ory
    dx += drx
    dy += dry
    if drx > dry:
        dr = drx
    else:
        dr = dry
    if dy < oy:
        yco = -1
    else:
        yco = 1
    if dx < ox:
        xco = -1
    else:
        xco = 1
    (leftx, boty, rightx, topy) = truncated_line(
        float(ox * xco), float(oy * yco),
        float(dx * xco), float(dy * yco),
        dr + 1)
    rise = topy - boty
    run = rightx - leftx
    if rise == 0:
        xoff1 = cos(fortyfive) * taillen
        yoff1 = xoff1
        xoff2 = xoff1
        yoff2 = -1 * yoff1
    elif run == 0:
        xoff1 = sin(fortyfive) * taillen
        yoff1 = xoff1
        xoff2 = -1 * xoff1
        yoff2 = yoff1
    else:
        (xoff1, yoff1, xoff2, yoff2) = wedge_offsets_rise_run(
            rise, run, taillen)
    x1 = (rightx - xoff1) * xco
    x2 = (rightx - xoff2) * xco
    y1 = (topy - yoff1) * yco
    y2 = (topy - yoff2) * yco
    endx = rightx * xco
    endy = topy * yco
    r = [ox, oy,
         endx, endy, x1, y1,
         endx, endy, x2, y2,
         endx, endy]
    return r


class Arrow(Widget):
    """A widget that points from one :class:`~LiSE.gui.board.Spot` to
    another.

    :class:`Arrow`s are the graphical representations of
    :class:`~LiSE.model.Portal`s. They point from the :class:`Spot`
    representing the :class:`Portal`'s origin, to the one representing
    its destination.

    """
    margin = 10
    """When deciding whether a touch collides with me, how far away can
    the touch get before I should consider it a miss?"""
    w = 1
    """The width of the inner, brighter portion of the :class:`Arrow`. The
    whole :class:`Arrow` will end up thicker."""
    board = ObjectProperty()
    """The board on which I am displayed."""
    portal = ObjectProperty()
    """The portal that I represent."""
    pawns_here = ListProperty([])
    points = ListProperty([])
    slope = NumericProperty(0.0, allownone=True)
    y_intercept = NumericProperty(0)
    origin = ObjectProperty()
    destination = ObjectProperty()
    reciprocal = ObjectProperty(None, allownone=True)
    engine = AliasProperty(
        lambda self: self.board.engine if self.board else None,
        lambda self, v: None,
        bind=('board',)
    )
    repointed = BooleanProperty(True)

    @property
    def reciprocal(self):
        orign = self.portal['origin']
        destn = self.portal['destination']
        if (
                destn in self.board.arrow and
                orign in self.board.arrow[destn]
        ):
            return self.board.arrow[destn][orign]
        else:
            return None

    def __init__(self, **kwargs):
        """Bind some properties, and put the relevant instructions into the
        canvas--but don't put any point data into the instructions
        just yet. For that, wait until ``on_parent``, when we are
        guaranteed to know the positions of our endpoints.

        """
        super().__init__(**kwargs)
        self._trigger_repoint = Clock.create_trigger(
            self._repoint,
            timeout=-1
        )
        self._trigger_update = Clock.create_trigger(
            self._update
        )
        self.finalize()

    def finalize(self, *args):
        if None in (
                self.board,
                self.engine,
                self.portal
        ):
            Clock.schedule_once(self.finalize, 0)
            if self.board is None:
                print("no board")
            if self.engine is None:
                print("no engine")
            if self.portal is None:
                print("no portal")
            return
        orign = self.portal["origin"]
        destn = self.portal["destination"]
        self.origin = self.board.spot[orign]
        self.origin.bind(
            pos=self._trigger_repoint,
            size=self._trigger_repoint
        )
        self.destination = self.board.spot[destn]
        self.destination.bind(
            pos=self._trigger_repoint,
            size=self._trigger_repoint
        )
        self.bg_color = Color(*self.board.arrow_bg)
        self.fg_color = Color(*self.board.arrow_fg)
        self.bg_line = Line(width=self.w * 1.4)
        self.fg_line = Line(width=self.w)
        self.canvas.add(self.bg_color)
        self.canvas.add(self.bg_line)
        self.canvas.add(self.fg_color)
        self.canvas.add(self.fg_line)
        self._trigger_repoint()

    def on_points(self, *args):
        """Propagate my points to both my lines"""
        self.bg_line.points = self.points
        self.fg_line.points = self.points

    def pos_along(self, pct):
        """Return coordinates for where a Pawn should be if it has travelled
        along ``pct`` percent of my length.

        Might get complex when I switch over to using beziers for
        arrows, but for now this is quite simple, using distance along
        a line segment.

        """
        (ox, oy) = self.origin.center
        (dx, dy) = self.destination.center
        xdist = (dx - ox) * pct
        ydist = (dy - oy) * pct
        return (ox + xdist, oy + ydist)

    def _update(self, *args):
        if (
                len(self.board.spots_to_update) +
                len(self.board.pawns_to_update) > 0 or
                not self.repointed
        ):
            Clock.schedule_once(self._update, 0)
            return
        for pawn in self.pawns_here:
            t2 = pawn.thing['next_arrival_time']
            if t2 is None:
                pawn.pos = self.center  # might be redundant
                continue
            else:
                t1 = pawn.thing['arrival_time']
                duration = float(t2 - t1)
                passed = float(self.engine.tick - t1)
                progress = passed / duration
            os = self.board.spot[self.portal['origin']]
            ds = self.board.spot[self.portal['destination']]
            (ox, oy) = os.pos
            (dx, dy) = ds.pos
            w = dx - ox
            h = dy - oy
            x = ox + w * progress
            y = oy + h * progress
            pawn.pos = (x, y)

    def _get_points(self):
        """Return the coordinates of the points that describe my shape."""
        orig = self.origin
        dest = self.destination
        (ox, oy) = orig.pos
        ow = orig.width if hasattr(orig, 'width') else 0
        taillen = float(self.board.arrowhead_size)
        orx = ow / 2
        ory = ow / 2
        (dx, dy) = dest.pos
        (dw, dh) = dest.size if hasattr(dest, 'size') else (0, 0)
        drx = dw / 2
        dry = dh / 2
        return get_points(ox, orx, oy, ory, dx, drx, dy, dry, taillen)

    def _get_slope(self):
        """Return a float of the increase in y divided by the increase in x,
        both from left to right."""
        orig = self.origin
        dest = self.destination
        ox = orig.x
        oy = orig.y
        dx = dest.x
        dy = dest.y
        if oy == dy:
            return 0
        elif ox == dx:
            return None
        else:
            rise = dy - oy
            run = dx - ox
            return rise / run

    def _get_b(self):
        """Return my Y-intercept.

        I probably don't really hit the left edge of the window, but
        this is where I would, if I were long enough.

        """
        orig = self.origin
        dest = self.destination
        (ox, oy) = orig.pos
        (dx, dy) = dest.pos
        denominator = dx - ox
        x_numerator = (dy - oy) * ox
        y_numerator = denominator * oy
        return ((y_numerator - x_numerator), denominator)

    def _repoint(self, *args):
        """Recalculate points, y-intercept, and slope"""
        if None in (self.origin, self.destination):
            Clock.schedule_once(self._repoint, 0)
            return
        self.points = self._get_points()
        self.slope = self._get_slope()
        self.y_intercept = self._get_b()
        self.repointed = True

    def collide_point(self, x, y):
        """Return True iff the point falls sufficiently close to my core line
        segment to count as a hit.

        """
        if not super(Arrow, self).collide_point(x, y):
            return False
        if None in (self.board, self.portal):
            return False
        orig = self.origin
        dest = self.destination
        (ox, oy) = orig.pos
        (dx, dy) = dest.pos
        if ox == dx:
            return abs(y - dy) <= self.w
        elif oy == dy:
            return abs(x - dx) <= self.w
        else:
            correct_angle_a = atan(dy / dx)
            observed_angle_a = atan(y / x)
            error_angle_a = abs(observed_angle_a - correct_angle_a)
            error_seg_len = hypot(x, y)
            return sin(error_angle_a) * error_seg_len <= self.margin
