import pyglet
import ctypes
import math
import logging
from math import atan, pi, sin, cos, hypot
from edge import Edge

logger = logging.getLogger(__name__)

ninety = math.pi / 2

fortyfive = math.pi / 4

threesixty = math.pi * 2


def average(*args):
    n = len(args)
    return sum(args)/n


line_len_rise_run = hypot


def line_len(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return hypot(rise, run)


def slope_theta_rise_run(rise, run):
    try:
        return atan(rise/run)
    except ZeroDivisionError:
        if rise >= 0:
            return ninety
        else:
            return -1 * ninety


def slope_theta(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return slope_theta_rise_run(rise, run)


def opp_theta_rise_run(rise, run):
    try:
        return atan(run/rise)
    except ZeroDivisionError:
        if run >= 0:
            return ninety
        else:
            return -1 * ninety


def opp_theta(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return opp_theta_rise_run(rise, run)


def truncated_line(leftx, boty, rightx, topy, r, from_start=False):
    # presumes pointed up and right
    if r == 0:
        return (leftx, boty, rightx, topy)
    rise = topy - boty
    run = rightx - leftx
    length = line_len_rise_run(rise, run) - r
    theta = slope_theta_rise_run(rise, run)
    if from_start:
        leftx = rightx - math.cos(theta) * length
        boty = topy - math.sin(theta) * length
    else:
        rightx = leftx + math.cos(theta) * length
        topy = boty + math.sin(theta) * length
    return (leftx, boty, rightx, topy)


def extended_line(leftx, boty, rightx, topy, r):
    return truncated_line(leftx, boty, rightx, topy, -1 * r)


def trimmed_line(leftx, boty, rightx, topy, trim_start, trim_end):
    et = truncated_line(leftx, boty, rightx, topy, trim_end)
    return truncated_line(et[0], et[1], et[2], et[3], trim_start, True)


def wedge_offsets_core(theta, opp_theta, taillen):
    top_theta = theta - fortyfive
    bot_theta = pi - fortyfive - opp_theta
    xoff1 = cos(top_theta) * taillen
    yoff1 = sin(top_theta) * taillen
    xoff2 = cos(bot_theta) * taillen
    yoff2 = sin(bot_theta) * taillen
    return (
        xoff1, yoff1, xoff2, yoff2)


def wedge_offsets_rise_run(rise, run, taillen):
    # theta is the slope of a line bisecting the ninety degree wedge.
    theta = slope_theta_rise_run(rise, run)
    opp_theta = opp_theta_rise_run(rise, run)
    return wedge_offsets_core(theta, opp_theta, taillen)


def wedge_offsets_slope(slope, taillen):
    theta = atan(slope)
    opp_theta = atan(1/slope)
    return wedge_offsets_core(theta, opp_theta, taillen)


def get_line_width():
    see = ctypes.c_float()
    pyglet.gl.glGetFloatv(pyglet.gl.GL_LINE_WIDTH, see)
    return float(see.value)


def set_line_width(w):
    wcf = ctypes.c_float(w)
    pyglet.gl.glLineWidth(wcf)

class BoldLineOrderedGroup(pyglet.graphics.OrderedGroup):
    def __init__(self, order, parent=None, width=1.0):
        self.width = float(width)
        pyglet.graphics.OrderedGroup.__init__(self, order, parent)

    def set_state(self):
        pyglet.gl.glDisable(pyglet.gl.GL_LINE_SMOOTH)
        set_line_width(self.width)

class SmoothBoldLineOrderedGroup(pyglet.graphics.OrderedGroup):
    def __init__(self, order, parent=None, width=1.0):
        self.width = float(width)
        pyglet.graphics.OrderedGroup.__init__(self, order, parent)

    def set_state(self):
        set_line_width(self.width)
        pyglet.gl.glEnable(pyglet.gl.GL_LINE_SMOOTH)


class TransparencyGroup(pyglet.graphics.Group):
    def set_state(self):
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)

    def unset_state(self):
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND)


class TransparencyOrderedGroup(
        pyglet.graphics.OrderedGroup,
        TransparencyGroup):
    pass


class GameWindow:
    """Instantiates a Pyglet window and displays the given board in it."""
    arrowhead_size = 10
    arrow_width = 1.4
    edge_order = 1

    def __init__(self, gamestate, boardname):
        self.arrow_girth = self.arrow_width * 2
        self.squareoff = self.arrowhead_size * math.sin(fortyfive)
        self.db = gamestate.db
        self.gamestate = gamestate

        self.biggroup = pyglet.graphics.Group()
        self.boardgroup = pyglet.graphics.OrderedGroup(0, self.biggroup)
        self.edgegroup = pyglet.graphics.OrderedGroup(1, self.biggroup)
        self.spotgroup = pyglet.graphics.OrderedGroup(2, self.biggroup)
        self.pawngroup = pyglet.graphics.OrderedGroup(3, self.biggroup)
        self.calgroup = TransparencyOrderedGroup(4, self.biggroup)
        self.celgroup = TransparencyOrderedGroup(5, self.biggroup)
        self.labelgroup = pyglet.graphics.OrderedGroup(6, self.biggroup)
        self.topgroup = pyglet.graphics.OrderedGroup(65535, self.biggroup)
        self.linegroups = {}
        self.bggd = {}
        self.fggd = {}

        self.pressed = None
        self.hovered = None
        self.grabbed = None
        self.selected = set()
        self.edge_order = 1
        self.keep_selected = False
        self.prev_view_bot = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.dxdy_hist_ct = 0
        dxdy_hist_max = 10
        self.dx_hist = [0] * dxdy_hist_max
        self.dy_hist = [0] * dxdy_hist_max

        window = pyglet.window.Window()

        self.window = window
        self.batch = pyglet.graphics.Batch()

        self.board = self.db.boarddict[boardname]
        self.board.set_gw(self)
        self.calcols = []
        for pawn in self.board.pawndict.itervalues():
            if hasattr(pawn, 'calcol'):
                self.calcols.append(pawn.calcol)
        self.calendar = self.board.calendar
        self.drawn_board = None
        self.drawn_edges = None
        self.timeline = None

        self.onscreen = set()
        self.last_age = -1
        self.last_timeline_y = -1

        orbimg = self.db.imgdict['default_spot']
        rx = orbimg.width / 2
        ry = orbimg.height / 2
        self.create_place_cursor = (
            pyglet.window.ImageMouseCursor(orbimg, rx, ry))
        self.create_place_cursor.rx = rx
        self.create_place_cursor.ry = ry
        self.placing = False
        self.thinging = False
        self.portaling = False
        self.portal_from = None
        self.edge_from_portal_from = None
        self.left_tail_edge_from_portal_from = None
        self.right_tail_edge_from_portal_from = None
        self.portal_triple = (
            self.left_tail_edge_from_portal_from,
            self.edge_from_portal_from,
            self.right_tail_edge_from_portal_from)

        @window.event
        def on_draw():
            """Draw the background image; all spots, pawns, and edges on the
board; all visible menus; and the calendar, if it's visible."""
            # draw the edges, representing portals
            if self.portaling:
                if self.portaled > 1:
                    print "i shall portal"
                if self.portal_from is not None:
                    self.portal_triple = self.connect_arrow(
                        self.portal_from.window_x,
                        self.portal_from.window_y,
                        self.last_mouse_x,
                        self.last_mouse_y,
                        self.portal_triple)
                else:
                    dx = self.dx
                    dy = self.dy
                    length = self.arrowhead_size * 2
                    x = self.last_mouse_x
                    y = self.last_mouse_y
                    if dx == 0:
                        if dy > 0:
                            coords = (x, y - length, x, y)
                        else:
                            coords = (x, y + length, x, y)
                    elif dy == 0:
                        if dx > 0:
                            coords = (x - length, y, x, y)
                        else:
                            coords = (x + length, y, x, y)
                    else:
                        xco = 1
                        yco = 1
                        if dx < 0:
                            xco = -1
                        if dy < 0:
                            yco = -1
                        x *= xco
                        dx *= xco
                        y *= yco
                        dy *= yco
                        theta = atan(float(dy)/float(dx))
                        xleft = int(x - cos(theta) * length)
                        ybot = int(y - sin(theta) * length)
                        coords = (xleft * xco, ybot * yco, x * xco, y * yco)
                        (x1, y1, x2, y2) = coords
                        self.portal_triple = self.connect_arrow(
                            x1, y1, x2, y2, 0, self.portal_triple)
            for edge in self.board.edges:
                newstate = edge.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(edge.oldstate)
                self.onscreen.add(newstate)
                edge.oldstate = newstate
                if edge.orig.visible or edge.dest.visible:
                    edge.vertices = self.connect_arrow(
                        edge.orig.window_x,
                        edge.orig.window_y,
                        edge.dest.window_x,
                        edge.dest.window_y,
                        edge.order,
                        edge.vertices,
                        edge.dest.r,
                        edge.highlit)
                else:
                    for pair in edge.vertices:
                        for twopair in pair:
                            try:
                                twopair.delete()
                            except:
                                pass
            # draw the spots, representing places
            for spot in self.board.spotdict.itervalues():
                newstate = spot.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(spot.oldstate)
                self.onscreen.add(newstate)
                spot.oldstate = newstate
                if spot.visible and spot.img is not None:
                    try:
                        spot.sprite.x = spot.window_left
                        spot.sprite.y = spot.window_bot
                    except AttributeError:
                        spot.sprite = pyglet.sprite.Sprite(
                            spot.img.tex,
                            spot.window_left,
                            spot.window_bot,
                            batch=self.batch,
                            group=self.spotgroup)
                else:
                    try:
                        spot.sprite.delete()
                    except (AttributeError, AssertionError):
                        pass
            # draw the pawns, representing things
            for pawn in self.board.pawndict.itervalues():
                newstate = pawn.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(pawn.oldstate)
                self.onscreen.add(newstate)
                pawn.oldstate = newstate
                if pawn.visible:
                    try:
                        pawn.sprite.x = pawn.window_left
                        pawn.sprite.y = pawn.window_bot
                    except AttributeError:
                        pawn.sprite = pyglet.sprite.Sprite(
                            pawn.img.tex,
                            pawn.window_left,
                            pawn.window_bot,
                            batch=self.batch,
                            group=self.pawngroup)
                else:
                    if pawn.sprite is not None:
                        try:
                            pawn.sprite.delete()
                        except (AttributeError, AssertionError):
                            pass

            # draw the menus, really just their backgrounds for the moment
            for menu in self.board.menudict.itervalues():
                for menu_item in menu:
                    newstate = menu_item.get_state_tup()
                    if newstate in self.onscreen:
                        continue
                    self.onscreen.discard(menu_item.oldstate)
                    self.onscreen.add(newstate)
                    menu_item.oldstate = newstate
                    if menu_item.label is not None:
                        try:
                            menu_item.label.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if menu_item.visible:
                        sty = menu.style
                        if menu_item.hovered:
                            color = sty.fg_active.tup
                        else:
                            color = sty.fg_inactive.tup
                        menu_item.label = pyglet.text.Label(
                            menu_item.text,
                            sty.fontface,
                            sty.fontsize,
                            color=color,
                            x=menu_item.window_left,
                            y=menu_item.window_bot,
                            batch=self.batch,
                            group=self.labelgroup)
                newstate = menu.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(menu.oldstate)
                self.onscreen.add(newstate)
                menu.oldstate = newstate
                if menu.sprite is not None:
                    try:
                        menu.sprite.delete()
                    except (AttributeError, AssertionError):
                        pass
                if menu.visible:
                    image = (
                        menu.inactive_pattern.create_image(
                            menu.width,
                            menu.height))
                    menu.sprite = pyglet.sprite.Sprite(
                        image, menu.window_left, menu.window_bot,
                        batch=self.batch, group=self.calgroup)

            # draw the calendar
            newstate = self.calendar.get_state_tup()
            if newstate not in self.onscreen:
                self.onscreen.add(newstate)
                self.onscreen.discard(self.calendar.oldstate)
                self.calendar.oldstate = newstate
                for calcol in self.calcols:
                    if calcol.sprite is not None:
                        try:
                            calcol.sprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if calcol.visible:
                        if calcol.width != calcol.old_width:
                            calcol.old_image = (
                                calcol.inactive_pattern.create_image(
                                    calcol.width, calcol.height))
                            calcol.old_width = calcol.width
                        image = calcol.old_image
                        calcol.sprite = pyglet.sprite.Sprite(
                            image,
                            calcol.window_left,
                            calcol.window_bot,
                            batch=self.batch,
                            group=self.calgroup)
                    for cel in calcol.celldict.itervalues():
                        if cel.sprite is not None:
                            try:
                                cel.sprite.delete()
                            except (AttributeError, AssertionError):
                                pass
                        if cel.visible:
                            if self.hovered == cel:
                                color = cel.style.fg_active.tup
                                if (
                                        cel.old_active_image is None or
                                        cel.old_width != cel.width or
                                        cel.old_height != cel.height):
                                    cel.old_active_image = (
                                        cel.active_pattern.create_image(
                                            cel.width, cel.height).texture)
                                    cel.old_width = cel.width
                                    cel.old_height = cel.height
                                image = cel.old_active_image
                            else:
                                color = cel.style.fg_inactive.tup
                                if (
                                        cel.old_inactive_image is None or
                                        cel.old_width != cel.width or
                                        cel.old_height != cel.height):
                                    cel.old_inactive_image = (
                                        cel.inactive_pattern.create_image(
                                            cel.width, cel.height).texture)
                                    cel.old_width = cel.width
                                    cel.old_height = cel.height
                                image = cel.old_inactive_image
                            cel.sprite = pyglet.sprite.Sprite(
                                image,
                                cel.window_left,
                                cel.window_bot,
                                batch=self.batch,
                                group=self.celgroup)
                            y = cel.window_top - cel.label_height
                            if cel.label is None:
                                cel.label = pyglet.text.Label(
                                    cel.text,
                                    cel.style.fontface,
                                    cel.style.fontsize,
                                    width=cel.width,
                                    height=cel.height,
                                    x=cel.window_left,
                                    y=y,
                                    multiline=True,
                                    batch=self.batch,
                                    group=self.labelgroup)
                            else:
                                cel.label.x = cel.window_left
                                cel.label.y = y
            if self.last_age != self.gamestate.age:
                # draw the time line on top of the calendar
                if (
                        self.timeline is not None and
                        self.timeline.domain.allocator.starts):
                    try:
                        self.timeline.delete()
                    except (AttributeError, AssertionError):
                        pass
                top = self.calendar.window_top
                left = self.calendar.window_left
                right = self.calendar.window_right
                starting = self.calendar.scrolled_to
                age = self.gamestate.age
                age_from_starting = age - starting
                age_offset = age_from_starting * self.calendar.row_height
                y = top - age_offset
                color = (255, 0, 0)
                if (
                        self.calendar.visible and
                        y > self.calendar.window_bot):
                    self.timeline = self.batch.add(
                        2, pyglet.graphics.GL_LINES, self.topgroup,
                        ('v2i', (left, y, right, y)),
                        ('c3B', color * 2))
                self.last_age = self.gamestate.age
                self.last_timeline_y = y
            # draw any and all hands
            for hand in self.board.hands:
                # No state management yet because the hand itself has
                # no graphics. The cards in it do.
                for card in hand:
                    ctxth = card.textholder
                    redrawn = (card.bgimage is None or
                               ctxth.bgimage is None or
                               card.bgimage.width != card.width or
                               card.bgimage.height != card.height)
                    if redrawn:
                        card.bgimage = (
                            card.pats.bg_inactive.create_image(
                                card.width, card.height))
                        ctxth.bgimage = (
                            card.pats.bg_active.create_image(
                                ctxth.width,
                                ctxth.height))
                        try:
                            card.bgsprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                        try:
                            ctxth.bgsprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                        card.bgsprite = None
                        ctxth.bgsprite = None
                    if card.visible:
                        if card.bgsprite is None:
                            card.bgsprite = pyglet.sprite.Sprite(
                                card.bgimage,
                                card.window_left,
                                card.window_bot,
                                batch=self.batch,
                                group=self.calgroup)
                        else:
                            if card.bgsprite.x != card.window_left:
                                card.bgsprite.x = card.window_left
                            if card.bgsprite.y != card.window_bot:
                                card.bgsprite.y = card.window_bot
                            if redrawn:
                                card.bgsprite.image = card.bgimage
                        if ctxth.bgsprite is None:
                            ctxth.bgsprite = pyglet.sprite.Sprite(
                                ctxth.bgimage,
                                ctxth.window_left,
                                ctxth.window_bot,
                                batch=self.batch,
                                group=self.celgroup)
                        else:
                            if ctxth.bgsprite.x != ctxth.window_left:
                                ctxth.bgsprite.x = ctxth.window_left
                            if ctxth.bgsprite.y != ctxth.window_bot:
                                ctxth.bgsprite.y = ctxth.window_bot
                            if redrawn:
                                ctxth.bgsprite.image = ctxth.bgimage
                        if ctxth.label is None:
                            ctxth.label = pyglet.text.Label(
                                card.text,
                                ctxth.style.fontface,
                                ctxth.style.fontsize,
                                anchor_y='bottom',
                                x=ctxth.text_left,
                                y=ctxth.text_bot,
                                width=ctxth.text_width,
                                height=ctxth.text_height,
                                multiline=True,
                                batch=self.batch,
                                group=self.labelgroup)
                        else:
                            if (
                                    ctxth.label.x !=
                                    ctxth.text_left):
                                ctxth.label.x = (
                                    ctxth.text_left)
                            if (
                                    ctxth.label.y !=
                                    ctxth.text_bot):
                                ctxth.label.y = (
                                    ctxth.text_bot)
                            if (
                                    ctxth.label.width !=
                                    ctxth.text_width):
                                ctxth.label.width = (
                                    ctxth.text_width)
                            if (
                                    ctxth.label.height !=
                                    ctxth.text_height):
                                ctxth.label.height = (
                                    ctxth.text_height)
                        if isinstance(card.img, pyglet.image.AbstractImage):
                            x = card.window_left + card.style.spacing
                            y = ctxth.window_top + card.style.spacing
                            if card.imgsprite is None:
                                card.imgsprite = pyglet.sprite.Sprite(
                                    card.img,
                                    x, y,
                                    batch=self.batch,
                                    group=self.celgroup)
                            else:
                                if card.imgsprite.x != x:
                                    card.imgsprite.x = x
                                if card.imgsprite.y != y:
                                    card.imgsprite.y = y
                    else:  # card not visible
                        for dead in (
                                card.bgsprite,
                                card.imgsprite,
                                ctxth.bgsprite,
                                ctxth.label):
                            if dead is not None:
                                try:
                                    dead.delete()
                                except:
                                    pass
                        card.bgsprite = None
                        card.imgsprite = None
                        ctxth.bgsprite = None
                        ctxth.label = None
            # draw the background image
            if self.drawn_board is None:
                self.drawn_board = pyglet.sprite.Sprite(
                    self.board.wallpaper.tex,
                    self.board.offset_x,
                    self.board.offset_y,
                    batch=self.batch, group=self.boardgroup)
            else:
                if self.drawn_board.x != self.board.offset_x:
                    self.drawn_board.x = self.board.offset_x
                if self.drawn_board.y != self.board.offset_y:
                    self.drawn_board.y = self.board.offset_y
            # well, I lied. I was really only adding those things to the batch.
            # NOW I'll draw them.
            self.batch.draw()
            self.resized = False

        @window.event
        def on_mouse_motion(x, y, dx, dy):
            """Find the widget, if any, that the mouse is over, and highlight
it."""
            self.last_mouse_x = x
            self.last_mouse_y = y
            del self.dx_hist[0]
            del self.dy_hist[0]
            self.dx_hist.append(dx)
            self.dy_hist.append(dy)
            if self.hovered is None:
                for hand in self.board.hands:
                    if (
                            hand.visible and
                            hand.interactive and
                            x > hand.window_left and
                            x < hand.window_right and
                            y > hand.window_bot and
                            y < hand.window_top):
                        for card in hand:
                            if (
                                    x > card.window_left and
                                    x < card.window_right):
                                self.hovered = card
                                card.tweaks += 1
                                return
                for menu in self.board.menus:
                    if (
                            menu.visible and
                            menu.interactive and
                            x > menu.window_left and
                            x < menu.window_right and
                            y > menu.window_bot and
                            y < menu.window_top):
                        for item in menu.items:
                            if (
                                    y > item.window_bot and
                                    y < item.window_top):
                                self.hovered = item
                                item.tweaks += 1
                                return

        @window.event
        def on_mouse_press(x, y, button, modifiers):
            """If there's something already highlit, and the mouse is
still over it when pressed, it's been half-way clicked; remember this."""
            if self.placing or self.thinging:
                return
            elif self.hovered is None:
                for pawn in self.board.pawns:
                    if (
                            pawn.visible and
                            pawn.interactive and
                            x > pawn.window_left and
                            x < pawn.window_right and
                            y > pawn.window_bot and
                            y < pawn.window_top):
                        self.pressed = pawn
                        self.pressed.tweaks += 1
                        return
                for spot in self.board.spots:
                    if (
                            spot.visible and
                            spot.interactive and
                            x > spot.window_left and
                            x < spot.window_right and
                            y > spot.window_bot and
                            y < spot.window_top):
                        self.pressed = spot
                        self.pressed.tweaks += 1
                        return
                for edge in self.board.edges:
                    if edge.touching(x, y):
                        if self.pressed is None or edge.order > self.pressed.order:
                            self.pressed = edge
            else:
                self.pressed = self.hovered

        @window.event
        def on_mouse_release(x, y, button, modifiers):
            """If something was being dragged, drop it. If something was being
pressed but not dragged, it's been clicked. Otherwise do nothing."""
            if self.placing:
                placed = self.db.make_generic_place(str(self.board))
                self.db.make_spot(
                    str(self.board), str(placed),
                    x + self.board.offset_x,
                    y + self.board.offset_y)
                self.window.set_mouse_cursor()
                self.placing = False
            elif self.thinging:
                thung = self.db.make_generic_thing(str(self.board))
                self.db.make_pawn(str(self.board), str(thung))
                self.thinging = False
            elif self.portaling:
                if self.portal_from is None:
                    if hasattr(self.pressed, 'place'):
                        self.portal_from = self.pressed
                        logger.debug(
                            "Making a portal from %s...",
                            str(self.portal_from.place))
                    else:
                        self.portaling = False
                        self.portal_from = None
                        for line in self.portal_triple:
                            if line is not None:
                                for edge in line:
                                    try:
                                        edge.delete()
                                    except:
                                        pass
                        self.portal_triple = ((None, None), (None, None), (None, None))

                else:
                    if (
                            hasattr(self.pressed, 'place') and
                            hasattr(self.portal_from, 'place') and
                            self.pressed.place != self.portal_from.place):
                        logger.debug("...to %s", str(self.pressed.place))
                        port = self.db.make_portal(
                            str(self.board),
                            str(self.portal_from.place),
                            str(self.pressed.place))
                        Edge(self, port)
                    self.portaling = False
                    self.portal_from = None
                    self.pressed = None
                    for line in self.portal_triple:
                        for edge in line:
                            try:
                                edge.delete()
                            except:
                                pass
                    self.portal_triple = ((None,None),(None,None),(None,None))
            elif self.grabbed is None:
                pass
            else:
                if hasattr(self.grabbed, 'dropped'):
                    self.grabbed.dropped(x, y, button, modifiers)
            self.grabbed = None
            if not self.keep_selected:
                self.selected = set()
            if self.pressed is not None:
                if (
                        x > self.pressed.window_left and
                        x < self.pressed.window_right and
                        y > self.pressed.window_bot and
                        y < self.pressed.window_top):
                    if hasattr(self.pressed, 'onclick'):
                        self.pressed.onclick()
                    if hasattr(self.pressed, 'selectable'):
                        self.edge_order += 1
                        self.pressed.order = self.edge_order
                        self.selected.add(self.pressed)
                        if hasattr(self.pressed, 'reciprocate'):
                            self.selected.add(self.pressed.reciprocate())
                self.pressed = None

        @window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            """If the thing previously pressed has a
move_with_mouse method, use it.

            """
            if self.grabbed is None:
                if (
                        self.pressed is not None and
                        x > self.pressed.window_left and
                        x < self.pressed.window_right and
                        y > self.pressed.window_bot and
                        y < self.pressed.window_top and
                        hasattr(self.pressed, 'move_with_mouse')):
                    self.grabbed = self.pressed
                else:
                    self.board.view_left -= dx
                    if (
                            self.board.view_left +
                            self.window.width >
                            self.board.img.width):
                        self.board.view_left = (
                            self.board.img.width -
                            self.window.width)
                    elif self.board.view_left < 0:
                        self.board.view_left = 0
                    self.board.view_bot -= dy
                    if (
                            self.board.view_bot +
                            self.window.height >
                            self.board.img.height):
                        self.board.view_bot = (
                            self.board.img.height -
                            self.window.height)
                    elif self.board.view_bot < 0:
                        self.board.view_bot = 0
                    if self.pressed is not None:
                        self.pressed = None
                    self.grabbed = None
            else:
                self.grabbed.move_with_mouse(x, y, dx, dy, buttons, modifiers)

        @window.event
        def on_resize(w, h):
            """Inform the on_draw function that the window's been resized."""
            self.resized = True

        @window.event
        def on_mouse_scroll(x, y, scroll_x, scroll_y):
            # for now, this only does anything if you're moused over
            # the calendar
            if (
                    self.calendar.visible and
                    x > self.calendar.window_left and
                    x < self.calendar.window_right and
                    y > self.calendar.window_bot and
                    y < self.calendar.window_top):
                sf = self.calendar.scroll_factor
                self.calendar.scrolled_to += scroll_y * sf

    def __getattr__(self, attrn):
        if attrn == 'width':
            return self.window.width
        elif attrn == 'height':
            return self.window.height
        elif attrn == 'dx':
            return sum(self.dx_hist)
        elif attrn == 'dy':
            return sum(self.dy_hist)
        else:
            raise AttributeError(
                "GameWindow has no attribute named {0}".format(attrn))

    def create_place(self):
        self.window.set_mouse_cursor(self.create_place_cursor)
        self.placing = True

    def create_thing(self):
        self.thinging = True

    def create_portal(self):
        if not hasattr(self, 'portaled'):
            self.portaled = 0
        self.portaled += 1
        self.portaling = True

    def connect_arrow(self, ox, oy, dx, dy,
                      order,
                      old_triple=((None,None),(None,None),(None,None)),
                      center_shrink=0,
                      highlight=False):
        supergroup = pyglet.graphics.OrderedGroup(order, self.edgegroup)
        bggroup = SmoothBoldLineOrderedGroup(
                0, supergroup, self.arrow_girth)
        fggroup = BoldLineOrderedGroup(
                1, supergroup, self.arrow_width)
        # xs and ys should be integers.
        #
        # results will be called l, c, r for left tail, center, right tail
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
            float(dx * xco), float(dy * yco), center_shrink+1)
        taillen = float(self.arrowhead_size)
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
        x1 = int(rightx - xoff1) * xco
        x2 = int(rightx - xoff2) * xco
        y1 = int(topy - yoff1) * yco
        y2 = int(topy - yoff2) * yco
        endx = int(rightx) * xco
        endy = int(topy) * yco
        if highlight:
            bgcolor = (255, 255, 0, 0)
            fgcolor = (0, 0, 0, 0)
        else:
            bgcolor = (64, 64, 64, 64)
            fgcolor = (255,255,255,0)
        lpoints = (x1, y1, endx, endy)
        cpoints = (ox, oy, endx, endy)
        rpoints = (x2, y2, endx, endy)
        lbg = self.draw_line(
            lpoints, bgcolor, bggroup, old_triple[0][0])
        cbg = self.draw_line(
            cpoints, bgcolor, bggroup, old_triple[1][0])
        rbg = self.draw_line(
            rpoints, bgcolor, bggroup, old_triple[2][0])
        lfg = self.draw_line(
            lpoints, fgcolor, fggroup, old_triple[0][1])
        rfg = self.draw_line(
            rpoints, fgcolor, fggroup, old_triple[2][1])
        cfg = self.draw_line(
            cpoints, fgcolor, fggroup, old_triple[1][1])
        return ((lbg,lfg), (cbg,cfg), (rbg,rfg))

    def draw_line(self, points, color, group, verts=None):
        colors = color * 2
        if verts is None:
            verts = self.batch.add(
                2,
                pyglet.gl.GL_LINES,
                group,
                ('v2i', tuple(points)),
                ('c4B', tuple(colors)))
        else:
            verts.vertices = list(points)
            verts.colors = list(colors)
        return verts
