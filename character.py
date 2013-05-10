from util import SaveableMetaclass


"""Things that should have character sheets."""


__metaclass__ = SaveableMetaclass


class Character:
    """An incorporeal object connecting corporeal ones together across
dimensions, indicating that they represent one thing and have that
thing's attributes.

Every item in LiSE's world model must be part of a Character, though
it may be the only member of that Character. Where items can only have
generic attributes appropriate to the dimension they occupy,
Characters have all the attributes of the items that make them up, and
possibly many more. There are no particular restrictions on what
manner of attribute a Character can have, so long as it is not used by
the physics of any dimension.

Characters may contain EventDecks. These may represent skills the
character has, in which case every EventCard in the EventDeck
represents something can happen upon using the skill, regardless of
what it's used on or where. "Success" and "failure" are appropriate
EventCards in this case, though there may be finer distinctions to be
made between various kinds of success and failure with a given skill.

However, the EventCards that go in a Character's EventDeck to
represent a skill should never represent anything particular to any
use-case of the skill. Those EventCards should instead be in the
EventDeck of those other Characters--perhaps people, perhaps places,
perhaps tools--that the skill may be used on, with, or for. All of
those Characters' relevant EventDecks will be used in constructing a
new one, called the OutcomeDeck, and the outcome of the event will be
drawn from that.

Otherwise, Characters can be treated much like three-dimensional
dictionaries, wherein you may look up the Character's attributes. The
key is composed of the dimension an item of this character is in, the
item's name, and the name of the attribute.

"""
    tables = [
        ("character_item_link",
         {"character": "text",
          "dimension": "text",
          "item": "text"},
         ("character", "dimension", "item"),
         {"dimension, item": ("item", "dimension, name")},
         []),
        ("character_skill_link",
         {"character": "text",
          "skill": "text",
          "effect_deck": "text"},
         ("character", "skill"),
         {"effect_deck": ("effect_deck", "name")},
         []),
        ("attribution",
         {"character": "text",
          "attribute": "text",
          "value": "text"},
         ("character", "attribute"),
         [],
         [])]

    def __init__(self, name, db=None):
        self.name = name
        self.character_item_link = set()
        self.character_skill_link = set()
        self.attribution = set()
        if db is not None:
            db.characterdict[self.name] = self

    def unravel(self, db):
        # Assumes that everything it relies on has been pre-unraveled
        self.itemdict = db.characteritemdict[self.name]
        self.skilldict = db.skilldict[self.name]
        self.attributiondict = db.attributiondict[self.name]
        for item in self.itemdict.iteritems():
            (dimname, it) = item
            self.character_item_link.add((self.name, dimname, it.name))
        for item in self.skilldict.iteritems():
            (skill, ed) = item
            self.character_skill_link.add((self.name, skill, ed.name))
        for item in self.attributiondict.iteritems():
            (trib, val) = item
            self.attribution.add((self.name, trib, val))
