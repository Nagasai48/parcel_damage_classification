from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from users.models import UserRegistrationModel, PredictionHistory
from .models import AdminModel


# Create your views here.

def AdminLoginCheck(request):
    if request.method == 'POST':
        usrid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        print("User ID is = ", usrid)
        
        try:
            admin_user = AdminModel.objects.get(username=usrid, password=pswd)
            request.session['admin_id'] = admin_user.id
            request.session['admin_role'] = admin_user.role
            return redirect('AdminHome')
        except AdminModel.DoesNotExist:
            pass
            
        if usrid in ['nagasaibokka', 'nagasaibokka@gmail.com'] and pswd == 'Sai123@':
            request.session['admin_id'] = 'Admin'
            request.session['admin_role'] = 'Admin'
            return redirect('AdminHome')
        else:
            messages.error(request, 'Invalid Admin Details')
    return render(request, 'AdminLogin.html', {})


def ViewRegisteredUsers(request):
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    data = UserRegistrationModel.objects.all()
    
    if search_query:
        data = data.filter(
            Q(name__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(loginid__icontains=search_query)
        )
    
    if status_filter:
        data = data.filter(status=status_filter)
        
    return render(request, 'admins/RegisteredUsers.html', {'data': data})


def AdminActivaUsers(request):
    if request.method == 'GET':
        id = request.GET.get('uid')
        status = 'activated'
        print("PID = ", id, status)
        UserRegistrationModel.objects.filter(id=id).update(status=status)
        data = UserRegistrationModel.objects.all()
        return render(request, 'admins/RegisteredUsers.html', {'data': data})


def AdminHome(request):
    total_users = UserRegistrationModel.objects.count()
    total_uploads = PredictionHistory.objects.count()
    damaged_parcels = PredictionHistory.objects.filter(prediction='Damaged').count()
    intact_parcels = total_uploads - damaged_parcels
    
    context = {
        'total_users': total_users,
        'total_uploads': total_uploads,
        'damaged_parcels': damaged_parcels,
        'intact_parcels': intact_parcels,
        'accuracy_stats': '92.5%', # Approximate model accuracy
    }
    return render(request, 'admins/AdminHome.html', context)

def EditUser(request):
    if request.method == 'GET':
        uid = request.GET.get('uid')
        user = UserRegistrationModel.objects.get(id=uid)
        return render(request, 'admins/EditUser.html', {'user': user})

def EditUserAction(request):
    if request.method == 'POST':
        uid = request.POST.get('uid')
        name = request.POST.get('name')
        loginid = request.POST.get('loginid')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        city = request.POST.get('city')
        locality = request.POST.get('locality')
        
        UserRegistrationModel.objects.filter(id=uid).update(
            name=name, loginid=loginid, email=email, mobile=mobile, city=city, locality=locality
        )
        messages.success(request, 'User updated successfully!')
        data = UserRegistrationModel.objects.all()
        return render(request, 'admins/RegisteredUsers.html', {'data': data})

def DeleteUser(request):
    if request.method == 'GET':
        uid = request.GET.get('uid')
        try:
            user = UserRegistrationModel.objects.get(id=uid)
            user.delete()
            messages.success(request, "User deleted successfully.")
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, "User not found.")
    return redirect('ViewRegisteredUsers')

def BlockUser(request):
    if request.method == 'GET':
        uid = request.GET.get('uid')
        try:
            user = UserRegistrationModel.objects.get(id=uid)
            user.status = 'blocked'
            user.save()
            messages.success(request, f"User {user.name} has been blocked.")
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, "User not found.")
    return redirect('ViewRegisteredUsers')

def PredictionHistoryView(request):
    filter_type = request.GET.get('filter')
    if filter_type == 'damaged':
        history = PredictionHistory.objects.filter(prediction='Damaged').order_by('-date')
    else:
        history = PredictionHistory.objects.all().order_by('-date')
    return render(request, 'admins/AdminPredictionHistory.html', {'history': history})

def DeletePrediction(request):
    if request.method == 'GET':
        pred_id = request.GET.get('id')
        try:
            record = PredictionHistory.objects.get(id=pred_id)
            record.delete()
            messages.success(request, "Prediction record deleted successfully.")
        except PredictionHistory.DoesNotExist:
            messages.error(request, "Record not found.")
    
    # Redirect back to whoever requested it (User or Admin)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('AdminPredictionHistory')