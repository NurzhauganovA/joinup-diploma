import json

from django.contrib import messages, auth
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse, HttpRequest
from django.shortcuts import render, redirect
from django.http.request import HttpRequest
from django.urls import reverse
from django.urls import reverse

from authorization import UserRoles
from authorization.models import User, UserInfo
from authorization.utils import send_email, verify_account
from contract.models import Contract


def login(request: HttpRequest):
    if request.method == 'POST':
        mobile_phone = request.POST.get('mobile_phone')
        password = request.POST.get('password')

        user: User = User.objects.filter(mobile_phone=mobile_phone).first()
        print(mobile_phone)

        if user is None:
            messages.error(request, 'User with this phone number does not exist!')
            return redirect('login')

        if not user.check_password(password):
            messages.error(request, 'Password is incorrect!')
            return redirect('login')

        auth.login(request, user)
        user.save_login_days()
        user.create_user_info()

        return redirect('/')

    return render(request, 'authorization/login.html')


def register(request: HttpRequest):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        mobile_phone = request.POST.get('mobile_phone')
        role = request.POST.get('role')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')

        if User.objects.filter(mobile_phone=mobile_phone).exists():
            messages.error(request, 'User with this phone number already exists!')
            return redirect('register')

        new_user = User.objects.create(
            full_name=full_name,
            mobile_phone=mobile_phone,
            role=role,
            password=password
        )

        messages.success(request, 'User created successfully!')

        request.session['mobile_phone'] = mobile_phone
        request.session['password'] = password

        return redirect('enter-email')
    return render(request, 'authorization/register.html')


def enter_email(request: HttpRequest):
    if request.method == 'POST':
        email = request.POST.get('email')

        send_email(
            email=email,
            subject='JoinUp - Verify email',
            message='Your verification code'
        )

        request.session['email'] = email

        return redirect('verify-email')

    return render(request, 'authorization/enter_email.html')


def verify_email(request: HttpRequest):
    mobile_phone = request.session.get('mobile_phone')
    password = request.session.get('password')
    email = request.session.get('email')

    if request.method == 'POST':
        body = json.loads(request.body)
        code = body.get('verification_code')

        if verify_account(email=email, code=int(code)):
            user = User.objects.filter(mobile_phone=mobile_phone).first()
            user.email = email
            user.save()

            if not user.check_password(password):
                return JsonResponse({'message': 'Password is incorrect!', 'status': 400})

            auth.login(request, user)
            user.save_login_days()
            user.create_user_info()

            return JsonResponse({'message': 'User verified successfully!', 'status': 200})

        return JsonResponse({'message': 'Verification code is incorrect!', 'status': 400})

    return render(request, 'authorization/verify_email.html', {'email': email})


def logout(request: HttpRequest):
    auth.logout(request)
    return redirect('login')


def profile(request: HttpRequest):
    user = request.user
    user_profile = UserInfo.objects.get(user=user)

    if isinstance(user, AnonymousUser):
        return redirect('login')

    completion_percentage = int(100 - (user_profile.empty_fields() / 5 * 100))

    context = {
        'user': user,
        'completion_percentage': completion_percentage
    }

    return render(request, 'authorization/profile.html', context)


def edit_profile(request: HttpRequest):
    user = request.user
    user_profile = UserInfo.objects.get(user=user)

    if request.method == 'POST':
        photo_avatar = request.FILES.get('photo_avatar')
        email = request.POST.get('email')
        mobile_phone = request.POST.get('mobile_phone')
        address = request.POST.get('address')
        iin = request.POST.get('iin')
        birth_date = request.POST.get('birth_date')
        full_name = request.POST.get('full_name')

        if User.objects.filter(email=email).exclude(id=user_profile.user.id):
            messages.error(request, 'User with this email already exists!')
            user_profile.user.email = user.email

        if User.objects.filter(mobile_phone=mobile_phone).exclude(id=user_profile.user.id):
            messages.error(request, 'User with this phone number already exists!')
            user_profile.user.mobile_phone = user.mobile_phone

        if UserInfo.objects.filter(iin=iin).exclude(id=user_profile.id):
            messages.error(request, 'User with this IIN already exists!')
            user_profile.iin = user_profile.iin
        else:
            user_profile.iin = iin

        user_profile.photo_avatar = photo_avatar
        user_profile.address = address
        user_profile.birth_date = birth_date
        user_profile.user.full_name = full_name

        user_profile.save()
        user_profile.user.save()

        return redirect('profile')

    completion_percentage = int(100 - (user_profile.empty_fields() / 5 * 100))

    context = {
        'user': user,
        'completion_percentage': completion_percentage
    }

    return render(request, 'authorization/edit_profile.html', context)


def my_contracts(request: HttpRequest):
    user = request.user
    user_profile = UserInfo.objects.get(user=user)
    contracts = Contract.objects.filter(student__user=user)

    contracts_count = Contract.objects.filter(student__user=user).count()
    completion_percentage = int(100 - (user_profile.empty_fields() / 5 * 100))

    context = {
        'user': user,
        'debt_sum': '990800',
        'contracts_count': contracts_count,
        'completion_percentage': completion_percentage,
        'contracts': contracts
    }

    return render(request, 'authorization/my_contracts.html', context)


def forgot_password(request: HttpRequest):

    if request.method == "POST":
        email = request.POST.get("email")

        send_email(
            email=email,
            subject="JoinUp - Reset password",
            message="Your verification code"
        )

        request.session['email'] = email

        return redirect("verify-by-code")
    
    return JsonResponse({"error": "Not Allowed Method", "status": 405})


def verify_by_code(request: HttpRequest):

    if request.method == "POST":
        email = request.session.get("email")
        body = json.loads(request.body)
        code = body.get('verification_code')

        if verify_account(email, code):
            return redirect("set-password")
        
        return JsonResponse({'message': 'Verification code is incorrect!', 'status': 400})
    
    return JsonResponse({"error": "Not Allowed Method", "status": 405})



def set_new_password(request: HttpRequest):
    
    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('set-password')
        
        user: User = User.objects.get(email=request.session.get("email"))

        user.set_password(password)
        
        return redirect("login")
    
    return JsonResponse({"error": "Not Allowed Method", "status": 405})
