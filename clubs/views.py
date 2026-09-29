from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def club(request):
    return render(request, 'clubs/club.html')
