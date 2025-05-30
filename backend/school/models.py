from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from school import Regions


class School(models.Model):
    """ Модель школы """

    logo = models.ImageField(upload_to='school/logo/', null=True, blank=True)
    name = models.CharField(max_length=155)
    address = models.CharField(max_length=155)
    direct = models.CharField(max_length=155)
    language = models.CharField(max_length=155)
    country = models.CharField(max_length=155, null=True, blank=True)
    region = models.CharField(max_length=155, choices=Regions.get_choices(), default=Regions.AQMOLA)
    city = models.CharField(max_length=155, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    bin = models.CharField(max_length=12)
    short_name = models.CharField(max_length=155)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Школа')
        verbose_name_plural = _('Школы')
        db_table = 'school'


class SchoolRequisites(models.Model):
    """ Модель реквизитов школы """

    school = models.ForeignKey(School, on_delete=models.CASCADE, null=False)
    bank_name = models.CharField(max_length=155, null=False)
    bank_address = models.CharField(max_length=155, null=False)
    bank_bik = models.CharField(max_length=9, null=False)
    bank_iik = models.CharField(max_length=20, null=False)
    bank_kbe = models.CharField(max_length=20, null=False)
    bank_bin = models.CharField(max_length=12, null=False)

    def __str__(self):
        return f'{self.school} - {self.bank_name}'

    class Meta:
        verbose_name = _('Реквизит школы')
        verbose_name_plural = _('Реквизиты школ')
        db_table = 'school_requisites'


class Class(models.Model):
    """ Модель класса """

    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
    class_num = models.IntegerField(null=False)
    class_liter = models.CharField(max_length=10, null=False)
    description = models.TextField(null=True, blank=True)
    mentor = models.ForeignKey('authorization.User', on_delete=models.SET_NULL, null=True, related_name='class_teacher')
    is_graduated = models.BooleanField(default=False)
    max_class_num = models.PositiveIntegerField(default=4)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.class_num}{self.class_liter}'

    class Meta:
        verbose_name = _('Класс')
        verbose_name_plural = _('Классы')
        db_table = 'class'


class OurSchools(models.Model):
    """ Модель наших школ """

    school = models.OneToOneField(School, on_delete=models.SET_NULL, null=True)
    city_short_name = models.CharField(max_length=155, null=False)
    short_name = models.CharField(max_length=155, null=False)
    fix_sum_contract = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    is_yearly_payment = models.BooleanField(default=True)

    def __str__(self):
        return self.short_name

    class Meta:
        verbose_name = _("Информация о школе")
        verbose_name_plural = _("Информация о школах")
        db_table = 'our_schools'


