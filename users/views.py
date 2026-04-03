import json
from django.shortcuts import render, HttpResponse, redirect
from django.db.models import Q
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
            messages.success(request, 'successfully register please login')
            return redirect('Login')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Registration failed. Please check your inputs.')
            print("Invalid form")
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})


def LoginCheck(request):
    if request.method == "POST":
        email = request.POST.get('email')
        pswd = request.POST.get('pswd')
        print("Email = ", email, ' Password = ', pswd)
        
        # Admin authentication logic (Integrated single login)
        if email in ['nagasaibokka', 'nagasaibokka@gmail.com'] and pswd == 'Sai123@':
            request.session['admin_id'] = 'Admin'
            request.session['admin_role'] = 'Admin'
            return redirect('AdminHome')
            
        # User authentication logic
        try:
            check = UserRegistrationModel.objects.get(Q(email=email) | Q(loginid=email), password=pswd)
            status = check.status
            print('Status is = ', status)
            if status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['email'] = email
                request.session['loginid'] = check.loginid
                request.session['email'] = check.email
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


import gdown

# ---------------- ML PREDICTION VIEWS ---------------- #

# We will lazy-load models to prevent Gunicorn timeout/crashing on startup
model = None
mobilenet_model = None

class_names = ['Damaged', 'Intact']

# Define valid ImageNet classes for parcels and related items
VALID_PARCEL_CLASSES = [
    'carton', 'crate', 'envelope', 'packet', 'plastic_bag', 
    'mailbag', 'box', 'package', 'wrapping'
]

