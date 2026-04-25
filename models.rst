.. Redisco documentation contianers file, created by
   sphinx-quickstart on Fri Sep  7 15:58:04 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Object Relation Manager
===================================

Redisco allows you to store objects in Redis_. Redisco can easily manage object creation, update and deletion. It is strongly Ohm_ and Django_ ORM and try to provide a simple approach.

.. _Redis: http://redis.io
.. _Ohm: http://ohm.keyvalue.org
.. _Django: http://djangoproject.org

::

    >>> from redisco import models
    >>> class Person(models.Model):
    ...    name = models.Attribute(required=True)
    ...    created_at = models.DateTimeField(auto_now_add=True)
    ...    fave_colors = models.ListField(str)

    >>> person = Person(name="Conchita")
    >>> person.is_valid()
    True
    >>> person.save()
    True
    >>> conchita = Person.objects.filter(name='Conchita')[0]
    >>> conchita.name
    'Conchita'
    >>> conchita.created_at
    datetime.datetime(2010, 5, 24, 16, 0, 31, 954704)



Model
-----------------------------------
The ``Model`` class is the class that will contain your object. It upports many different type of attributes and support custom object validation to ensure data integrity when saving.

.. autoclass:: redisco.models.Model
   :members:


Attributes
----------------------------------
The attributes are the core of any redisco ``Model``. Many different attributes are available according to your needs. Read the following documentation to understand the caveats of each attribute.


Attribute
    Stores unicode strings. If used for large bodies of text,
    turn indexing of this field off by setting indexed=True.

IntegerField
    Stores an int. Ints are stringified using unicode() before saving to
    Redis.

Counter
    An IntegerField that can only be accessed via Model.incr and Model.decr.

DateTimeField
    Can store a DateTime object. Saved in the Redis store as a float.

DateField
    Can store a Date object. Saved in Redis as a float.

TimeDeltaField
    Can store a TimeDelta object. Saved in Redis as a float.

FloatField
    Can store floats.

BooleanField
    Can store bools. Saved in Redis as 1's and 0's.

ReferenceField
    Can reference other redisco model.

ListField
    Can store a list of unicode, int, float, as well as other redisco models.


Attribute Options
-----------------

required
    If True, the attirbute cannot be None or empty. Strings are stripped to
    check if they are empty. Default is False.

default
    Sets the default value of the attribute. Default is None.

indexed
    If True, redisco will create index entries for the attribute. Indexes
    are used in filtering and ordering results of queries. For large bodies
    of strings, this should be set to False. Default is True.

validator
    Set this to a callable that accepts two arguments -- the field name and
    the value of the attribute. The callable should return a list of tuples
    with the first item is the field name, and the second item is the error.

unique
    The field must be unique. Default is False.

DateField and DateTimeField Options

auto_now_add
    Automatically set the datetime/date field to now/today when the object
    is first created. Default is False.

auto_now
    Automatically set the datetime/date field to now/today everytime the object
    is saved. Default is False.

Modelset
-----------------------------------
The ``ModelSet`` class is useful for all kind of queries when you want to filter data (like in SQL). You can filter objects by values in their attributes, creation dates and even perform some unions and exclusions.


    >>> from redisco import models
    >>> class Person(models.Model):
    ...    name = models.Attribute(required=True)
    ...    created_at = models.DateTimeField(auto_now_add=True)
    ...    fave_colors = models.ListField(str)

    >>> person = Person(name="Conchita")
    >>> person.save()
    True
    >>> conchita = Person.objects.filter(name='Conchita').first()

.. autoclass:: redisco.models.modelset.ModelSet
   :members: get_by_id, filter, first, exclude, all, get_or_create, order, limit

