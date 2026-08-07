from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django import forms


class RegisterForm(UserCreationForm):
    avatar = forms.ImageField(required=False)

    class Meta:
        model = get_user_model()
        fields = ["username", "password1", "password2", "avatar"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""


class LoginForm(AuthenticationForm):
    pass


class ChangeAvatarForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["avatar"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["avatar"].required = True


class EditUsernameForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""


class LocationForm(forms.forms.Form):
    longitude = forms.DecimalField(max_digits=12, decimal_places=8)
    latitude = forms.DecimalField(max_digits=12, decimal_places=8)
