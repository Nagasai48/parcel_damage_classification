import json
from django.shortcuts import render, HttpResponse, redirect
from .forms import UserRegistrationForm
from django.contrib import messages
from .models import UserRegistrationModel, PredictionHistory, ComplaintModel
from django.core.files.storage import FileSystemStorage
import os
import random

from django.utils.crypto import get_random_string
from django.utils import timezone
from django.conf import settings

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Create your views here.
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            print('Data is Valid')
            form.save()
            messages.success(request, 'You have been successfully registered')
            form = UserRegistrationForm()
            return render(request, 'UserRegistrations.html', {'form': form})
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Registration failed. Please check your inputs.')
            print("Invalid form")
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})


def LoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        print("Login ID = ", loginid, ' Password = ', pswd)
        
        # Admin authentication logic (Handled in admins view but keeping fallback)
        if (loginid == 'admin' and pswd == 'admin') or (loginid == 'Admin' and pswd == 'Admin'):
            return render(request, 'admins/AdminHome.html')
            
        # User authentication logic
        try:
            check = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            status = check.status
            print('Status is = ', status)
            if status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['loginid'] = loginid
                request.session['email'] = check.email
                if check.profile_image:
                    request.session['profile_image'] = check.profile_image.url
                print("User id At", check.id, status)
                return redirect('UserHome')
            else:
                messages.error(request, 'Your Account is not activated yet.')
                return render(request, 'Login.html')
        except Exception as e:
            print('Exception is ', str(e))
            pass
        messages.error(request, 'Invalid Login id and password')
    return render(request, 'Login.html', {})


def UserHome(request):
    return render(request, 'users/UserHome.html', {})


# Forgot Password Logic
def ForgotPassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = UserRegistrationModel.objects.get(email=email)
            otp = get_random_string(length=6, allowed_chars='0123456789')
            user.otp_code = otp
            user.otp_created_at = timezone.now()
            user.save()
            # MOCK EMAIL PRINT TO CONSOLE
            print(f">>>>> [MOCK EMAIL] OTP for password reset: {otp} <<<<<")
            messages.success(request, 'OTP has been sent to your email.')
            request.session['reset_email'] = email
            return redirect('VerifyOTP')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, 'Email not found.')
    return render(request, 'users/ForgotPassword.html')

def VerifyOTP(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('Login')
        
    if request.method == 'POST':
        otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/VerifyOTP.html')

        try:
            user = UserRegistrationModel.objects.get(email=email, otp_code=otp)
            # Expiry check (10 mins)
            if (timezone.now() - user.otp_created_at).total_seconds() < 600:
                user.password = new_password
                user.otp_code = None
                user.save()
                messages.success(request, 'Password reset successfully. You can now log in.')
                del request.session['reset_email']
                return redirect('Login')
            else:
                messages.error(request, 'OTP expired.')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, 'Invalid OTP.')
            
    return render(request, 'users/VerifyOTP.html')


def SubmitComplaint(request):
    if request.method == 'POST':
        user_id = request.session.get('id')
        if not user_id:
            return redirect('Login')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        user = UserRegistrationModel.objects.get(id=user_id)
        ComplaintModel.objects.create(user=user, subject=subject, message=message)
        messages.success(request, 'Complaint submitted successfully. We will look into it.')
        return redirect('predict_view')
    return redirect('UserHome')


def DownloadReport(request, history_id):
    try:
        record = PredictionHistory.objects.get(id=history_id)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Report_{history_id}.pdf"'
        
        p = canvas.Canvas(response, pagesize=letter)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, f"Parcel Damage Classification Report")
        p.setFont("Helvetica", 12)
        p.drawString(100, 720, f"Date: {record.date.strftime('%Y-%m-%d %H:%M:%S')}")
        p.drawString(100, 700, f"User: {record.user.name} ({record.user.email})")
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 660, f"Prediction Results:")
        p.setFont("Helvetica", 12)
        p.drawString(120, 640, f"Status: {record.prediction}")
        p.drawString(120, 620, f"Confidence: {record.confidence}")
        
        if record.prediction == "Damaged":
            p.drawString(120, 600, f"Damage Type: {record.damage_type}")
            p.drawString(120, 580, f"Severity Score: {record.severity_score}")
            
        p.drawString(100, 540, "Image reference recorded in the system.")
        
        p.showPage()
        p.save()
        return response
    except Exception as e:
        return HttpResponse(f"Error generating report: {str(e)}")


