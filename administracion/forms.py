from django import forms

from clubs.models import Equipo

class GenerarCalendarioForm(forms.Form):
    
    division = forms.CharField(label="División", max_length=10)
    grupo = forms.CharField(label="Grupo", max_length=50)
    fecha_inicio = forms.DateField(label="Fecha de Inicio", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))

class SimularPartidosForm(forms.Form):
    
    MODOS = [("jornada", "Jornada completa"), ("individual", "Partido individual")]
    TIPOS = [("oficial", "Oficial"), ("amistoso", "Amistoso")]
    
    modo = forms.ChoiceField(label="Modo", choices=MODOS)
    tipo = forms.ChoiceField(label="Tipo de partido", choices=TIPOS)
    division = forms.IntegerField(label="División", min_value=1, required=False)
    grupo = forms.IntegerField(label="Grupo", min_value=1, required=False)
    jornada = forms.IntegerField(label="Jornada", min_value=1, max_value=14, required=False)
    equipo_local = forms.ModelChoiceField(
        label="Equipo Local", queryset=Equipo.objects.order_by("nombre_equipo"), required=False
    )
    equipo_visitante = forms.ModelChoiceField(
            label="Equipo Visitante", queryset=Equipo.objects.order_by("nombre_equipo"), required=False
        )
    
    def clean(self):
        
        datos = super().clean()
        if datos.get("modo") == "jornada":
            for campo in ("division", "grupo", "jornada"):
                if datos.get(campo) is None:
                    self.add_error(campo, "Obligatorio para simular una jornada completa")
        elif datos.get("modo") == "individual":
            local = datos.get("equipo_local")
            visitante = datos.get("equipo_visitante")
            if not local:
                self.add_error("equipo_local", "Elige el equipo local")
            if not visitante:
                self.add_error("equipo_visitante", "Elige el equipo visitante")
            if local and visitante and local == visitante:
                self.add_error("equipo_visitante", "Debe ser distinto del equipo local")
                
        return datos
    