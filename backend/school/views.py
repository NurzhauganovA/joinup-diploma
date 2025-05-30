import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import QuerySet, Q, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse

from authorization.models import User, Student, UserInfo
from authorization import UserRoles
from school.forms import ClubApplicationForm
from school.models import (
    Class, Faculty, ClubCategory, Club,
    ClubApplication, ClubMember, ClubEvent, EventRegistration, Donation
)
from school.services import GetSchoolPartData
from school.utils import CacheData


def clubs_list(request):
    """Отображение списка клубов с фильтрацией и поиском"""

    # Получаем все категории и факультеты для фильтров
    categories = ClubCategory.objects.all()
    faculties = Faculty.objects.all()

    # Базовый queryset активных клубов
    clubs = Club.objects.filter(status="active").select_related('category').prefetch_related('associated_faculties')

    # Применяем фильтры
    category_id = request.GET.get('category')
    faculty_id = request.GET.get('faculty')
    search_query = request.GET.get('search', '')

    if category_id:
        clubs = clubs.filter(category_id=category_id)

    if faculty_id:
        clubs = clubs.filter(associated_faculties__id=faculty_id)

    if search_query:
        clubs = clubs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )

    # Применяем сортировку
    sort_by = request.GET.get('sort', 'popular')
    if sort_by == 'newest':
        clubs = clubs.order_by('-establishment_date')
    elif sort_by == 'oldest':
        clubs = clubs.order_by('establishment_date')
    elif sort_by == 'popular':
        clubs = clubs.annotate(total_members=Count('members')).order_by('-total_members', '-views_count')
    elif sort_by == 'alphabetical':
        clubs = clubs.order_by('name')

    # Пагинация
    paginator = Paginator(clubs, 12)  # 12 клубов на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Рекомендуемые клубы
    featured_clubs = Club.objects.filter(is_featured=True, status='active')[:5]

    members_count = ClubMember.objects.filter(
        club__in=clubs,
        status='active'
    ).count()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'faculties': faculties,
        'featured_clubs': featured_clubs,
        'selected_category': category_id,
        'selected_faculty': faculty_id,
        'search_query': search_query,
        'sort_by': sort_by,
        'clubs': clubs,
        'total_clubs': clubs.count(),
        'members_count': members_count,
    }

    return render(request, 'clubs/clubs_list.html', context)


def club_detail(request, slug):
    """Детальная страница клуба"""
    club = get_object_or_404(Club, slug=slug)

    # Увеличиваем счетчик просмотров
    club.views_count += 1
    club.save(update_fields=['views_count'])

    # Получаем участников клуба
    members = ClubMember.objects.filter(club=club, status='active').select_related('user', 'faculty')

    # Получаем предстоящие события
    upcoming_events = ClubEvent.objects.filter(
        club=club,
        start_date__gte=timezone.now()
    ).order_by('start_date')[:3]

    # Проверяем, является ли пользователь участником
    is_member = False
    user_membership = None
    if request.user.is_authenticated:
        user_membership = ClubMember.objects.filter(club=club, user=request.user).first()
        is_member = user_membership and user_membership.status == 'active'

    # Получаем новости клуба
    news = club.news.filter(is_public=True).order_by('-created_at')[:5]

    # Получаем ресурсы клуба
    resources = club.resources.filter(is_public=True).order_by('-created_at')[:5]

    context = {
        'club': club,
        'members': members,
        'upcoming_events': upcoming_events,
        'is_member': is_member,
        'user_membership': user_membership,
        'news': news,
        'resources': resources,
        'can_join': request.user.is_authenticated and not is_member and club.accepting_members,
    }

    return render(request, 'clubs/club_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_club_application(request):
    """Создание заявки на новый клуб"""

    if request.method == 'POST':
        form = ClubApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    application = form.save(commit=False)
                    application.founder = request.user
                    application.save()

                    messages.success(request, 'Ваша заявка на создание клуба успешно подана!')
                    return redirect('clubs_list')
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Произошла ошибка при подаче заявки. Попробуйте еще раз.'
                }, status=500)
        else:
            # Возвращаем ошибки валидации
            return JsonResponse({
                'status': 'error',
                'errors': form.errors,
                'message': 'Пожалуйста, исправьте ошибки в форме.'
            }, status=400)

    # GET запрос - показываем форму (обычно через AJAX)
    faculties = Faculty.objects.all()
    categories = ClubCategory.objects.all()

    context = {
        'form': ClubApplicationForm(),
        'faculties': faculties,
        'categories': categories,
    }

    return render(request, 'clubs/includes/club_application_form.html', context)