class Faculty(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Faculty"
        verbose_name_plural = "Faculties"
        db_table = 'faculties'


class ClubCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='club_category_icons/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Club Category"
        verbose_name_plural = "Club Categories"
        db_table = 'club_categories'


class Club(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
    )

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='clubs')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='club_logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='club_banners/', blank=True, null=True)
    description = models.TextField()
    short_description = models.CharField(max_length=200)
    establishment_date = models.DateField()
    category = models.ForeignKey(ClubCategory, on_delete=models.CASCADE, related_name='clubs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Social media links
    instagram = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    telegram = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Club settings
    accepting_members = models.BooleanField(default=True)
    members_limit = models.PositiveIntegerField(default=0, help_text="0 means no limit")
    is_featured = models.BooleanField(default=False)

    # Faculty associations
    associated_faculties = models.ManyToManyField(Faculty, related_name='clubs', blank=True)

    # Stats
    views_count = models.PositiveIntegerField(default=0)
    members_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        db_table = 'clubs'
        ordering = ['-created_at']

    def get_members_count(self):
        """Получить количество участников клуба"""
        return ClubMember.objects.filter(club=self, status='active').count()


class ClubMember(models.Model):
    ROLE_CHOICES = (
        ('founder', 'Founder'),
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('member', 'Member'),
        ('trainer', 'Trainer'),
        ('advisor', 'Advisor'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
        ('test_required', 'Test Required'),  # Новый статус
        ('test_in_progress', 'Test In Progress'),  # Новый статус
        ('test_failed', 'Test Failed'),  # Новый статус
    )

    user = models.ForeignKey('authorization.User', on_delete=models.CASCADE, related_name='club_memberships')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    join_date = models.DateField(auto_now_add=True)
    faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, null=True, blank=True)
    bio = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    academic_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_public = models.BooleanField(default=True, help_text="Whether this membership is visible to others")

    # Новые поля для тестирования
    test_attempt = models.ForeignKey("JoinTestAttempt", on_delete=models.SET_NULL, null=True, blank=True)
    attempts_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_take_test(self):
        """Может ли пользователь пройти тест"""
        if not hasattr(self.club, 'join_test') or not self.club.join_test.is_active:
            return False
        return self.attempts_count < self.club.join_test.max_attempts

    def get_current_attempt(self):
        """Получить текущую попытку прохождения теста"""
        return JoinTestAttempt.objects.filter(
            user=self.user,
            test=self.club.join_test,
            status='in_progress'
        ).first()

    class Meta:
        verbose_name = "Club Member"
        verbose_name_plural = "Club Members"
        db_table = 'club_members'
        unique_together = ('user', 'club')

    def __str__(self):
        return f"{self.user.full_name} - {self.club.name} ({self.role})"


class ClubEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ('meeting', 'Meeting'),
        ('workshop', 'Workshop'),
        ('competition', 'Competition'),
        ('audition', 'Audition/Casting'),
        ('performance', 'Performance'),
        ('training', 'Training'),
        ('other', 'Other'),
    )

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)

    # Registration info
    registration_required = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    max_participants = models.PositiveIntegerField(default=0, help_text="0 means no limit")
    current_participants = models.PositiveIntegerField(default=0)

    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Club Event"
        verbose_name_plural = "Club Events"
        db_table = 'club_events'
        ordering = ['-start_date']


