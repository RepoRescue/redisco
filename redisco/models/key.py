try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

class Key(unicode):
    def __getitem__(self, key):
        return Key(u"%s:%s" % (self, key))