@login_required
@require_POST
def register_for_event(request, event_id):
    """Регистрация на мероприятие клуба"""
    event = get_object_or_404(ClubEvent, id=event_id)

    # Проверяем, требуется ли регистрация
    if not event.registration_required:
        return JsonResponse({
            'success': False,
            'error': 'Регистрация на это мероприятие не требуется'
        })

    # Проверяем дедлайн регистрации
    if event.registration_deadline and timezone.now() > event.registration_deadline:
        return JsonResponse({
            'success': False,
            'error': 'Срок регистрации истек'
        })

    # Проверяем лимит участников
    if event.max_participants > 0 and event.current_participants >= event.max_participants:
        return JsonResponse({
            'success': False,
            'error': 'Все места заняты'
        })

    # Проверяем, не зарегистрирован ли уже пользователь
    existing_registration = EventRegistration.objects.filter(
        event=event,
        user=request.user
    ).first()

    if existing_registration:
        return JsonResponse({
            'success': False,
            'error': 'Вы уже зарегистрированы на это мероприятие'
        })

    # Создаем регистрацию
    try:
        with transaction.atomic():
            EventRegistration.objects.create(
                event=event,
                user=request.user,
                status='registered'
            )

            # Увеличиваем счетчик участников
            event.current_participants += 1
            event.save(update_fields=['current_participants'])

            return JsonResponse({
                'success': True,
                'message': 'Вы успешно зарегистрированы на мероприятие!'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при регистрации'
        })


def get_club_application_form(request):
    """Возвращает форму заявки на создание клуба для модального окна"""
    faculties = Faculty.objects.all()
    categories = ClubCategory.objects.all()

    context = {
        'faculties': faculties,
        'categories': categories,
    }

    return render(request, 'clubs/includes/club_application_form.html', context)


# Дополнительные вспомогательные функции

def get_user_club_recommendations(user):
    """Получение рекомендаций клубов для пользователя"""
    # Базовые рекомендации по факультету
    recommendations = []

    try:
        if hasattr(user, 'student_info'):
            student = user.student_info
            if student.stud_class and student.stud_class.school:
                # Рекомендуем клубы той же школы
                school_clubs = Club.objects.filter(
                    school=student.stud_class.school,
                    status='active',
                    accepting_members=True
                )[:3]
                recommendations.extend(school_clubs)

        # Если рекомендаций мало, добавляем популярные клубы
        if len(recommendations) < 6:
            popular_clubs = Club.objects.filter(
                status='active',
                accepting_members=True
            ).annotate(
                total_members=Count('members')
            ).order_by('-total_members')[:6 - len(recommendations)]
            recommendations.extend(popular_clubs)

    except Exception:
        # В случае ошибки возвращаем популярные клубы
        recommendations = Club.objects.filter(
            status='active',
            accepting_members=True
        ).annotate(
            total_members=Count('members')
        ).order_by('-total_members')[:6]

    return recommendations


@login_required
def my_clubs(request):
    """Страница клубов пользователя"""
    # Получаем членство пользователя в клубах
    memberships = ClubMember.objects.filter(
        user=request.user
    ).select_related('club', 'club__category').order_by('-join_date')

    # Разделяем по статусам
    active_memberships = memberships.filter(status='active')
    pending_memberships = memberships.filter(status='pending')

    # Получаем предстоящие события клубов пользователя
    user_clubs = [m.club for m in active_memberships]
    upcoming_events = ClubEvent.objects.filter(
        club__in=user_clubs,
        start_date__gte=timezone.now()
    ).order_by('start_date')[:5]

    context = {
        'active_memberships': active_memberships,
        'pending_memberships': pending_memberships,
        'upcoming_events': upcoming_events,
        'total_clubs': active_memberships.count(),
    }

    return render(request, 'clubs/my_clubs.html', context)


@login_required
def club_donations(request, slug):
    """Страница донатов для клуба"""
    club = get_object_or_404(Club, slug=slug)

    # Получаем статистику донатов
    total_donations = club.donations.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0

    donations_count = club.donations.filter(status='completed').count()

    # Последние донаты (не анонимные)
    recent_donations = club.donations.filter(
        status='completed',
        is_anonymous=False
    ).select_related('user').order_by('-created_at')[:5]

    context = {
        'club': club,
        'total_donations': total_donations,
        'donations_count': donations_count,
        'recent_donations': recent_donations,
    }

    return render(request, 'clubs/club_donations.html', context)


@login_required
@require_POST
def make_donation(request, slug):
    """Создание доната для клуба"""
    club = get_object_or_404(Club, slug=slug)

    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        message = data.get('message', '')
        is_anonymous = data.get('is_anonymous', False)

        # Валидация суммы
        if not amount or float(amount) <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Некорректная сумма доната'
            })

        if float(amount) > 100000:  # Максимальная сумма
            return JsonResponse({
                'success': False,
                'error': 'Максимальная сумма доната: 100,000 тенге'
            })

        # Создаем донат
        with transaction.atomic():
            donation = Donation.objects.create(
                club=club,
                user=request.user,
                amount=float(amount),
                message=message,
                is_anonymous=is_anonymous,
                status='pending'  # В реальном приложении здесь была бы интеграция с платежной системой
            )

            # В реальном приложении здесь был бы редирект на платежную систему
            # Для демо сразу помечаем как завершенный
            donation.status = 'completed'
            donation.transaction_id = f'demo_{donation.id}_{timezone.now().timestamp()}'
            donation.save()

            return JsonResponse({
                'success': True,
                'message': 'Спасибо за поддержку клуба!',
                'donation_id': donation.id
            })

    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'error': 'Некорректные данные'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при обработке доната'
        })