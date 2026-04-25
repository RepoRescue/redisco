.. Redisco documentation contianers file, created by
   sphinx-quickstart on Fri Sep  7 15:58:04 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Containers
===================================

A suite of containers is available to the developer (you!) in order to manipulate some of redis' objects. You can easily create, modify, update, and delete Sets, SortedSets, Lists and Hashes. Pay attention that mnay of the operations are serialized to the redis server and are therefore time consuming.


Base Class
-----------------------------------
.. autoclass:: redisco.containers.Container
   :members:

Set
-----------------------------------
.. autoclass:: redisco.containers.Set
   :members:

SortedSet
-----------------------------------
.. autoclass:: redisco.containers.SortedSet
   :members:

List
-----------------------------------
.. autoclass:: redisco.containers.List
   :members:

Hash
-----------------------------------
.. autoclass:: redisco.containers.Hash
   :members:

