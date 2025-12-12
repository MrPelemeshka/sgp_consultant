from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm

def register_view(request):
    """
    Представление для регистрации нового пользователя
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Автоматический вход после регистрации
            login(request, user)
            
            messages.success(request, f'Добро пожаловать, {user.username}! Регистрация прошла успешно.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users_app/register.html', {'form': form})

def login_view(request):
    """
    Представление для входа пользователя
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                
                # Редирект на страницу, с которой пришел пользователь, или на dashboard
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users_app/login.html', {'form': form})

@login_required
def profile_view(request):
    """
    Просмотр и редактирование профиля пользователя
    """
    user = request.user
    
    # Создаем контекст с дополнительными свойствами
    context = {
        'user': user,
        'is_moderator': user.is_moderator(),
        'is_admin': user.is_admin()
    }
    
    if request.method == 'POST':
        # Обновление информации профиля
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.company = request.POST.get('company', user.company)
        user.position = request.POST.get('position', user.position)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        
        # Обработка смены пароля
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            if user.check_password(current_password):
                if new_password == confirm_password:
                    user.set_password(new_password)
                    messages.success(request, 'Пароль успешно изменен.')
                    # После смены пароля нужно заново залогинить пользователя
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                else:
                    messages.error(request, 'Новые пароли не совпадают.')
            else:
                messages.error(request, 'Текущий пароль неверен.')
        
        user.save()
        messages.success(request, 'Профиль успешно обновлен.')
        return redirect('profile')
    
    return render(request, 'users_app/profile.html', context)