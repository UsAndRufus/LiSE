# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from container import Container


class Portal(Container):
    tables = [
        ("portal", {
            "columns": {
                "character": "text not null default 'Physical'",
                "name": "text not null",
                "host": "text not null default 'Physical'"},
            "primary_key": (
                "character", "name")}),
        ("portal_loc", {
            "columns": {
                "character": "text not null default 'Physical'",
                "name": "text not null",
                "branch": "integer not null default 0",
                "tick": "integer not null default 0",
                "origin": "text",
                "destination": "text"},
            "primary_key": (
                "character", "name", "branch", "tick"),
            "foreign_keys": {
                "character, name": (
                    "portal", "character, name")}}),
        ("portal_stat", {
            "columns": {
                "character": "text not null default 'Physical'",
                "name": "text not null",
                "key": "text not null",
                "branch": "integer not null default 0",
                "tick": "integer not null default 0",
                "value": "text"},
            "primary_key": (
                "character", "name", "key", "branch", "tick"),
            "foreign_keys": {
                "character, name": (
                    "portal", "character, name")}}),
        ("portal_loc_facade", {
            "columns": {
                "observer": "text not null",
                "observed": "text not null",
                "name": "text not null",
                "branch": "integer not null default 0",
                "tick": "integer not null default 0",
                "origin": "text",
                "destination": "text"},
            "primary_key": (
                "observer", "observed", "name", "branch", "tick"),
            "foreign_keys": {
                "observed, name": (
                    "portal", "character, name")}}),
        ("portal_stat_facade", {
            "columns": {
                "observer": "text not null",
                "observed": "text not null",
                "name": "text not null",
                "key": "text not null",
                "branch": "integer not null default 0",
                "tick": "integer not null default 0",
                "value": "text"},
            "primary_key": (
                "observer", "observed", "name",
                "key", "branch", "tick"),
            "foreign_keys": {
                "observed, name": (
                    "portal", "character, name")}})]

    def __init__(self, character, name):
        self.character = character
        self.name = name

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return unicode(self.name)

    def __repr__(self):
        bone = self.bone
        return "{2}({0}->{1})".format(
            bone.origin, bone.destination, self.name)

    def get_bone(self, observer=None, branch=None, tick=None):
        if observer is None:
            return self.character.get_portal_bone(self.name, branch, tick)
        else:
            facade = self.character.get_facade(observer)
            return facade.get_portal_bone(self.name, branch, tick)
