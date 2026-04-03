from django.shortcuts import render
from users.forms import UserRegistrationForm


# Create your views here.
def index(request):
    return render(request, 'index.html', {})



def logout(request):
    request.session.flush()
    from django.shortcuts import redirect
    return redirect('index')
def Login(request):
    return render(request, 'Login.html', {})

def UserRegister(request):
    form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})
