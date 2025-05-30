from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings

from .models import ClubApplication, Club, ClubMember, School


@receiver(pre_save, sender=ClubApplication)
def track_application_status_change(sender, instance, **kwargs):
    """Отслеживаем изменение статуса заявки"""
    if instance.pk:
        try:
            old_instance = ClubApplication.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except ClubApplication.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=ClubApplication)
@transaction.atomic
def handle_club_application_approval(sender, instance, created, **kwargs):
    """Обрабатываем одобрение заявки на создание клуба"""

    # Проверяем, что статус изменился на 'approved'
    old_status = getattr(instance, '_old_status', None)

    if instance.status == 'approved' and old_status != 'approved':
        try:
            # Проверяем, не существует ли уже клуб с таким именем
            if Club.objects.filter(name=instance.name).exists():
                print(f"Клуб с именем '{instance.name}' уже существует")
                return

            # Создаем уникальный slug
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Club.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Создаем клуб на основе заявки
            club = Club.objects.create(
                school=School.objects.first(),  # Предполагаем, что школа уже создана
                name=instance.name,
                slug=slug,
                description=instance.description,
                short_description=instance.description[:200] if len(
                    instance.description) > 200 else instance.description,
                establishment_date=instance.created_at.date(),
                category=instance.category,
                status='active',  # Сразу делаем активным

                # Контактная информация
                email=instance.founder.email if hasattr(instance.founder, 'email') else f"{slug}@sdu.edu.kz",
                phone=getattr(instance.founder, 'mobile_phone', ''),

                # Настройки клуба
                accepting_members=True,
                members_limit=0,  # Без лимита
                is_featured=False,
            )

            # Добавляем логотип если есть
            if instance.logo:
                club.logo = instance.logo
                club.save()

            # Связываем с факультетом основателя
            if instance.founder_faculty:
                club.associated_faculties.add(instance.founder_faculty)

            # Создаем основателя как участника клуба с ролью 'founder'
            ClubMember.objects.create(
                user=instance.founder,
                club=club,
                role='founder',
                status='active',
                faculty=instance.founder_faculty,
                bio=f"Основатель клуба. {instance.founder_motivation}",
                academic_year=instance.founder_year,
                is_public=True
            )

            # Обновляем счетчик участников
            club.members_count = 1
            club.save()

            print(f"✅ Клуб '{club.name}' успешно создан из заявки #{instance.id}")

            # Отправляем уведомление основателю (опционально)
            try:
                send_notification_to_founder(instance, club)
            except Exception as e:
                print(f"Ошибка при отправке уведомления: {e}")

        except Exception as e:
            print(f"❌ Ошибка при создании клуба из заявки #{instance.id}: {e}")
            # Можно также логировать в файл или отправить в систему мониторинга


def send_notification_to_founder(application, club):
    """Отправляем уведомление основателю о создании клуба"""
    try:
        subject = f'🎉 Ваш клуб "{club.name}" одобрен!'

        message = f"""
Поздравляем!

Ваша заявка на создание клуба "{club.name}" была одобрена администрацией.

Детали клуба:
• Название: {club.name}
• Категория: {club.category.name}
• Статус: Активен
• Ссылка: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/panel/club/{club.slug}/

Вы автоматически назначены основателем клуба. Теперь вы можете:
✓ Управлять участниками
✓ Создавать мероприятия  
✓ Публиковать новости
✓ Загружать ресурсы

Желаем успехов в развитии вашего клуба!

С уважением,
Команда JoinUP
        """.strip()

        # Попытка отправки email (если настроен)
        if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                  'DEFAULT_FROM_EMAIL') else 'noreply@sdu.edu.kz',
                recipient_list=[application.founder.email] if hasattr(application.founder, 'email') else [],
                fail_silently=True
            )
            print(f"📧 Уведомление отправлено на {application.founder.email}")
        else:
            print("📧 Email не настроен, уведомление не отправлено")

    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")


@receiver(post_save, sender=ClubApplication)
def handle_club_application_rejection(sender, instance, created, **kwargs):
    """Обрабатываем отклонение заявки"""

    old_status = getattr(instance, '_old_status', None)

    if instance.status == 'rejected' and old_status != 'rejected':
        try:
            # Уведомляем основателя об отклонении (опционально)
            subject = f'Заявка на клуб "{instance.name}" отклонена'

            message = f"""
К сожалению, ваша заявка на создание клуба "{instance.name}" была отклонена.

Причина: {instance.admin_notes if instance.admin_notes else 'Не указана'}

Вы можете подать новую заявку, учтив замечания администрации.

С уважением,
Команда JoinUP
            """.strip()

            if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                      'DEFAULT_FROM_EMAIL') else 'noreply@sdu.edu.kz',
                    recipient_list=[instance.founder.email] if hasattr(instance.founder, 'email') else [],
                    fail_silently=True
                )

            print(f"📧 Уведомление об отклонении отправлено для заявки #{instance.id}")

        except Exception as e:
            print(f"Ошибка при обработке отклонения заявки: {e}")


# Дополнительный signal для обновления счетчика участников при изменении ClubMember
@receiver(post_save, sender=ClubMember)
def update_club_members_count_on_save(sender, instance, created, **kwargs):
    """Обновляем счетчик участников при добавлении/изменении участника"""
    if instance.status == 'active':
        active_members_count = ClubMember.objects.filter(
            club=instance.club,
            status='active'
        ).count()

        instance.club.members_count = active_members_count
        instance.club.save(update_fields=['members_count'])


@receiver(post_save, sender=ClubMember)
def update_club_members_count_on_delete(sender, instance, **kwargs):
    """Обновляем счетчик участников при удалении участника"""
    try:
        active_members_count = ClubMember.objects.filter(
            club=instance.club,
            status='active'
        ).count()

        instance.club.members_count = active_members_count
        instance.club.save(update_fields=['members_count'])
    except:
        pass  # Клуб мог быть удален