from django.core.management.base import BaseCommand, CommandError

from administracion.services import generar_arbitros

class Command(BaseCommand):
    help = "Genera árbitros aleatorios en la base de datos"
    
    def add_arguments(self, parser):
        parser.add_argument("cantidad", type=int, help="Número de árbitros a crear")
        
    def handle(self, *args, **options):
        try:
            creados = generar_arbitros(options["cantidad"])
        except ValueError as e:
            raise CommandError(str(e)) from e
        
        self.stdout.write(self.style.SUCCESS(f"{len(creados)} árbitros creados"))