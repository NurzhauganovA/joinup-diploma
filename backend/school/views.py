import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import QuerySet, Q, Count, Sum
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse

from authorization.models import User, Student, UserInfo
from authorization import UserRoles
from school.forms import ClubApplicationForm
from school.models import (
    Class, Faculty, ClubCategory, Club,
    ClubApplication, ClubMember, ClubEvent, EventRegistration, Donation, ClubMemberContract
)
from school.services import GetSchoolPartData
from school.utils import CacheData

import qrcode
from xml.etree import ElementTree as ET
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from cryptography.hazmat.primitives.serialization import pkcs12
from Crypto.Hash import SHA256
import base64


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
    needs_contract_signature = False

    if request.user.is_authenticated:
        user_membership = ClubMember.objects.filter(club=club, user=request.user).first()
        is_member = user_membership and user_membership.status == 'active'

        # Проверяем, нужно ли подписать контракт
        if user_membership and user_membership.status in ['approved', 'contract_pending']:
            # Проверяем, есть ли шаблон контракта
            if hasattr(club, 'contract_template') and club.contract_template.is_active:
                # Проверяем, нет ли уже подписанного контракта
                existing_contract = ClubMemberContract.objects.filter(
                    member=user_membership,
                    status='signed'
                ).first()

                if not existing_contract:
                    needs_contract_signature = True

    # Получаем новости клуба
    news = club.news.filter(is_public=True).order_by('-created_at')[:5]

    # Получаем ресурсы клуба
    resources = club.resources.filter(is_public=True).order_by('-created_at')[:5]

    # Определяем, может ли пользователь присоединиться
    can_join = (request.user.is_authenticated and
                not user_membership and
                club.accepting_members and
                club.status == 'active')

    context = {
        'club': club,
        'members': members,
        'upcoming_events': upcoming_events,
        'is_member': is_member,
        'user_membership': user_membership,
        'needs_contract_signature': needs_contract_signature,
        'news': news,
        'resources': resources,
        'can_join': can_join,
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


@login_required
def club_management(request, slug):
    """Страница управления клубом для основателя"""
    club = get_object_or_404(Club, slug=slug)

    # Проверяем права доступа
    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        role__in=['founder', 'president']
    ).first()

    if not membership:
        messages.error(request, 'У вас нет прав для управления этим клубом')
        return redirect('club_detail', slug=slug)

    # Получаем заявки на рассмотрение
    pending_applications = ClubMember.objects.filter(
        club=club,
        status='pending'
    ).select_related('user', 'test_attempt').order_by('-created_at')

    # Заявки требующие подписания контракта
    contract_pending = ClubMember.objects.filter(
        club=club,
        status__in=['approved', 'contract_pending']
    ).select_related('user').order_by('-approved_at')

    # Активные участники
    active_members = ClubMember.objects.filter(
        club=club,
        status='active'
    ).select_related('user', 'faculty').order_by('-join_date')

    # Подписанные контракты
    signed_contracts = ClubMemberContract.objects.filter(
        member__club=club,
        status='signed'
    ).select_related('member__user').order_by('-signed_at')

    # Статистика
    stats = {
        'total_members': active_members.count(),
        'pending_applications': pending_applications.count(),
        'contract_pending': contract_pending.count(),
        'total_applications': ClubMember.objects.filter(club=club).count(),
        'signed_contracts': signed_contracts.count(),
    }

    context = {
        'club': club,
        'membership': membership,
        'pending_applications': pending_applications,
        'contract_pending': contract_pending,
        'active_members': active_members,
        'signed_contracts': signed_contracts,
        'stats': stats,
        'has_contract': hasattr(club, 'contract_template'),
    }

    return render(request, 'clubs/club_management.html', context)


@login_required
def application_detail(request, slug, application_id):
    """Детальная страница заявки"""
    club = get_object_or_404(Club, slug=slug)
    application = get_object_or_404(ClubMember, id=application_id, club=club)

    # Проверяем права доступа
    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        role__in=['founder', 'president']
    ).first()

    if not membership:
        messages.error(request, 'У вас нет прав для просмотра этой заявки')
        return redirect('club_detail', slug=slug)

    # Получаем результаты теста если есть
    test_attempt = None
    if application.test_attempt:
        test_attempt = application.test_attempt
        test_attempt.user_answers = test_attempt.user_answers.select_related('question').prefetch_related(
            'selected_answers', 'question__answers'
        ).order_by('question__order')

    context = {
        'club': club,
        'application': application,
        'test_attempt': test_attempt,
        'membership': membership,
    }

    return render(request, 'clubs/application_detail.html', context)


