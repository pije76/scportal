============
Known issues
============


GridPortal 2.0 Super user can break measurement point groups
============================================================

Customer *superusers* that are bound to groups and create new *root* groups or
move existing groups to be *root* groups may lead to the absolute order of
*root* groups for the customer to **not** be well-defined. The reason for this is
that the order saved will be constructed taking only those existing groups
that are *currently visible* into account.  This can lead to several groups
specifying the same position at which point the relative order among those is
unspecified and may vary when loaded/reloaded in different pages or at
different times.  Displaying the *children* of such conflicting groups may also
mix/associate them wrongly. The feature of restricting a user to a certain
group is inherently broken if that user is a super user.

To rebuild all the trees run `./manage.py rebuild_group_tree` or use the following Python statement:

::

    Collection.tree.rebuild()
