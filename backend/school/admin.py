from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from school.models import *

admin.site.register(School)
admin.site.register(SchoolRequisites)
admin.site.register(Class)
admin.site.register(Faculty)
admin.site.register(ClubCategory)
admin.site.register(Club)
admin.site.register(ClubMember)
admin.site.register(ClubEvent)
admin.site.register(EventRegistration)
admin.site.register(ClubResource)
admin.site.register(ClubNews)
admin.site.register(Donation)
admin.site.register(JoinTest)
admin.site.register(JoinTestQuestion)
admin.site.register(JoinTestAnswer)
admin.site.register(JoinTestAttempt)
admin.site.register(JoinTestUserAnswer)

# Добавьте это в school/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ClubApplication, Club


@admin.register(ClubApplication)
class ClubApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'founder_display',
        'category',
        'status_display',
        'created_at',
        'founder_faculty',
        'actions_display'
    ]

    list_filter = [
        'status',
        'category',
        'founder_faculty',
        'created_at'
    ]

    search_fields = [
        'name',
        'founder__first_name',
        'founder__last_name',
        'founder__mobile_phone',
        'description'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'founder_info_display',
        'application_preview'
    ]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'category', 'status')
        }),
        ('Информация об основателе', {
            'fields': (
                'founder_info_display',
                'founder_faculty',
                'founder_year',
                'founder_motivation'
            )
        }),
        ('План клуба', {
            'fields': ('goals', 'activities', 'meeting_frequency', 'min_members')
        }),
        ('Дополнительная информация', {
            'fields': ('faculty_advisor', 'logo', 'supporting_document')
        }),
        ('Администрирование', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Предварительный просмотр', {
            'fields': ('application_preview',),
            'classes': ('collapse',)
        })
    )

    actions = ['approve_applications', 'reject_applications']

    def founder_display(self, obj):
        """Отображение основателя"""
        return f"{obj.founder.full_name} ({obj.founder.mobile_phone})"

    founder_display.short_description = 'Основатель'

    def status_display(self, obj):
        """Цветное отображение статуса"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'more_info': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Статус'

    def actions_display(self, obj):
        """Быстрые действия"""
        buttons = []

        if obj.status == 'pending':
            # Кнопка одобрения
            approve_url = f"javascript:if(confirm('Одобрить заявку \"{obj.name}\"? Клуб будет создан автоматически.')){{ location.href='/admin/school/clubapplication/{obj.id}/change/?approve=1'; }}"
            buttons.append(
                f'<a href="{approve_url}" style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; text-decoration: none; font-size: 11px;">✓ Одобрить</a>')

            # Кнопка отклонения
            reject_url = f"javascript:if(confirm('Отклонить заявку \"{obj.name}\"?')){{ location.href='/admin/school/clubapplication/{obj.id}/change/?reject=1'; }}"
            buttons.append(
                f'<a href="{reject_url}" style="background: #dc3545; color: white; padding: 2px 8px; border-radius: 3px; text-decoration: none; font-size: 11px;">✗ Отклонить</a>')

        elif obj.status == 'approved':
            # Проверяем, создан ли клуб
            try:
                club = Club.objects.get(name=obj.name)
                club_url = reverse('admin:school_club_change', args=[club.id])
                buttons.append(
                    f'<a href="{club_url}" style="background: #007bff; color: white; padding: 2px 8px; border-radius: 3px; text-decoration: none; font-size: 11px;">Клуб →</a>')
            except Club.DoesNotExist:
                buttons.append('<span style="color: #dc3545; font-size: 11px;">Клуб не найден</span>')

        return mark_safe(' '.join(buttons))

    actions_display.short_description = 'Действия'

    def founder_info_display(self, obj):
        """Подробная информация об основателе"""
        info = f"""
        <strong>Имя:</strong> {obj.founder.full_name}<br>
        <strong>Телефон:</strong> {obj.founder.mobile_phone}<br>
        <strong>Email:</strong> {getattr(obj.founder, 'email', 'Не указан')}<br>
        <strong>Факультет:</strong> {obj.founder_faculty}<br>
        <strong>Курс:</strong> {obj.founder_year}<br>
        """
        return mark_safe(info)

    founder_info_display.short_description = 'Информация об основателе'

    def application_preview(self, obj):
        """Предварительный просмотр заявки"""
        preview = f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
            <h3 style="margin-top: 0; color: #333;">{obj.name}</h3>
            <p><strong>Категория:</strong> {obj.category}</p>
            <p><strong>Описание:</strong> {obj.description[:200]}{'...' if len(obj.description) > 200 else ''}</p>

            <details>
                <summary style="cursor: pointer; font-weight: bold;">Цели клуба</summary>
                <p style="margin-left: 20px;">{obj.goals}</p>
            </details>

            <details>
                <summary style="cursor: pointer; font-weight: bold;">Планируемые активности</summary>
                <p style="margin-left: 20px;">{obj.activities}</p>
            </details>

            <details>
                <summary style="cursor: pointer; font-weight: bold;">Мотивация основателя</summary>
                <p style="margin-left: 20px;">{obj.founder_motivation}</p>
            </details>

            <p><strong>Частота встреч:</strong> {obj.meeting_frequency}</p>
            <p><strong>Минимум участников:</strong> {obj.min_members}</p>
            {f'<p><strong>Научный руководитель:</strong> {obj.faculty_advisor}</p>' if obj.faculty_advisor else ''}
        </div>
        """
        return mark_safe(preview)

    application_preview.short_description = 'Предварительный просмотр'

    def approve_applications(self, request, queryset):
        """Массовое одобрение заявок"""
        approved_count = 0
        for application in queryset.filter(status='pending'):
            application.status = 'approved'
            application.save()  # Триггерит signal
            approved_count += 1

        self.message_user(
            request,
            f'Одобрено {approved_count} заявок. Клубы будут созданы автоматически.'
        )

    approve_applications.short_description = 'Одобрить выбранные заявки'

    def reject_applications(self, request, queryset):
        """Массовое отклонение заявок"""
        rejected_count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'Отклонено {rejected_count} заявок.')

    reject_applications.short_description = 'Отклонить выбранные заявки'

    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для обработки статуса"""
        # Сначала сохраняем объект
        super().save_model(request, obj, form, change)

        # Добавляем сообщение в зависимости от статуса
        if change and obj.status == 'approved':
            self.message_user(
                request,
                f'Заявка "{obj.name}" одобрена. Клуб будет создан автоматически.',
                level='SUCCESS'
            )
        elif change and obj.status == 'rejected':
            self.message_user(
                request,
                f'Заявка "{obj.name}" отклонена.',
                level='WARNING'
            )