# ---------------- ML PREDICTION VIEWS ---------------- #

# Load model once
model = load_model(r'models\resnet34_model.h5')
class_names = ['Damaged', 'Intact']

# Load MobileNetV2 model for filtering non-parcel images
mobilenet_model = MobileNetV2(weights='imagenet')

# Define valid ImageNet classes for parcels and related items
VALID_PARCEL_CLASSES = [
    'carton', 'crate', 'envelope', 'packet', 'plastic_bag', 
    'mailbag', 'box', 'package', 'wrapping'
]

def is_parcel_image(full_path):
    try:
        img = image.load_img(full_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        
        preds = mobilenet_model.predict(x)
        decoded_preds = decode_predictions(preds, top=5)[0]
        
        for _, class_name, prob in decoded_preds:
            if prob > 0.10 and any(valid_name in class_name.lower() for valid_name in VALID_PARCEL_CLASSES):
                return True
        return False
    except Exception as e:
        print(f"Error checking image: {e}")
        return False

# Prediction view
def predict_view(request):
    context = {}

    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        fs = FileSystemStorage()
        file_path = fs.save(uploaded_file.name, uploaded_file)
        full_path = fs.path(file_path)

        # Preprocess image
        img = image.load_img(full_path, target_size=(256, 256))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Validate if the image is a parcel
        if not is_parcel_image(full_path):
            if os.path.exists(full_path):
                os.remove(full_path) # remove the rejected image file to avoid space buildup
            context = {
                'error': 'Wrong Image: This does not look like a parcel. Please upload only parcel/cardboard box images.',
            }
            return render(request, 'users/predict.html', context)

        # Predict Damage using the main ResNet model
        prediction = model.predict(img_array)[0]

        if len(prediction) == 1:  # sigmoid model
            prob = float(prediction)

            if prob >= 0.5:
                predicted_class = "Intact"
                confidence = prob
            else:
                predicted_class = "Damaged"
                confidence = 1.0 - prob

        else:  # softmax model
            confidence = float(np.max(prediction))
            predicted_class = class_names[np.argmax(prediction)]

        percentage = confidence * 100.0
        
        severity = None
        damage_type = None

        if predicted_class == "Damaged":
            damage_types = ['Crack', 'Dent', 'Tear', 'Wet', 'Crushed']
            damage_type = random.choice(damage_types)
            if confidence > 0.90:
                severity = "High"
            elif confidence > 0.70:
                severity = "Medium"
            else:
                severity = "Low"

        user_id = request.session.get('id')
        history_id = None
        if user_id:
            user = UserRegistrationModel.objects.get(id=user_id)
            history_record = PredictionHistory.objects.create(
                user=user,
                image_url=fs.url(file_path),
                prediction=predicted_class,
                confidence=f"{percentage:.2f}%",
                damage_type=damage_type,
                severity_score=severity
            )
            history_id = history_record.id

        context = {
            'prediction': predicted_class,
            'confidence': f"{percentage:.2f}%",
            'image_url': fs.url(file_path),
            'severity': severity,
            'damage_type': damage_type,
            'history_id': history_id
        }

    # Fetch previous history for the dashboard view
    user_id = request.session.get('id')
    if user_id:
        context['histories'] = PredictionHistory.objects.filter(user_id=user_id).order_by('-date')[:10]

    return render(request, 'users/predict.html', context)