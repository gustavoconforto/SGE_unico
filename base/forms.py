from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission, User


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "permissions"]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "permissions": forms.SelectMultiple(
                attrs={
                    "class": "w-full h-64 rounded-field border border-base-content/20 "
                    "bg-base-100 p-2 text-sm focus:outline-2 focus:outline-neutral"
                }
            ),
        }


class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ["name", "content_type", "codename"]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "content_type": forms.Select(
                attrs={
                    "class": "select select-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "codename": forms.TextInput(
                attrs={
                    "class": "input input-neutral  w-full",
                    "placeholder": "Digite...",
                }
            ),
        }


class UserStatusFieldsMixin:
    """Drops is_active/is_staff/is_superuser unless `can_set_status`.

    user_form.html shows them only to superusers; left in the form, a missing
    field would save as False and deactivate the user.
    """

    status_fields = ("is_active", "is_staff", "is_superuser")

    def __init__(self, *args, can_set_status=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_set_status:
            for name in self.status_fields:
                del self.fields[name]


class UserForm(UserStatusFieldsMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "is_staff",
            "is_active",
            "is_superuser",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "email": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "is_staff": forms.NullBooleanSelect(
                attrs={
                    "class": "select select-bordered w-full max-w-xs",
                }
            ),
            "is_active": forms.NullBooleanSelect(
                attrs={
                    "class": "select select-bordered w-full max-w-xs",
                }
            ),
            "is_superuser": forms.NullBooleanSelect(
                attrs={
                    "class": "select select-bordered w-full max-w-xs",
                }
            ),
        }


class UserCreateForm(UserStatusFieldsMixin, UserCreationForm):
    """UserForm plus the password, so the new user can log in."""

    class Meta(UserForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs["class"] = "input input-neutral w-full"
        # Django's help text is an HTML list, which the field component escapes.
        self.fields["password1"].help_text = (
            "Mínimo de 8 caracteres, não pode ser só números nem parecida com os "
            "dados do usuário."
        )
