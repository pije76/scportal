# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.forms import ModelForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import redirect
from django.forms.models import inlineformset_factory, modelform_factory
from django.db.models import BLANK_CHOICE_DASH
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods

from gridplatform.utils.views import (
    render_to,
    json_list_response,
)
from gridplatform.utils import units
from legacy.rules.models import (
    UserRule, MinimizeRule, TriggeredRule,
    DateException,
    RelayAction, EmailAction, PhoneAction, Action,
    IndexInvariant, InputInvariant,
)
from legacy.indexes.models import Index
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.users.decorators import (
    auth_or_error,
    customer_admin_or_error,
)
from gridplatform.trackuser import get_customer


@auth_or_error
@json_list_response
def rule_list_json(request):
    customer = request.customer
    rules = list(UserRule.objects.filter(customer=customer))

    order_map = {
        'name': lambda rule: rule.name_plain.lower(),
    }
    return (order_map, rules, 'manage_rules/rule_block.html')


class MinimizeRuleForm(forms.ModelForm):
    class Meta:
        model = MinimizeRule
        localized_fields = '__all__'
        fields = (
            'name', 'enabled', 'timezone', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday', 'from_time', 'to_time',
            'consecutive', 'activity_duration', 'index',
        )

    def clean_activity_duration(self):
        activity_duration = self.cleaned_data['activity_duration']
        # checks both length of duration and blank duration
        if not activity_duration:
            raise forms.ValidationError(_("Duration is required"))
        return activity_duration

TriggeredRuleForm = modelform_factory(
    TriggeredRule, localized_fields='__all__')


def base_rule_formsets(rule, meters_qs, data=None):

    class Meta:
        model = RelayAction
        exclude = ['execution_time']

    RelayActionForm = type(b'RelayActionForm', (ModelForm,), {
        'meter': forms.ModelChoiceField(
            queryset=meters_qs),
        'Meta': Meta,
    })

    class PhoneActionForm(forms.ModelForm):
        phone_number = forms.CharField(
            label=_('phone number'), min_length=10)

        class Meta:
            model = PhoneAction
            exclude = ('execution_time', )
            localized_fields = '__all__'

    DateExceptionFormset = inlineformset_factory(
        UserRule, DateException, extra=0)
    RelayActionFormSet = inlineformset_factory(
        UserRule, RelayAction, form=RelayActionForm, extra=0)
    EmailActionFormSet = inlineformset_factory(
        UserRule, EmailAction, exclude=['execution_time'], extra=0)
    PhoneActionFormSet = inlineformset_factory(
        UserRule, PhoneAction, form=PhoneActionForm, extra=0)
    result = {
        'dateexception': DateExceptionFormset(
            data, instance=rule, auto_id=False, prefix='dateexception'),
    }
    for name, cls in [('relay', RelayActionFormSet),
                      ('email', EmailActionFormSet),
                      ('phone', PhoneActionFormSet)]:
        result[name + '_initial'] = cls(
            data, instance=rule, auto_id=False, prefix=name + '-initial',
            queryset=cls.model.objects.filter(
                rule=rule, execution_time=Action.INITIAL))
        result[name + '_final'] = cls(
            data, instance=rule, auto_id=False, prefix=name + '-final',
            queryset=cls.model.objects.filter(
                rule=rule, execution_time=Action.FINAL))
    return result


@customer_admin_or_error
@render_to('manage_rules/minimizerule_form.html')
def minimizerule_form(request, pk=None):
    customer = request.customer
    if pk:
        rule = get_object_or_404(MinimizeRule, pk=pk)
        if rule.customer != customer:
            return HttpResponseForbidden()
    else:
        rule = None
    if request.method == 'POST':
        data = request.POST
    else:
        data = None

    form = MinimizeRuleForm(data, auto_id=False, instance=rule)
    qs = Index.objects.all().exclude(
        role__in=[DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
                  DataRoleField.CO2_QUOTIENT])
    form.fields['index'].queryset = qs

    if data and form.is_valid():
        rule = form.save(commit=False)
    meters_qs = customer.meter_set.filter(relay_enabled=True)
    formsets = base_rule_formsets(rule, meters_qs, data)
    if data and form.is_valid() and all([f.is_valid()
                                         for f in formsets.itervalues()]):
        rule = form.save(commit=False)
        rule.customer = request.customer
        rule.save()
        for name, formset in formsets.iteritems():
            instances = formset.save(commit=False)
            for instance in instances:
                if name.endswith('_initial'):
                    instance.execution_time = Action.INITIAL
                elif name.endswith('_final'):
                    instance.execution_time = Action.FINAL
                instance.save()
        if pk:
            messages.success(request, _('The rule has been saved'))
        else:
            messages.success(request, _('The rule has been created'))
        if 'save_return' in data:
            return redirect('manage_rules-list')
        if not pk:
            return redirect('manage_rules-minimizerule_form',
                            pk=rule.id)
        else:
            # reload formsets from DB, to get IDs, remove deleted...
            formsets = base_rule_formsets(rule, meters_qs)

    return {
        'form': form,
        'formsets': formsets,
    }


