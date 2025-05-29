# Обновить school/views.py

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
    Class, Faculty, ClubCategory, ClubInterestQuiz, Club,
    ClubApplication, ClubMember, ClubEvent, EventRegistration, QuizResult, Donation
)
from school.services import GetSchoolPartData
from school.utils import CacheData


def clubs_list(request):
    """Отображение списка клубов с фильтрацией и поиском"""

    # Получаем все категории и факультеты для фильтров
    categories = ClubCategory.objects.all()
    faculties = Faculty.objects.all()

    # Базовый queryset активных клубов
    clubs = Club.objects.select_related('category').prefetch_related('associated_faculties')

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

    # Активная викторина
    active_quiz = ClubInterestQuiz.objects.filter(is_active=True).first()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'faculties': faculties,
        'featured_clubs': featured_clubs,
        'active_quiz': active_quiz,
        'selected_category': category_id,
        'selected_faculty': faculty_id,
        'search_query': search_query,
        'sort_by': sort_by,
        'clubs': page_obj,  # Для совместимости
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
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Заявка подана успешно! Мы рассмотрим её в ближайшее время.',
                        'redirect_url': reverse('clubs_list')
                    })
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
def join_club(request, club_id):
    """Подача заявки на вступление в клуб"""
    club = get_object_or_404(Club, id=club_id, status='active')

    if not club.accepting_members:
        return JsonResponse({
            'success': False,
            'error': 'Клуб в настоящее время не принимает новых участников'
        })

    # Проверяем, не является ли пользователь уже участником
    existing_membership = ClubMember.objects.filter(club=club, user=request.user).first()
    if existing_membership:
        if existing_membership.status == 'active':
            return JsonResponse({
                'success': False,
                'error': 'Вы уже являетесь участником этого клуба'
            })
        elif existing_membership.status == 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Ваша заявка уже рассматривается'
            })

    # Создаем заявку на вступление
    try:
        with transaction.atomic():
            if existing_membership:
                existing_membership.status = 'pending'
                existing_membership.save()
            else:
                ClubMember.objects.create(
                    user=request.user,
                    club=club,
                    status='pending'
                )

            return JsonResponse({
                'success': True,
                'message': 'Заявка подана успешно!'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при подаче заявки'
        })


@login_required
def start_club_quiz(request):
    """Начало теста для подбора клуба"""
    active_quiz = get_object_or_404(ClubInterestQuiz, is_active=True)

    # Получаем первый вопрос
    first_question = active_quiz.questions.order_by('order').first()

    if not first_question:
        messages.error(request, 'Тест временно недоступен')
        return redirect('clubs_list')

    # Очищаем предыдущие ответы из сессии
    if 'quiz_answers' in request.session:
        del request.session['quiz_answers']

    context = {
        'quiz': active_quiz,
        'question': first_question,
        'question_number': 1,
        'total_questions': active_quiz.questions.count(),
    }

    return render(request, 'clubs/quiz_start.html', context)


@login_required
@require_POST
def submit_quiz_answer(request):
    """Обработка ответа на вопрос теста"""
    quiz_id = request.POST.get('quiz_id')
    question_id = request.POST.get('question_id')
    option_id = request.POST.get('option_id')

    quiz = get_object_or_404(ClubInterestQuiz, id=quiz_id, is_active=True)
    question = get_object_or_404(quiz.questions, id=question_id)

    # Сохраняем ответ в сессии
    if 'quiz_answers' not in request.session:
        request.session['quiz_answers'] = {}

    request.session['quiz_answers'][question_id] = option_id
    request.session.modified = True

    # Проверяем, есть ли следующий вопрос
    next_question = quiz.questions.filter(order__gt=question.order).order_by('order').first()

    if next_question:
        # Возвращаем следующий вопрос
        return JsonResponse({
            'status': 'next_question',
            'question': {
                'id': next_question.id,
                'text': next_question.text,
                'number': next_question.order,
                'total': quiz.questions.count(),
                'options': [
                    {'id': option.id, 'text': option.text}
                    for option in next_question.options.all()
                ]
            }
        })
    else:
        # Тест завершен, обрабатываем результаты
        try:
            result = process_quiz_results(request.user, quiz, request.session['quiz_answers'])
            return JsonResponse({
                'status': 'completed',
                'redirect_url': reverse('quiz_results')
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка при обработке результатов теста'
            }, status=500)


def process_quiz_results(user, quiz, answers):
    """Обработка результатов теста и подбор подходящих клубов"""
    from collections import defaultdict
    from school.models import QuizResult, UserAnswer, QuizOption, OptionCategoryRelation

    # Подсчитываем баллы по категориям
    category_scores = defaultdict(int)

    for question_id, option_id in answers.items():
        try:
            option = QuizOption.objects.get(id=option_id)
            # Получаем связи категорий с опцией
            relations = OptionCategoryRelation.objects.filter(option=option)
            for relation in relations:
                category_scores[relation.category] += relation.strength
        except QuizOption.DoesNotExist:
            continue

    # Сортируем категории по баллам
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

    # Получаем топ-3 категории
    top_categories = [cat for cat, score in sorted_categories[:3]]

    # Находим рекомендуемые клубы
    recommended_clubs = Club.objects.filter(
        category__in=top_categories,
        status='active',
        accepting_members=True
    ).order_by('-members_count')[:6]

    # Сохраняем результат
    with transaction.atomic():
        # Удаляем предыдущий результат если есть
        QuizResult.objects.filter(user=user, quiz=quiz).delete()

        # Создаем новый результат
        result = QuizResult.objects.create(
            user=user,
            quiz=quiz,
            top_category_1=top_categories[0] if len(top_categories) > 0 else None,
            top_category_2=top_categories[1] if len(top_categories) > 1 else None,
            top_category_3=top_categories[2] if len(top_categories) > 2 else None,
        )

        # Добавляем рекомендуемые клубы
        result.recommended_clubs.set(recommended_clubs)

        # Сохраняем ответы пользователя
        for question_id, option_id in answers.items():
            try:
                question = quiz.questions.get(id=question_id)
                option = QuizOption.objects.get(id=option_id)
                UserAnswer.objects.create(
                    quiz_result=result,
                    question=question,
                    selected_option=option
                )
            except (QuizOption.DoesNotExist, Exception):
                continue

    return result


@login_required
def quiz_results(request):
    """Отображение результатов теста"""
    # Получаем последний результат пользователя
    result = QuizResult.objects.filter(user=request.user).order_by('-date_taken').first()

    if not result:
        messages.error(request, 'Результаты теста не найдены. Пройдите тест заново.')
        return redirect('quiz_start')

    # Получаем рекомендуемые клубы
    recommended_clubs = result.recommended_clubs.all()

    # Получаем топ категории
    top_categories = [
        result.top_category_1,
        result.top_category_2,
        result.top_category_3
    ]
    top_categories = [cat for cat in top_categories if cat is not None]

    context = {
        'result': result,
        'recommended_clubs': recommended_clubs,
        'top_categories': top_categories,
    }

    return render(request, 'clubs/quiz_results.html', context)


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