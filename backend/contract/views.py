from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages

from school.models import ClubMemberContract, ClubContract, Club, ClubMember


@login_required
def contracts_list(request):
    """Список всех контрактов пользователя"""

    # Получаем все контракты пользователя
    user_contracts = ClubMemberContract.objects.filter(
        member__user=request.user
    ).select_related(
        'member__club',
        'member__club__category',
        'contract_template'
    ).order_by('-created_at')

    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        user_contracts = user_contracts.filter(status=status_filter)

    # Поиск по названию клуба
    search_query = request.GET.get('search', '')
    if search_query:
        user_contracts = user_contracts.filter(
            Q(member__club__name__icontains=search_query) |
            Q(contract_template__title__icontains=search_query)
        )

    # Пагинация
    paginator = Paginator(user_contracts, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Статистика
    stats = {
        'total_contracts': user_contracts.count(),
        'signed_contracts': user_contracts.filter(status='signed').count(),
        'pending_contracts': user_contracts.filter(status='pending').count(),
        'expired_contracts': user_contracts.filter(status='expired').count(),
    }

    # Недавние контракты для быстрого доступа
    recent_contracts = ClubMemberContract.objects.filter(
        member__user=request.user,
        status='signed'
    ).select_related('member__club').order_by('-signed_at')[:5]

    context = {
        'page_obj': page_obj,
        'contracts': user_contracts,
        'stats': stats,
        'recent_contracts': recent_contracts,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': ClubMemberContract.STATUS_CHOICES,
    }

    return render(request, 'contract/contracts_list.html', context)


@login_required
def contract_detail(request, contract_id):
    """Детальная страница контракта"""

    contract = get_object_or_404(
        ClubMemberContract,
        id=contract_id,
        member__user=request.user
    )

    # Получаем историю изменений статуса (если есть модель для этого)
    status_history = []

    # Проверяем права доступа
    can_download = contract.status == 'signed' and contract.signed_pdf
    can_view_details = True

    # Информация о подписи
    signature_info = None
    if contract.signature_data:
        signature_info = contract.signature_data

    # Связанные контракты того же клуба
    related_contracts = ClubMemberContract.objects.filter(
        member__club=contract.member.club,
        member__user=request.user
    ).exclude(id=contract.id).order_by('-created_at')[:3]

    context = {
        'contract': contract,
        'can_download': can_download,
        'can_view_details': can_view_details,
        'signature_info': signature_info,
        'status_history': status_history,
        'related_contracts': related_contracts,
    }

    return render(request, 'contract/contract_detail.html', context)


@login_required
def download_signed_contract(request, contract_id):
    """Скачивание подписанного контракта"""

    contract = get_object_or_404(
        ClubMemberContract,
        id=contract_id,
        member__user=request.user,
        status='signed'
    )

    if not contract.signed_pdf:
        messages.error(request, 'Подписанный файл контракта не найден')
        return redirect('contracts:detail', contract_id=contract_id)

    try:
        response = HttpResponse(
            contract.signed_pdf.read(),
            content_type='application/pdf'
        )
        filename = f"contract_{contract.member.club.slug}_{contract.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, 'Ошибка при скачивании файла')
        return redirect('contracts:detail', contract_id=contract_id)


@login_required
def contract_verification(request, contract_id):
    """Проверка подлинности контракта"""

    contract = get_object_or_404(
        ClubMemberContract,
        id=contract_id,
        member__user=request.user,
        status='signed'
    )

    verification_data = {
        'contract_id': contract.id,
        'club_name': contract.member.club.name,
        'member_name': contract.member.user.full_name,
        'signed_at': contract.signed_at,
        'signature_valid': bool(contract.signature_data),
        'contract_hash': f"CONTRACT_{contract.id}_{contract.signed_at.timestamp()}" if contract.signed_at else None,
    }

    if contract.signature_data:
        verification_data.update({
            'signer_name': contract.signature_data.get('full_name'),
            'signer_iin': contract.signature_data.get('iin'),
            'certificate_issuer': contract.signature_data.get('issuer'),
            'certificate_valid_from': contract.signature_data.get('valid_from'),
            'certificate_valid_to': contract.signature_data.get('valid_to'),
        })

    qr_data = contract.get_qr_code_data()

    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'success': True,
            'verification': verification_data,
            'qr_code': qr_data
        })

    context = {
        'contract': contract,
        'verification_data': verification_data,
        'qr_data': qr_data,
    }

    return render(request, 'contract/contract_verification.html', context)


@login_required
def contracts_dashboard(request):
    """Дашборд контрактов с аналитикой"""

    user_memberships = ClubMember.objects.filter(user=request.user)

    # Статистика по контрактам
    total_memberships = user_memberships.count()
    active_memberships = user_memberships.filter(status='active').count()
    pending_contracts = ClubMemberContract.objects.filter(
        member__user=request.user,
        status='pending'
    ).count()

    # Последние активности
    recent_activities = []

    # Недавно подписанные контракты
    recent_signed = ClubMemberContract.objects.filter(
        member__user=request.user,
        status='signed'
    ).order_by('-signed_at')[:3]

    for contract in recent_signed:
        recent_activities.append({
            'type': 'signed',
            'club_name': contract.member.club.name,
            'date': contract.signed_at,
            'contract_id': contract.id,
        })

    # Ожидающие подписания
    pending_signature = ClubMemberContract.objects.filter(
        member__user=request.user,
        status='pending'
    ).order_by('-created_at')[:3]

    for contract in pending_signature:
        recent_activities.append({
            'type': 'pending',
            'club_name': contract.member.club.name,
            'date': contract.created_at,
            'contract_id': contract.id,
        })

    # Сортируем активности по дате
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:5]

    # Клубы по категориям
    club_categories = {}
    for membership in user_memberships.filter(status='active'):
        category = membership.club.category.name
        if category not in club_categories:
            club_categories[category] = []
        club_categories[category].append(membership.club)

    context = {
        'total_memberships': total_memberships,
        'active_memberships': active_memberships,
        'pending_contracts': pending_contracts,
        'recent_activities': recent_activities,
        'club_categories': club_categories,
    }

    return render(request, 'contract/dashboard.html', context)