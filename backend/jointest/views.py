import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from school.models import Club, ClubMember, JoinTestAttempt, JoinTestQuestion, JoinTestUserAnswer, JoinTestAnswer


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
        elif existing_membership.status in ['pending', 'test_required', 'test_in_progress']:
            return JsonResponse({
                'success': False,
                'error': 'Ваша заявка уже рассматривается'
            })

    # Проверяем, есть ли у клуба тест для вступления
    has_test = hasattr(club, 'join_test') and club.join_test.is_active

    try:
        with transaction.atomic():
            if existing_membership:
                # Обновляем существующую заявку
                if has_test:
                    existing_membership.status = 'test_required'
                else:
                    existing_membership.status = 'pending'
                existing_membership.save()
                membership = existing_membership
            else:
                # Создаем новую заявку
                membership = ClubMember.objects.create(
                    user=request.user,
                    club=club,
                    status='test_required' if has_test else 'pending'
                )

            return JsonResponse({
                'success': True,
                'message': 'Заявка подана успешно!',
                'has_test': has_test,
                'membership_id': membership.id
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при подаче заявки'
        })


@login_required
def join_test_info(request, membership_id):
    """Страница с информацией о тесте перед началом"""
    membership = get_object_or_404(
        ClubMember,
        id=membership_id,
        user=request.user,
        status__in=['test_required', 'test_failed']
    )

    if not hasattr(membership.club, 'join_test') or not membership.club.join_test.is_active:
        messages.error(request, 'Тест для этого клуба недоступен')
        return redirect('club_detail', slug=membership.club.slug)

    test = membership.club.join_test

    # Проверяем, может ли пользователь пройти тест
    if not membership.can_take_test():
        messages.error(request, f'Вы превысили максимальное количество попыток ({test.max_attempts})')
        return redirect('club_detail', slug=membership.club.slug)

    # Получаем предыдущие попытки
    previous_attempts = JoinTestAttempt.objects.filter(
        user=request.user,
        test=test
    ).order_by('-started_at')[:3]

    context = {
        'membership': membership,
        'club': membership.club,
        'test': test,
        'previous_attempts': previous_attempts,
        'attempts_left': test.max_attempts - membership.attempts_count,
        'questions_count': test.questions.count(),
    }

    return render(request, 'jointest/join_test_info.html', context)


@login_required
@require_POST
def start_join_test(request, membership_id):
    """Начать прохождение теста"""
    membership = get_object_or_404(
        ClubMember,
        id=membership_id,
        user=request.user,
        status__in=['test_required', 'test_failed']
    )

    test = membership.club.join_test

    # Проверяем, может ли пользователь пройти тест
    if not membership.can_take_test():
        return JsonResponse({
            'success': False,
            'error': 'Вы превысили максимальное количество попыток'
        })

    # Проверяем, нет ли уже активной попытки
    active_attempt = membership.get_current_attempt()
    if active_attempt:
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('take_join_test', args=[active_attempt.id])
        })

    try:
        with transaction.atomic():
            # Создаем новую попытку
            attempt = JoinTestAttempt.objects.create(
                user=request.user,
                test=test,
                status='in_progress',
                total_questions=test.questions.count()
            )

            # Обновляем статус участника
            membership.status = 'test_in_progress'
            membership.attempts_count += 1
            membership.test_attempt = attempt
            membership.save()

            return JsonResponse({
                'success': True,
                'redirect_url': reverse('take_join_test', args=[attempt.id])
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при создании теста'
        })


@login_required
def take_join_test(request, attempt_id):
    """Страница прохождения теста"""
    attempt = get_object_or_404(
        JoinTestAttempt,
        id=attempt_id,
        user=request.user,
        status='in_progress'
    )

    # Проверяем, не истекло ли время
    if attempt.is_expired():
        attempt.status = 'expired'
        attempt.completed_at = timezone.now()
        attempt.save()

        # Обновляем статус участника
        membership = ClubMember.objects.get(user=request.user, club=attempt.test.club)
        membership.status = 'test_failed'
        membership.save()

        messages.error(request, 'Время прохождения теста истекло')
        return redirect('club_detail', slug=attempt.test.club.slug)

    # Получаем вопросы теста
    questions = attempt.test.questions.prefetch_related('answers').order_by('order')

    # Получаем уже данные ответы
    user_answers = {
        ua.question_id: ua for ua in
        attempt.user_answers.select_related('question').prefetch_related('selected_answers')
    }

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'club': attempt.test.club,
        'questions': questions,
        'user_answers': user_answers,
        'time_left': max(0, (attempt.test.time_limit * 60) - (timezone.now() - attempt.started_at).seconds),
    }

    return render(request, 'jointest/take_join_test.html', context)


