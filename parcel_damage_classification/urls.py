"""
URL configuration for parcel_damage_classification project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from admins import views as admins
from django.urls import path
from users import views as usr
from . import views as mainView
from django.contrib.staticfiles.urls import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', mainView.index, name='index'),
    path("UserRegister/", mainView.UserRegister, name="UserRegister"),
    path("Login/", mainView.Login, name="Login"),
    path('index/', mainView.index, name='index'),

    # Admin actions
    path("AdminLogin/", admins.AdminLoginCheck, name="AdminLogin"),
    path("AdminLoginCheck/", admins.AdminLoginCheck, name="AdminLoginCheck"),
    path("PredictionHistory/", admins.PredictionHistoryView, name="AdminPredictionHistory"),
    path("DeletePrediction/", admins.DeletePrediction, name="DeletePrediction"),
    path("EditUser/<int:user_id>/", admins.EditUser, name="EditUser"),

    ### User Side Views
    path("UserRegisterActions/", usr.UserRegisterActions, name="UserRegisterActions"),
    path("LoginCheck/", usr.LoginCheck, name="LoginCheck"),
    path("UserHome/", usr.UserHome, name="UserHome"),
    path('predict_view/',usr.predict_view,name='predict_view'),
    
    # New endpoints for Advanced Features
    path("ForgotPassword/", usr.ForgotPassword, name="ForgotPassword"),
    path("VerifyOTP/", usr.VerifyOTP, name="VerifyOTP"),
    path("DownloadReport/<int:history_id>/", usr.DownloadReport, name="DownloadReport"),
    path("SubmitComplaint/", usr.SubmitComplaint, name="SubmitComplaint"),


    ### Admin Side Views
    path("AdminHome/", admins.AdminHome, name="AdminHome"),
    path("ViewRegisteredUsers/", admins.ViewRegisteredUsers, name="ViewRegisteredUsers"),
    path("AdminActivaUsers/", admins.AdminActivaUsers, name="AdminActivaUsers"),
    path("EditUser/", admins.EditUser, name="EditUser"),
    path("EditUserAction/", admins.EditUserAction, name="EditUserAction"),
    path("DeleteUser/", admins.DeleteUser, name="DeleteUser"),
    path("BlockUser/", admins.BlockUser, name="BlockUser"),
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
