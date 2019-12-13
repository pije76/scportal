# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


class SurvivingFormsModelFormSetMixin(object):
    """
    Mixes :meth:`~.SurvivingFormsModelFormSetMixin.surviving_forms`
    into a formset.
    """

    def surviving_forms(self):
        """
        Surviving forms are forms that Django will save to the database.

        Surviving forms may be subject to extra validation logic
        compared to nonsurviving forms (those that Django will either
        delete or ignore).
        """
        result = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if self._should_delete_form(form):
                continue
            if i >= self.initial_form_count():
                if form.has_changed():
                    result.append(form)
            else:
                result.append(form)
        return result
