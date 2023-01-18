from django import forms
from .models import TenantProfile, MaintenanceCharge

from django.contrib.auth import get_user_model

CUser = get_user_model()


class TenantCreateForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = CUser
        fields = ('username', 'first_name', 'last_name')

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

    # def clean_email(self):
    #     data = self.cleaned_data['email']
    #     if CUser.objects.filter(email=data).exists():
    #         # if settings.AUTH_USER_MODEL.objects.filter(email=data).exists():
    #         raise forms.ValidationError('Email already in use.')
    #     return data


class TenantProfileCreateForm(forms.ModelForm):
    class Meta:
        model = TenantProfile
        # fields = {'room_no','elec_unit','water_unit','misc_cost'}
        exclude = ['tenant', 'deduct', 'cum_ovd', 'elec_unit', 'water_unit', 'misc_cost', 'late_fee', 'maint_cost']


class PaymentForm(forms.Form):
    payment_amount = forms.DecimalField(max_digits=7, decimal_places=2,
                                        widget=forms.NumberInput(
                                            attrs={'class': 'paid_amount', 'placeholder': 'amount', 'min': 0}))
    payment_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'pay_date', 'placeholder': 'date'}))


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceCharge
        fields = {'room_no', 'job_cost'}
        widgets = {

            'job_cost': forms.NumberInput(attrs={'class': 'job_cost', 'placeholder': 'Baht', 'min': 0})
        }


class Elec_cpu_change(forms.Form):
    elec_cpu = forms.DecimalField(max_digits=7, decimal_places=2,
                                  widget=forms.NumberInput(
                                      attrs={'class': 'elec_cpu', 'placeholder': 'elec_cpu', 'min': 0}))


class Water_cpu_change(forms.Form):
    water_cpu = forms.DecimalField(max_digits=7, decimal_places=2,
                                   widget=forms.NumberInput(
                                       attrs={'class': 'water_cpu', 'placeholder': 'water_cpu', 'min': 0}))


class PhoneNoMessage(forms.Form):
    phone_no = forms.CharField(max_length=10)
    sms_msg = forms.CharField(widget=forms.Textarea)
    # msg = forms.CharField(widget=forms.TextInput( attrs={'class': 'msg'}))


class BillForm(forms.ModelForm):
    class Meta:
        model = TenantProfile
        fields = {'elec_unit', 'water_unit'}
        widgets = {
            'elec_unit': forms.NumberInput({'class': 'eu', 'placeholder': 'elect-unit', 'min': 0}),
            'water_unit': forms.NumberInput(attrs={'class': 'wu', 'placeholder': 'water-unit', 'min': 0})
        }

