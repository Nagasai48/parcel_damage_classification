from django.db import models

# Create your models here.
class UserRegistrationModel(models.Model):
    name = models.CharField(unique=True, max_length=100)
    loginid = models.CharField(unique=True, max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100)
    mobile = models.CharField(unique=True, max_length=100)
    email = models.CharField(unique=True, max_length=100)
    locality = models.CharField(max_length=100)
    address = models.CharField(max_length=1000)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    
    # New Fields
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email

    class Meta:
        db_table = 'UserRegistrations'

class PredictionHistory(models.Model):
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    image_url = models.CharField(max_length=500)
    prediction = models.CharField(max_length=200)
    confidence = models.CharField(max_length=50)
    
    # New Fields
    damage_type = models.CharField(max_length=100, null=True, blank=True)
    severity_score = models.CharField(max_length=50, null=True, blank=True)
    
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.prediction}"

class ComplaintModel(models.Model):
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.subject}"