class IndexInvariantForm(ModelForm):
    """
    C{ModelForm} for L{IndexInvariant}s.

    This form is intended for use in inline formsets, so it is required to
    work-out-of-the-box without special initialization requirements.
    """
    class Meta:
        model = IndexInvariant
        fields = ('operator', 'index', 'value')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(IndexInvariantForm, self).__init__(*args, **kwargs)
        self.fields['index'].queryset = Index.objects.filter(
            Q(customer=get_customer()) | Q(customer=None)).exclude(
            role__in=[DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
                      DataRoleField.CO2_QUOTIENT])

    def save(self, commit=True):
        """
        C{IndexInvariantForm} specialization of C{ModelForm.save()}.  Unit is
        derived from the chosen index.
        """
        super(IndexInvariantForm, self).save(commit=False)
        self.instance.unit = self.instance.index.unit
        if commit:
            super(IndexInvariantForm, self).save(commit=True)
        return self.instance


class InputInvariantForm(ModelForm):
    """
    C{ModelForm} for L{InputInvariant}s.

    This form is intended for use in inline formsets, so it is required to
    work-out-of-the-box without special initialization requirements.
    """
    unit = forms.ChoiceField(
        choices=tuple(BLANK_CHOICE_DASH) +
        units.INPUT_CHOICES + units.CURRENCY_CHOICES)

    class Meta:
        model = InputInvariant
        fields = ('operator', 'data_series', 'value', 'unit')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(InputInvariantForm, self).__init__(*args, **kwargs)
        self.fields['data_series'].queryset = \
            DataSeries.objects.filter(
                graph__collection__customer=get_customer()).exclude(
                role__in=DataSeries.HIDDEN_ROLES).exclude(
                graph__role__in=DataSeries.HIDDEN_ROLES)

        customer = get_customer()
        self.fields['unit'].choices.extend(
            customer.get_production_unit_choices())


def triggeredrule_formsets(rule, meters_qs, data=None):
    IndexInvariantFormSet = inlineformset_factory(
        TriggeredRule, IndexInvariant, form=IndexInvariantForm, extra=0)
    InputInvariantFormSet = inlineformset_factory(
        TriggeredRule, InputInvariant, form=InputInvariantForm, extra=0)

    result = {
        'index_invariant': IndexInvariantFormSet(
            data, instance=rule, auto_id=False, prefix='index-invariant'),
        'input_invariant': InputInvariantFormSet(
            data, instance=rule, auto_id=False, prefix='input-invariant'),
    }
    result.update(base_rule_formsets(rule, meters_qs, data))
    return result


@customer_admin_or_error
@render_to('manage_rules/triggeredrule_form.html')
def triggeredrule_form(request, pk=None):
    customer = request.customer
    if pk:
        rule = get_object_or_404(TriggeredRule, pk=pk)
        if rule.customer != customer:
            return HttpResponseForbidden()
        initial = {}
    else:
        rule = None
        initial = {"timezone": get_customer().timezone}
    if request.method == 'POST':
        data = request.POST
    else:
        data = None
    form = TriggeredRuleForm(data, auto_id=False, instance=rule,
                             initial=initial)
    if data and form.is_valid():
        rule = form.save(commit=False)
    meters_qs = customer.meter_set.filter(relay_enabled=True)

    formsets = triggeredrule_formsets(rule, meters_qs, data)
    if data and form.is_valid() and all([f.is_valid()
                                         for f in formsets.itervalues()]):
        rule = form.save(commit=False)
        rule.customer = request.customer
        rule.save()
        for name, formset in formsets.iteritems():
            instances = formset.save(commit=False)
            for instance in instances:
                if name.endswith('_initial'):
                    instance.execution_time = Action.INITIAL
                elif name.endswith('_final'):
                    instance.execution_time = Action.FINAL
                instance.save()

        if pk:
            messages.success(request, _('The rule has been saved'))
        else:
            messages.success(request, _('The rule has been created'))

        if 'save_return' in data:
            return redirect('manage_rules-list')
        if not pk:
            return redirect('manage_rules-triggeredrule_form',
                            pk=rule.id)
        else:
            # reload formsets from DB, to get IDs, remove deleted...
            formsets = triggeredrule_formsets(rule, meters_qs)
    return {
        'form': form,
        'formsets': formsets,
    }


@customer_admin_or_error
def form(request, pk):
    if TriggeredRule.objects.filter(pk=pk).exists():
        return redirect('manage_rules-triggeredrule_form', pk=pk)
    elif MinimizeRule.objects.filter(pk=pk).exists():
        return redirect('manage_rules-minimizerule_form', pk=pk)
    raise Http404('No rule with pk=%s' % (pk,))


@require_http_methods(["POST"])
@customer_admin_or_error
def delete(request):
    pk = request.POST.get('pk', None)
    customer = request.customer
    rule = get_object_or_404(UserRule, pk=pk)
    if rule.customer != customer:
        return HttpResponseForbidden()
    rule.delete()
    messages.success(request, _('The rule has been deleted'))
    return redirect('manage_rules-list')
