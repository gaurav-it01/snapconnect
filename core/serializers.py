from rest_framework import serializers
from django import forms


class LocationForm(forms.forms.Form):
    longitude = forms.DecimalField(max_digits=12, decimal_places=8)
    latitude = forms.DecimalField(max_digits=12, decimal_places=8)
