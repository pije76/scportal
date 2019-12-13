===========
Future Work
===========

In this chapter we list a few things we had planned to do in the near future
that we feel might be of use to future developers.


Upgrade Python and Django
=========================

We had planned to upgrade to Python 3 and the newest version of Django as soon
as possible. Both upgrades should be fairly straight forward. The Python 3 upgrade
might require a significant amount work if some of the libraries currently used
still are unavailable in versions working with Python 3 but for the most part
the code has been prepared for Python 3.


Refactor user model according to present Django convensions
===========================================================

The user model was naturally one of the first models implemented and back then
Django was at version 1.5. A lot has changed since then, especially regarding
to how custom user models are integrated, and therefore it would be wise to
refactor the model to follow current Django user model guidelines.


Get rid of :attr:`User.user_type`
===========================================================

The :attr:`gridplatform.users.models.User.user_type` attribute is legacy, and
is still used in GridPortal 2.0 by access control logic. However, the same
access control can easily be achieved using permissions.


Refactor the :attr:`Sample` class.
==================================

The :class:`gridplatform.utils.samples.Sample` class already should be refactored into
two separate classes, namely :class:`PointSample` and :class:`RangedSample`. See
:file:`gridplatform/utils/samples.py` code comments for further details.


Re-specification and refactoring of the *Provider* concept
==========================================================

When the provider concept was originally created only provider users needed
access to provider information. However, later it made sense that customers
users for a specific provider can see the provider information as well.

Whoever continues the work on this code should stress the necessity of getting
provider concept properly specified and then refactor accordingly.
