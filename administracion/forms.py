from django import forms

class GenerarCalendarioForm(forms.Form):
    
    division = forms.CharField(label="División", max_length=10)
    grupo = forms.CharField(label="Grupo", max_length=50)
    fecha_inicio = forms.DateField(label="Fecha de Inicio", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    