import json
import re
from sqlite3 import Date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import QuerySet, Q
from django.views.decorators.http import require_POST

from authorization.models import User, Student, UserInfo
from authorization import UserRoles
from contract.services.contract import CreateContractService
from school.forms import ClubApplicationForm
from school.models import Class, Faculty, ClubCategory, ClubInterestQuiz, Club
from school.services import GetSchoolPartData
from school.utils import CacheData
from contract.models import Contract, Transaction, ContractDayPay, ContractMonthPay
from django.db.models import Sum
from django.utils import timezone


def school_part(request: HttpRequest):
    context = {}

    return render(request, "school/school_part.html", context)


def clubs_list(request):
    """Display the School part page with club listings and filtering"""

    # Get all categories and faculties for filters
    categories = ClubCategory.objects.all()
    faculties = Faculty.objects.all()

    # Get base queryset of active clubs
    clubs = Club.objects.filter(status='active')

    # Apply filters if any
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
            Q(description__icontains=search_query)
        )

    # Apply sorting
    sort_by = request.GET.get('sort', 'popular')
    if sort_by == 'newest':
        clubs = clubs.order_by('-establishment_date')
    elif sort_by == 'oldest':
        clubs = clubs.order_by('establishment_date')
    elif sort_by == 'popular':
        clubs = clubs.order_by('-members_count')
    elif sort_by == 'alphabetical':
        clubs = clubs.order_by('name')

    # Pagination
    paginator = Paginator(clubs, 12)  # Show 12 clubs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Featured clubs for carousel
    featured_clubs = Club.objects.filter(is_featured=True, status='active')[:5]

    # Get quiz for club matching
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
    }

    return render(request, 'clubs/clubs_list.html', context)


@login_required
def create_club_application(request):
    """Handle creation of a new club application"""

    if request.method == 'POST':
        form = ClubApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.founder = request.user
            application.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Your club application has been submitted successfully and is pending review.'
            })
        else:
            # Return form errors for AJAX validation
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)
    else:
        # This is just for non-AJAX fallback
        form = ClubApplicationForm()
        faculties = Faculty.objects.all()
        categories = ClubCategory.objects.all()

        context = {
            'form': form,
            'faculties': faculties,
            'categories': categories,
        }

        return render(request, 'clubs/create_club.html', context)


def get_club_application_form(request):
    """Return the club application form for modal loading"""
    faculties = Faculty.objects.all()
    categories = ClubCategory.objects.all()

    context = {
        'faculties': faculties,
        'categories': categories,
    }

    return render(request, 'clubs/includes/club_application_form.html', context)


@login_required
def start_club_quiz(request):
    """Start the club interest quiz"""
    active_quiz = get_object_or_404(ClubInterestQuiz, is_active=True)

    # Get the first question
    first_question = active_quiz.questions.order_by('order').first()

    context = {
        'quiz': active_quiz,
        'question': first_question,
    }

    return render(request, 'clubs/quiz_start.html', context)


@login_required
@require_POST
def submit_quiz_answer(request):
    """Handle quiz answer submission via AJAX"""
    quiz_id = request.POST.get('quiz_id')
    question_id = request.POST.get('question_id')
    option_id = request.POST.get('option_id')

    quiz = get_object_or_404(ClubInterestQuiz, id=quiz_id)
    question = get_object_or_404(quiz.questions, id=question_id)

    # Store answer in session for now
    if 'quiz_answers' not in request.session:
        request.session['quiz_answers'] = {}

    request.session['quiz_answers'][question_id] = option_id
    request.session.modified = True

    # Check if there are more questions
    next_question = quiz.questions.filter(order__gt=question.order).order_by('order').first()

    if next_question:
        # Return next question
        return JsonResponse({
            'status': 'next_question',
            'question_id': next_question.id,
            'question_text': next_question.text,
            'options': list(next_question.options.values('id', 'text'))
        })
    else:
        # Process results
        # In a real implementation, this would calculate and store results
        # For now, just redirect to a result page
        return JsonResponse({
            'status': 'completed',
            'redirect_url': '/clubs/quiz-results/'
        })


@login_required
def quiz_results(request):
    """Display quiz results"""
    # In a real implementation, this would retrieve and display actual results
    # For now, just show a basic results page

    # Recommended clubs based on user's answers
    # This would normally be calculated from the answers
    recommended_clubs = Club.objects.filter(status='active').order_by('?')[:3]

    context = {
        'recommended_clubs': recommended_clubs,
    }

    return render(request, 'clubs/quiz_results.html', context)