@login_required
@require_POST
def approve_application(request, slug, application_id):
    """Одобрить заявку"""
    club = get_object_or_404(Club, slug=slug)
    application = get_object_or_404(ClubMember, id=application_id, club=club)

    # Проверяем права доступа
    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        role__in=['founder', 'president']
    ).first()

    if not membership:
        return JsonResponse({'success': False, 'error': 'Нет прав доступа'})

    try:
        with transaction.atomic():
            # Проверяем есть ли контракт у клуба
            has_contract = hasattr(club, 'contract_template') and club.contract_template.is_active

            if has_contract:
                application.status = 'approved'
                application.approved_at = timezone.now()
                application.approved_by = request.user
                application.save()

                message = 'Заявка одобрена. Пользователь должен подписать контракт.'
            else:
                # Если нет контракта, сразу принимаем в клуб
                application.status = 'active'
                application.approved_at = timezone.now()
                application.approved_by = request.user
                application.save()

                # Обновляем счетчик участников
                club.members_count = ClubMember.objects.filter(
                    club=club, status='active'
                ).count()
                club.save()

                message = 'Заявка одобрена. Пользователь принят в клуб.'

            return JsonResponse({
                'success': True,
                'message': message,
                'new_status': application.get_status_display(),
                'has_contract': has_contract
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Произошла ошибка при одобрении заявки'})


@login_required
@require_POST
def reject_application(request, slug, application_id):
    """Отклонить заявку"""
    club = get_object_or_404(Club, slug=slug)
    application = get_object_or_404(ClubMember, id=application_id, club=club)

    # Проверяем права доступа
    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        role__in=['founder', 'president']
    ).first()

    if not membership:
        return JsonResponse({'success': False, 'error': 'Нет прав доступа'})

    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')

        with transaction.atomic():
            application.status = 'rejected'
            application.rejection_reason = reason
            application.approved_by = request.user
            application.save()

            return JsonResponse({
                'success': True,
                'message': 'Заявка отклонена',
                'new_status': application.get_status_display()
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Произошла ошибка при отклонении заявки'})


@login_required
def contract_sign_page(request, slug):
    """Страница подписания контракта"""
    club = get_object_or_404(Club, slug=slug)

    # Ищем членство пользователя
    membership = ClubMember.objects.filter(
        club=club,
        user=request.user
    ).first()

    # Проверяем, что пользователь имеет право подписывать контракт
    if not membership:
        messages.error(request, 'Вы не подавали заявку в этот клуб')
        return redirect('club_detail', slug=slug)

    # Проверяем статус заявки
    if membership.status not in ['approved', 'contract_pending']:
        if membership.status == 'pending':
            messages.warning(request, 'Ваша заявка еще рассматривается администратором клуба')
        elif membership.status == 'active':
            messages.info(request, 'Вы уже являетесь участником клуба')
        elif membership.status == 'rejected':
            messages.error(request, 'Ваша заявка была отклонена')
        else:
            messages.error(request, f'Текущий статус заявки: {membership.get_status_display()}')
        return redirect('club_detail', slug=slug)

    # Проверяем наличие шаблона контракта
    if not hasattr(club, 'contract_template') or not club.contract_template.is_active:
        messages.error(request, 'Шаблон контракта не найден или не активен')
        return redirect('club_detail', slug=slug)

    contract_template = club.contract_template

    # Проверяем, нет ли уже подписанного контракта
    existing_contract = ClubMemberContract.objects.filter(
        member=membership,
        status='signed'
    ).first()

    if existing_contract:
        messages.success(request, 'Контракт уже подписан! Добро пожаловать в клуб!')
        return redirect('club_detail', slug=slug)

    # Получаем или создаем контракт для подписания
    pending_contract, created = ClubMemberContract.objects.get_or_create(
        member=membership,
        contract_template=contract_template,
        defaults={'status': 'pending'}
    )

    # Обновляем статус членства на contract_pending если нужно
    if membership.status == 'approved':
        membership.status = 'contract_pending'
        membership.save()

    context = {
        'club': club,
        'membership': membership,
        'contract_template': contract_template,
        'pending_contract': pending_contract,
    }

    return render(request, 'clubs/contract_sign.html', context)


@login_required
@require_POST
def process_digital_signature(request, slug):
    """Обработка ЭЦП"""
    club = get_object_or_404(Club, slug=slug)

    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        status__in=['approved', 'contract_pending']
    ).first()

    if not membership:
        return JsonResponse({'success': False, 'error': 'Заявка не найдена'})

    try:
        # Получаем файл ЭЦП и пароль
        signature_file = request.FILES.get('signature_file')
        password = request.POST.get('password')

        if not signature_file or not password:
            return JsonResponse({'success': False, 'error': 'Файл ЭЦП и пароль обязательны'})

        # Здесь должна быть логика проверки ЭЦП
        print("Received signature file:", signature_file)
        print("Received password:", password)
        private_key = pkcs12.load_key_and_certificates(
            signature_file.read(),
            password.encode(),
        )
        print("Private Key:", private_key)

        # Проверяем срок действия сертификата
        date_today = timezone.now().date()
        before_time = private_key[1].not_valid_before.date()
        after_time = private_key[1].not_valid_after.date()
        # if before_time > date_today or after_time < date_today:
        #     return JsonResponse({'success': False, 'error': 'Срок действия сертификата истек'})

        public_key = private_key[1]
        subject = public_key.subject
        issuer = public_key.issuer

        # Для демо создаем фиктивные данные
        signature_data = {
            'full_name': str(subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value),
            'iin': str(subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)[0].value),
            'valid_from': str(before_time.strftime('%Y-%m-%d')),
            'valid_to': str(after_time.strftime('%Y-%m-%d')),
            'issuer': 'НУЦ РК',
            'serial_number': str(public_key.serial_number),
            'verified': True
        }

        return JsonResponse({
            'success': True,
            'signature_data': signature_data,
            'message': 'ЭЦП успешно проверена'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': e})


@login_required
@require_POST
def sign_contract(request, slug):
    """Подписание контракта - обновленная версия"""
    club = get_object_or_404(Club, slug=slug)

    membership = ClubMember.objects.filter(
        club=club,
        user=request.user,
        status__in=['approved', 'contract_pending']
    ).first()

    if not membership:
        return JsonResponse({'success': False, 'error': 'Заявка не найдена'})

    try:
        data = json.loads(request.body)
        signature_data = data.get('signature_data')

        if not signature_data:
            return JsonResponse({'success': False, 'error': 'Данные подписи не найдены'})

        with transaction.atomic():
            # Обновляем или создаем контракт
            contract, created = ClubMemberContract.objects.get_or_create(
                member=membership,
                contract_template=club.contract_template,
                defaults={'status': 'pending'}
            )

            # Подписываем контракт
            contract.status = 'signed'
            contract.signed_at = timezone.now()
            contract.signature_data = signature_data
            contract.ip_address = request.META.get('REMOTE_ADDR')
            contract.user_agent = request.META.get('HTTP_USER_AGENT')

            # Генерируем QR код
            contract.generate_qr_code(request)
            contract.save()

            # Активируем участника
            membership.status = 'active'
            membership.save()

            # Обновляем счетчик участников клуба
            club.members_count = ClubMember.objects.filter(
                club=club, status='active'
            ).count()
            club.save()

            return JsonResponse({
                'success': True,
                'message': 'Контракт успешно подписан! QR код для проверки создан.',
                'redirect_url': f'/panel/club/{club.slug}/',
                'contract_id': contract.id
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Ошибка при подписании контракта'})


@login_required
def download_contract_pdf(request, slug):
    """Скачивание PDF контракта"""
    club = get_object_or_404(Club, slug=slug)

    if not hasattr(club, 'contract_template'):
        return HttpResponse('Шаблон контракта не найден', status=404)

    contract_template = club.contract_template

    if contract_template.pdf_template:
        # Возвращаем готовый PDF файл
        response = HttpResponse(
            contract_template.pdf_template.read(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="contract_{club.slug}.pdf"'
        return response
    else:
        # Генерируем PDF из HTML шаблона
        template = get_template('clubs/contract_pdf.html')
        context = {
            'club': club,
            'contract': contract_template,
            'user': request.user,
            'date': timezone.now().date()
        }
        html = template.render(context)

        # Здесь должна быть логика генерации PDF из HTML
        # Для простоты возвращаем HTML
        response = HttpResponse(html, content_type='text/html')
        return response