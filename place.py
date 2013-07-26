class Place:
    """Where you go when you have to be someplace.

Places have no database records of their own. They are considered to
exist so long as there's a portal from there, a portal to there, or a
thing located there.

    """
    def __init__(self, dimension, name):
        self.name = name
        self.dimension = dimension
        self.db = self.dimension.db
        self.contents = set()

    def __contains__(self, that):
        return that.location == self

    def __int__(self):
        return self.i  # assigned by dimension.

    def __str__(self):
        return self.name

    def update_contents(self):
        for thing in self.dimension.things:
            if thing.location == self:
                self.contents.add(thing)
            else:
                self.contents.discard(thing)