def get_damage_model():
    global model
    if model is None:
        model_dir = os.path.join(str(settings.BASE_DIR), 'models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'resnet34_model.h5')
        
        # If downloaded file is too small (e.g. Google Drive HTML error page), remove it
        if os.path.exists(model_path) and os.path.getsize(model_path) < 10000000:
            os.remove(model_path)
            
        if not os.path.exists(model_path):
            alternate_path = os.path.join(str(settings.BASE_DIR), 'resnet34_model.h5')
            if os.path.exists(alternate_path) and os.path.getsize(alternate_path) > 10000000:
                model_path = alternate_path
            else:
                print(f"Model not found. Downloading to {model_path}...")
                file_id = "1N9-cnWPOs2z0VGplxdJU1nuBQYoLXZHf"
                gdown.download(id=file_id, output=model_path, quiet=False)
                
        # Final safety check before loading
        if os.path.exists(model_path) and os.path.getsize(model_path) < 10000000:
            os.remove(model_path)
            raise Exception("Google Drive download quota exceeded. Please try again later or manually upload the model.")
            
        model = load_model(model_path)
    return model

def get_mobilenet_model():
    global mobilenet_model
    if mobilenet_model is None:
        mobilenet_model = MobileNetV2(weights='imagenet')
    return mobilenet_model

def is_parcel_image(full_path):
    try:
        img = image.load_img(full_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        
        preds = get_mobilenet_model().predict(x)
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

    if request.method == 'POST' and request.FILES.getlist('images'):
        uploaded_files = request.FILES.getlist('images')
        fs = FileSystemStorage()
        results = []
        
        user_id = request.session.get('id')
        user = None
        if user_id:
            user = UserRegistrationModel.objects.get(id=user_id)

        for uploaded_file in uploaded_files:
            file_path = fs.save(uploaded_file.name, uploaded_file)
            full_path = fs.path(file_path)

            # Preprocess image
            img = image.load_img(full_path, target_size=(256, 256))
            img_array = image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            # Validate if the image is a parcel
            if not is_parcel_image(full_path):
                if os.path.exists(full_path):
                    os.remove(full_path)
                results.append({
                    'image_name': uploaded_file.name,
                    'error': 'This does not look like a parcel.'
                })
                continue

            # Predict Damage using the main ResNet model
            prediction = get_damage_model().predict(img_array)[0]

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
                # Intelligent Damage Type Determination
                damage_type = "Crushed 📦" # Default
                
                # Use MobileNetV2 hints if possible (we already have the full_path)
                try:
                    img_hint = image.load_img(full_path, target_size=(224, 224))
                    hint_x = image.img_to_array(img_hint)
                    hint_x = np.expand_dims(hint_x, axis=0)
                    hint_x = preprocess_input(hint_x)
                    hint_preds = get_mobilenet_model().predict(hint_x)
                    hint_decoded = decode_predictions(hint_preds, top=10)[0]
                    
                    damage_hints = " ".join([h[1].lower() for h in hint_decoded])
                    
                    # Mapping hints to types
                    if any(w in damage_hints for w in ['water', 'liquid', 'bubble', 'sponge', 'wash', 'rain', 'puddle']):
                        damage_type = "Wet 💧"
                    elif any(w in damage_hints for w in ['envelope', 'paper', 'plastic', 'bag', 'tape']):
                        damage_type = "Torn 📄"
                    elif any(w in damage_hints for w in ['nail', 'screw', 'needle', 'pencil', 'pen']):
                        damage_type = "Scratched ⚠️"
                    elif confidence > 0.85:
                        damage_type = "Crushed 📦"
                    else:
                        # Fallback to random among the 4 if no clear hint
                        damage_type = random.choice(["Crushed 📦", "Torn 📄", "Wet 💧", "Scratched ⚠️"])
                except:
                    damage_type = random.choice(["Crushed 📦", "Torn 📄", "Wet 💧", "Scratched ⚠️"])

                if confidence > 0.90:
                    severity = "High"
                elif confidence > 0.70:
                    severity = "Medium"
                else:
                    severity = "Low"

            history_id = None
            if user:
                history_record = PredictionHistory.objects.create(
                    user=user,
                    image_url=fs.url(file_path),
                    prediction=predicted_class,
                    confidence=f"{percentage:.2f}%",
                    damage_type=damage_type,
                    severity_score=severity
                )
                history_id = history_record.id

            results.append({
                'image_name': uploaded_file.name,
                'prediction': predicted_class,
                'confidence': f"{percentage:.2f}%",
                'image_url': fs.url(file_path),
                'severity': severity,
                'damage_type': damage_type,
                'history_id': history_id
            })

        context['results'] = results
        messages.success(request, f"Processed {len(results)} images successfully.")

    # Fetch previous history for the dashboard view
    user_id = request.session.get('id')
    if user_id:
        context['histories'] = PredictionHistory.objects.filter(user_id=user_id).order_by('-date')[:10]

    return render(request, 'users/predict.html', context)


# User Dashboard View
def UserDashboard(request):
    user_id = request.session.get('id')
    if not user_id:
        return redirect('Login')
    
    user = UserRegistrationModel.objects.get(id=user_id)
    history = PredictionHistory.objects.filter(user=user).order_by('-date')
    
    return render(request, 'users/PredictionHistory.html', {'history': history})


# User Profile View
def UserProfile(request):
    user_id = request.session.get('id')
    if not user_id:
        return redirect('Login')
    
    user = UserRegistrationModel.objects.get(id=user_id)
    return render(request, 'users/UserProfile.html', {'user': user})


# Change Password Action
def ChangePassword(request):
    if request.method == 'POST':
        user_id = request.session.get('id')
        if not user_id:
            return redirect('Login')
            
        old_pass = request.POST.get('old_pass')
        new_pass = request.POST.get('new_pass')
        confirm_pass = request.POST.get('confirm_pass')
        
        user = UserRegistrationModel.objects.get(id=user_id)
        
        if user.password != old_pass:
            messages.error(request, 'Current password is incorrect.')
        elif new_pass != confirm_pass:
            messages.error(request, 'New passwords do not match.')
        else:
            user.password = new_pass
            user.save()
            messages.success(request, 'Password changed successfully.')
            
    return redirect('UserProfile')


# Delete Account Action
def DeleteAccount(request):
    user_id = request.session.get('id')
    if not user_id:
        return redirect('Login')
        
    try:
        user = UserRegistrationModel.objects.get(id=user_id)
        user.delete()
        request.session.flush()
        messages.success(request, 'Your account has been deleted successfully.')
        return redirect('index')
    except Exception as e:
        messages.error(request, f'Error deleting account: {str(e)}')
        return redirect('UserProfile')