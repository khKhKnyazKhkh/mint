# -*- coding: utf-8 -*-

'''
Template Engine based on indention and python syntax.
'''

import weakref
import logging
from os import path
from StringIO import StringIO

from parser import Parser, TemplateError

logger = logging.getLogger(__name__)


class TemplateNotFound(Exception):
    pass


class Template(object):

    def __init__(self, sourcefile, cache=True, loader=None):
        self.sourcefile = sourcefile
        self.need_caching = cache
        # ast
        self._tree = None
        self.compiled_code = None
        self._loader = weakref.proxy(loader) if loader else None

    @property
    def tree(self):
        if self._tree is None:
            tree = self.parse()
            if self.need_caching:
                self._tree = tree
            return tree
        else:
            return self._tree

    def parse(self, slots=None):
        parser = Parser(indent=4, slots=slots)
        parser.parse(self.sourcefile)
        tree = parser.tree
        # templates inheritance
        if parser.base is not None:
            base_template = self._loader.get_template(parser.base)
            # one base template may have multiple childs, so
            # every time we need to get base template tree again
            tree = base_template.parse(slots=parser.slots)
        return tree

    def compile(self):
        compiled_souces = compile(self.tree, self.sourcefile.name, 'exec')
        if self.need_caching:
            self.compiled_code = compiled_souces
        return compiled_souces

    def render(self, **kwargs):
        if self.compiled_code is None:
            code = self.compile()
        else:
            code = self.compiled_code
        ns = Parser.NAMESPACE.copy()
        ns.update(kwargs)
        exec code in ns
        return ns[Parser.OUTPUT_NAME].getvalue()


class Loader(object):

    def __init__(self, *dirs, **kwargs):
        cache = kwargs.get('cache', False)
        self.dirs = []
        for dir in dirs:
            self.dirs.append(path.abspath(dir))
        self.need_caching = cache
        self._templates_cache = {}

    def get_template(self, template):
        if template in self._templates_cache:
            return self._templates_cache[template]
        for dir in self.dirs:
            location = path.join(dir, template)
            if path.exists(location) and path.isfile(location):
                tmpl = Template(open(location, 'r'), cache=self.need_caching,
                                loader=self)
                self._templates_cache[template] = tmpl
                return tmpl
        raise TemplateNotFound(template)

    def __add__(self, other):
        self.dirs = self.dirs + other.dirs
        return self