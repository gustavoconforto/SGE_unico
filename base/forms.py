from django import forms
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


class UserForm(forms.ModelForm):
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
