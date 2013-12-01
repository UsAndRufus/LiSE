from os import sep

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import (
    ObjectProperty,
    ListProperty,
    StringProperty)
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.scatter import Scatter
from kivy.uix.textinput import TextInput

from LiSE.gui.board import Pawn
from LiSE.util import Skeleton
from LiSE.closet import load_closet


class CueCard(TextInput):
    """Widget that looks like TextInput but doesn't take input and can't be
clicked.

This is used to display feedback to the user when it's not serious
enough to get a popup of its own.

    """
    def on_touch_down(self, touch):
        return

    def on_touch_move(self, touch):
        return

    def on_touch_up(self, touch):
        return

    def collide_point(self, x, y):
        return

    def collide_widget(self, w):
        return


class DummyPawn(Scatter):
    """Looks like a Pawn, but doesn't have a Thing associated.

This is meant to be used when the user is presently engaged with
deciding where a Thing should be, when the Thing in question doesn't
exist yet, but you know what it should look like."""
    imgnames = ListProperty()
    board = ObjectProperty()
    callback = ObjectProperty()

    def __init__(self, **kwargs):
        """Fill myself with Images taken from self.textures"""
        super(DummyPawn, self).__init__(**kwargs)

        sized = False
        for imgn in self.imgnames:
            tex = self.board.closet.get_texture(imgn)
            if not sized:
                self.size = tex.size
                sized = True
            self.add_widget(Image(texture=tex, size=self.size))

    def on_touch_up(self, touch):
        """Create a real Pawn on top of the Spot that's been clicked, along
with a Thing for it to represent. Then disappear."""
        for spot in self.board.spotdict.itervalues():
            if self.collide_widget(spot):
                dimn = unicode(spot.board)
                placen = unicode(spot.place)
                th = self.board.closet.make_generic_thing(
                    dimn, placen)
                thingn = unicode(th)
                branch = spot.board.closet.branch
                tick = spot.board.closet.tick
                skel = spot.board.closet.skeleton[u"pawn_img"]
                if dimn not in skel:
                    skel[dimn] = Skeleton()
                skel[dimn][thingn] = Skeleton()
                for layer in xrange(0, len(self.imgnames)):
                    skel[dimn][thingn][layer] = Skeleton()
                    ptr = skel[dimn][thingn][layer][branch] = Skeleton()
                    ptr[tick] = Pawn.bonetypes.pawn_img(
                        dimension=dimn,
                        thing=thingn,
                        layer=layer,
                        branch=branch,
                        tick=tick,
                        img=self.imgnames[layer])
                pawn = Pawn(board=self.board, thing=th)
                pawn.set_interactive()
                self.board.pawndict[thingn] = pawn
                self.board.add_widget(pawn)
                self.clear_widgets()
                self.callback()
                return True


class LiSELayout(FloatLayout):
    """A very tiny master layout that contains one board and some menus
and charsheets.

    """
    menus = ListProperty()
    charsheets = ListProperty()
    board = ObjectProperty()
    prompt = ObjectProperty()

    def __init__(self, **kwargs):
        """Add board first, then menus and charsheets."""
        super(LiSELayout, self).__init__(**kwargs)
        self._popups = []
        self.add_widget(self.board)
        for menu in self.menus:
            self.add_widget(menu)
        for charsheet in self.charsheets:
            self.add_widget(charsheet)
        self.add_widget(self.prompt)

    def display_prompt(self, text):
        """Put the text in the cue card"""
        self.prompt.text = text

    def dismiss_prompt(self):
        """Blank out the cue card"""
        self.prompt.text = ''

    def dismiss_popup(self):
        """Destroy the latest popup"""
        self._popups.pop().dismiss()

    def new_spot_with_swatch(self, swatch):
        """Given a Swatch widget, make a Spot with the graphic therein, and
dismiss the popup."""
        pass

    def new_pawn_with_swatches(self, swatches):
        """Given some iterable of Swatch widgets, make a dummy pawn, prompt
the user to place it, and dismiss the popup."""
        self.display_prompt(self.board.closet.get_text("@putthing"))
        self.add_widget(DummyPawn(
            board=self.board,
            imgnames=[swatch.text for swatch in swatches],
            callback=self.dismiss_prompt,
            pos=(self.width * 0.1, self.height * 0.9)))
        self.dismiss_popup()

    def show_spot_picker(self, texdict):
        pass

    def show_pawn_picker(self, texdict):
        """Show a SwatchBox for the given texdict. The chosen Swatches will be
used to build a Pawn later."""
        dialog = PickImgDialog(
            set_imgs=self.new_pawn_with_swatches,
            cancel=self.dismiss_popup,
            texdict=texdict)
        self._popups.append(Popup(
            title="Select some images",
            content=dialog,
            size_hint=(0.9, 0.9)))
        self._popups[-1].open()


class LoadImgDialog(FloatLayout):
    """Dialog for adding img files to the database."""
    load = ObjectProperty()
    cancel = ObjectProperty()


class PickImgDialog(FloatLayout):
    """Dialog for associating imgs with something, perhaps a Pawn.

In lise.kv this is given a SwatchBox with texdict=root.texdict."""
    texdict = ObjectProperty()
    set_imgs = ObjectProperty()
    cancel = ObjectProperty()


class LiSEApp(App):
    closet = ObjectProperty(None)
    dbfn = StringProperty(allownone=True)
    lang = StringProperty()
    lise_path = StringProperty()
    menu_name = StringProperty()
    dimension_name = StringProperty()
    character_name = StringProperty()

    def build(self):
        if self.dbfn is None:
            self.dbfn = self.user_data_dir + sep + "default.lise"
        self.closet = load_closet(self.dbfn, self.lise_path, self.lang, True)
        self.closet.uptick_skel()
        self.updater = Clock.schedule_interval(self.closet.update, 0.1)
        menu = self.closet.load_menu(self.menu_name)
        board = self.closet.load_board(self.dimension_name)
        charsheet = self.closet.load_charsheet(self.character_name)
        prompt = CueCard()
        return LiSELayout(
            menus=[menu],
            board=board,
            charsheets=[charsheet],
            prompt=prompt)