class EventRegistration(models.Model):
    STATUS_CHOICES = (
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled'),
        ('waitlisted', 'Waitlisted'),
    )

    event = models.ForeignKey(ClubEvent, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey('authorization.User', on_delete=models.CASCADE, related_name='event_registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        db_table = 'event_registrations'
        unique_together = ('event', 'user')

    def __str__(self):
        return f"{self.user.mobile_phone} - {self.event.title}"


class ClubApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('more_info', 'More Information Needed'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(ClubCategory, on_delete=models.CASCADE)

    # Founder information
    founder = models.ForeignKey('authorization.User', on_delete=models.CASCADE, related_name='club_applications')
    founder_faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    founder_year = models.PositiveSmallIntegerField()
    founder_motivation = models.TextField()

    # Club plan
    goals = models.TextField()
    activities = models.TextField()
    meeting_frequency = models.CharField(max_length=100)

    # Requirements
    min_members = models.PositiveSmallIntegerField(default=5)
    faculty_advisor = models.CharField(max_length=100, blank=True)

    # Logo and supporting documents
    logo = models.ImageField(upload_to='club_applications/logos/', blank=True, null=True)
    supporting_document = models.FileField(upload_to='club_applications/documents/', blank=True, null=True)

    # Application status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.founder.mobile_phone} ({self.status})"

    class Meta:
        verbose_name = "Club Application"
        verbose_name_plural = "Club Applications"
        db_table = 'club_applications'
        ordering = ['-created_at']


class ClubResource(models.Model):
    RESOURCE_TYPE_CHOICES = (
        ('document', 'Document'),
        ('video', 'Video Tutorial'),
        ('presentation', 'Presentation'),
        ('link', 'External Link'),
        ('other', 'Other'),
    )

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)

    # Content - either file or link
    file = models.FileField(upload_to='club_resources/', blank=True, null=True)
    link = models.URLField(blank=True, null=True)

    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey('authorization.User', on_delete=models.SET_NULL, null=True, related_name='uploaded_resources')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Club Resource"
        verbose_name_plural = "Club Resources"
        db_table = 'club_resources'
        ordering = ['-created_at']


class ClubNews(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='news')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='club_news/', blank=True, null=True)

    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey('authorization.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Club News"
        verbose_name_plural = "Club News"
        db_table = 'club_news'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Donation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='donations')
    user = models.ForeignKey('authorization.User', on_delete=models.CASCADE, related_name='donations', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)

    # For anonymous donations
    donor_name = models.CharField(max_length=100, blank=True)
    donor_email = models.EmailField(blank=True)

    is_anonymous = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous - {self.club.name} ({self.amount})"
        elif self.user:
            return f"{self.user.mobile_phone} - {self.club.name} ({self.amount})"
        else:
            return f"{self.donor_name} - {self.club.name} ({self.amount})"

    class Meta:
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        db_table = 'donations'
        ordering = ['-created_at']


class JoinTest(models.Model):
    """Тест для вступления в клуб"""
    club = models.OneToOneField(Club, on_delete=models.CASCADE, related_name='join_test')
    title = models.CharField(max_length=200, default="Тест для вступления")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    passing_score = models.IntegerField(default=70, help_text="Минимальный балл для прохождения (%)")
    time_limit = models.IntegerField(default=30, help_text="Ограничение по времени (минуты)")
    max_attempts = models.IntegerField(default=3, help_text="Максимальное количество попыток")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Тест для {self.club.name}"

    class Meta:
        verbose_name = "Тест для вступления"
        verbose_name_plural = "Тесты для вступления"
        db_table = 'join_tests'


class JoinTestQuestion(models.Model):
    """Вопрос теста для вступления"""
    QUESTION_TYPES = (
        ('single', 'Один правильный ответ'),
        ('multiple', 'Несколько правильных ответов'),
        ('text', 'Текстовый ответ'),
    )

    test = models.ForeignKey(JoinTest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single')
    points = models.IntegerField(default=1, help_text="Баллы за правильный ответ")
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Вопрос {self.order}: {self.question_text[:50]}..."

    class Meta:
        verbose_name = "Вопрос теста"
        verbose_name_plural = "Вопросы теста"
        db_table = 'join_test_questions'
        ordering = ['order']


class JoinTestAnswer(models.Model):
    """Варианты ответов на вопросы теста"""
    question = models.ForeignKey(JoinTestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Ответ: {self.answer_text[:30]}..."

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"
        db_table = 'join_test_answers'
        ordering = ['order']


class JoinTestAttempt(models.Model):
    """Попытка прохождения теста"""
    STATUS_CHOICES = (
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('failed', 'Провалена'),
        ('passed', 'Пройдена'),
        ('expired', 'Время истекло'),
    )

    user = models.ForeignKey('authorization.User', on_delete=models.CASCADE, related_name='join_test_attempts')
    test = models.ForeignKey(JoinTest, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.FloatField(null=True, blank=True, help_text="Результат в процентах")
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.IntegerField(null=True, blank=True, help_text="Время в секундах")

    def is_expired(self):
        if self.status != 'in_progress':
            return False
        time_limit_seconds = self.test.time_limit * 60
        return (timezone.now() - self.started_at).seconds > time_limit_seconds

    def calculate_score(self):
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100

    def is_passed(self):
        return self.score and self.score >= self.test.passing_score

    def __str__(self):
        return f"{self.user.full_name} - {self.test.club.name} ({self.status})"

    class Meta:
        verbose_name = "Попытка теста"
        verbose_name_plural = "Попытки тестов"
        db_table = 'join_test_attempts'
        ordering = ['-started_at']


class JoinTestUserAnswer(models.Model):
    """Ответы пользователя на вопросы теста"""
    attempt = models.ForeignKey(JoinTestAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(JoinTestQuestion, on_delete=models.CASCADE)
    selected_answers = models.ManyToManyField(JoinTestAnswer, blank=True)
    text_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ответ на вопрос {self.question.order}"

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"
        db_table = 'join_test_user_answers'
