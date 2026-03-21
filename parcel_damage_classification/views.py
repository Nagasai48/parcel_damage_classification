from django.shortcuts import render
from users.forms import UserRegistrationForm


# Create your views here.
def index(request):
    return render(request, 'index.html', {})



def logout(request):
    return render(request, 'index.html', {})

def Login(request):
    return render(request, 'Login.html', {})

def UserRegister(request):
    form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})
