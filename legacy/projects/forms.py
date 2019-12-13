# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.db.models import F

from .models import BenchmarkProject


class AnnualSavingsPotentialReportGenerationForm(forms.Form):
    projects = forms.ModelMultipleChoiceField(
        BenchmarkProject.objects.none())

    def __init__(self, *args, **kwargs):
        super(AnnualSavingsPotentialReportGenerationForm, self).__init__(
            *args, **kwargs)
        self.fields['projects'].queryset = BenchmarkProject.objects.all()
