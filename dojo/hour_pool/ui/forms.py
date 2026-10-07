from django import forms
from dojo.models import HourPool, TimeEntry, ActivityType


class HourPoolForm(forms.ModelForm):
    class Meta:
        model = HourPool
        fields = ['name', 'total_hours', 'alert_threshold_pct', 'valid_from', 'valid_until', 'status', 'notes']
        widgets = {
            'name':                forms.TextInput(attrs={'class': 'form-control'}),
            'total_hours':         forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'alert_threshold_pct': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '99'}),
            'valid_from':          forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':              forms.Select(attrs={'class': 'form-control'}),
            'notes':               forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['pentest_project', 'analyst', 'date', 'hours', 'activity_type', 'description']
        widgets = {
            'pentest_project': forms.Select(attrs={'class': 'form-control'}),
            'analyst':         forms.Select(attrs={'class': 'form-control'}),
            'date':            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hours':           forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'activity_type':   forms.Select(attrs={'class': 'form-control'}),
            'description':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ActivityTypeForm(forms.ModelForm):
    class Meta:
        model = ActivityType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
