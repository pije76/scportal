************
Introduction
************


This is the GridManager ApS final documentation of the GridPlatform. It was
compiled in the last months before the final termination of the
GridManager ApS Research & Development department.


Disclaimer
==========
This documentation is intended as a minimalistic form of *hand over*
documentation to help future developers understand the code and the thoughts
behind it. The documentation here is basically all we had time to compile
before our time with GridManager ApS was up.


Target audience
===============
The readers of this document are expected to be experienced software developers,
comfortable with the following technologies:

- Python programming language
- Django web framework
- Celery (used for background tasks for Django)
- HTML and JavaScript
- RESTful web services
- Django REST Framework

Preferably the reader is also experienced within the field of energy
management, and thus know the terminology used within that field.


What is documented and what is not
==================================
There are four software components that were developed by GridManager ApS. They are:
GridPlatform, GridAgent Server, GridPortal 2.0, and Energy Manager.

Only GridAgent Server and GridPlatform are documented in detail here. The
GridPortal 2.0 is legacy and no documentation exists apart from what is found
as code comments in the code itself. However, if a developer with the right
technical skill set reads this documentation then he/she should also be able to
understand the GridPortal 2.0 design and code simply by inspecting it, as both
are software systems for use in the energy management domain.
