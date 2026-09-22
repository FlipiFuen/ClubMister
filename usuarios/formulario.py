from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from clubs.models import Equipo

class RegistroForm(UserCreationForm):
    """
    Formulario de registro para nuevos usuarios
    Contiene campos para el correo electrónico, nombre del equipo y abreviatura del equipo
    Incluye validaciones para asegurar que el nombre del equipo sea único y que la abreviatura tenga exactamente 3 caracteres
    """
    email = forms.EmailField(required=True, label=_('Correo electrónico'), widget=forms.EmailInput(attrs={'class': 'form-control'}))
    nombre_equipo = forms.CharField(required=True, label=_('Nombre del equipo'), widget=forms.TextInput(attrs={'class': 'form-control'}))
    abreviatura = forms.CharField(
        required=True,
        max_length=3,
        label=_('Abreviatura'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text=_('Abreviatura de 3 letras para el equipo')
    )
    
    class Meta: 
        # Especifica que este formulario está asociado al modelo User de Django y define los campos que se incluirán en el formulario
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        
    def clean_nombre_equipo(self):
        """Valida que el nombre del equipo sea único """
        nombre_equipo = self.cleaned_data['nombre_equipo'].strip()
        
        if Equipo.objects.filter(nombre_equipo__iexact = nombre_equipo).exists():
            raise forms.ValidationError(_("El nombre del equipo ya existe"))
        return nombre_equipo
    
    def clean_abreviatura(self):
        """Comprueba que la abreviatura del equipo tenga exactamente 3 caracteres"""
        abreviatura = self.cleaned_data['abreviatura'].strip().upper()
        
        if len(abreviatura) != 3 or not abreviatura.isalpha():
             raise forms.ValidationError(_("La abreviatura debe tener exactamente 3 caracteres."))
        
        return abreviatura
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
        return user
            