@login_required
@require_POST
def submit_test_answer(request, attempt_id):
    """Сохранить ответ на вопрос теста"""
    attempt = get_object_or_404(
        JoinTestAttempt,
        id=attempt_id,
        user=request.user,
        status='in_progress'
    )

    if attempt.is_expired():
        return JsonResponse({
            'success': False,
            'error': 'Время прохождения теста истекло'
        })

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        selected_answers = data.get('selected_answers', [])
        text_answer = data.get('text_answer', '')

        question = get_object_or_404(JoinTestQuestion, id=question_id, test=attempt.test)

        # Получаем или создаем ответ пользователя
        user_answer, created = JoinTestUserAnswer.objects.get_or_create(
            attempt=attempt,
            question=question,
            defaults={'text_answer': text_answer}
        )

        if not created:
            user_answer.text_answer = text_answer
            user_answer.selected_answers.clear()

        # Сохраняем выбранные ответы
        if selected_answers:
            correct_answers = JoinTestAnswer.objects.filter(
                question=question,
                is_correct=True
            ).values_list('id', flatten=True)

            user_answer.selected_answers.set(selected_answers)

            # Проверяем правильность ответа
            if question.question_type == 'single':
                user_answer.is_correct = len(selected_answers) == 1 and selected_answers[0] in correct_answers
            elif question.question_type == 'multiple':
                user_answer.is_correct = set(selected_answers) == set(correct_answers)

            user_answer.points_earned = question.points if user_answer.is_correct else 0

        user_answer.save()

        return JsonResponse({
            'success': True,
            'is_correct': user_answer.is_correct,
            'points_earned': user_answer.points_earned
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при сохранении ответа'
        })


@login_required
@require_POST
def complete_join_test(request, attempt_id):
    """Завершить прохождение теста"""
    attempt = get_object_or_404(
        JoinTestAttempt,
        id=attempt_id,
        user=request.user,
        status='in_progress'
    )

    try:
        with transaction.atomic():
            # Подсчитываем результаты
            user_answers = attempt.user_answers.all()
            correct_answers = user_answers.filter(is_correct=True).count()
            total_points = sum(ua.points_earned for ua in user_answers)
            max_points = sum(q.points for q in attempt.test.questions.all())

            # Вычисляем процент
            score = (total_points / max_points * 100) if max_points > 0 else 0

            # Обновляем попытку
            attempt.status = 'passed' if score >= attempt.test.passing_score else 'failed'
            attempt.score = score
            attempt.correct_answers = correct_answers
            attempt.completed_at = timezone.now()
            attempt.time_spent = (timezone.now() - attempt.started_at).seconds
            attempt.save()

            # Обновляем статус участника
            membership = ClubMember.objects.get(user=request.user, club=attempt.test.club)
            if attempt.status == 'passed':
                membership.status = 'pending'  # Ожидает одобрения администратора
            else:
                membership.status = 'test_failed'
            membership.save()

            return JsonResponse({
                'success': True,
                'redirect_url': reverse('join_test_results', args=[attempt.id])
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при завершении теста'
        })


@login_required
def join_test_results(request, attempt_id):
    """Страница с результатами теста"""
    attempt = get_object_or_404(
        JoinTestAttempt,
        id=attempt_id,
        user=request.user,
        status__in=['passed', 'failed', 'expired']
    )

    # Получаем детальные результаты
    user_answers = attempt.user_answers.select_related('question').prefetch_related(
        'selected_answers', 'question__answers'
    ).order_by('question__order')

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'club': attempt.test.club,
        'user_answers': user_answers,
        'is_passed': attempt.is_passed(),
        'membership': ClubMember.objects.get(user=request.user, club=attempt.test.club),
    }

    return render(request, 'jointest/join_test_results.html', context)