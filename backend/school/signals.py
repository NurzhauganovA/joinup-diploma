from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings

from .models import ClubApplication, Club, ClubMember, School, ClubMemberContract, JoinTestAttempt


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


@receiver(post_save, sender=JoinTestAttempt)
def update_membership_after_test(sender, instance, created, **kwargs):
    """Обновляем статус членства после завершения теста"""
    if instance.status in ['passed', 'failed', 'expired'] and instance.user:
        try:
            # Находим соответствующее членство
            membership = ClubMember.objects.get(
                user=instance.user,
                club=instance.test.club,
                test_attempt=instance
            )

            if instance.status == 'passed':
                # Тест пройден - переводим в статус ожидания одобрения
                membership.status = 'pending'
                membership.save()

                print(f"✅ Пользователь {instance.user.full_name} прошел тест для клуба {instance.test.club.name}")

            else:
                # Тест не пройден
                membership.status = 'test_failed'
                membership.save()

                print(f"❌ Пользователь {instance.user.full_name} не прошел тест для клуба {instance.test.club.name}")

        except ClubMember.DoesNotExist:
            print(
                f"⚠️ Не найдено членство для пользователя {instance.user.full_name} в клубе {instance.test.club.name}")
        except Exception as e:
            print(f"❌ Ошибка при обновлении статуса членства: {e}")


# Автоматическое создание контракта при одобрении заявки
# @receiver(post_save, sender=ClubMember)
# def create_contract_on_approval(sender, instance, created, **kwargs):
#     """Создаем контракт при одобрении заявки"""
#     # Проверяем, что статус изменился на 'approved' и есть шаблон контракта
#     if (instance.status == 'approved' and
#             hasattr(instance.club, 'contract_template') and
#             instance.club.contract_template.is_active):
#
#         # Создаем контракт для подписания, если его еще нет
#         contract, contract_created = ClubMemberContract.objects.get_or_create(
#             member=instance,
#             contract_template=instance.club.contract_template,
#             defaults={'status': 'pending'}
#         )
#
#         if contract_created:
#             print(f"📄 Создан контракт для {instance.user.full_name} в клубе {instance.club.name}")
#
#         # Обновляем статус на ожидание контракта
#         if instance.status != 'contract_pending':
#             instance.status = 'contract_pending'
#             instance.save()


# Автоматическая активация участника после подписания контракта
@receiver(post_save, sender=ClubMemberContract)
def activate_member_on_contract_sign(sender, instance, created, **kwargs):
    """Активируем участника после подписания контракта"""
    if instance.status == 'signed' and instance.member.status != 'active':
        try:
            with transaction.atomic():
                # Активируем участника
                instance.member.status = 'active'
                instance.member.save()

                # Обновляем счетчик участников клуба
                club = instance.member.club
                club.members_count = ClubMember.objects.filter(
                    club=club, status='active'
                ).count()
                club.save()

                print(f"🎉 Пользователь {instance.member.user.full_name} активирован в клубе {club.name}")

                # Отправляем уведомление о вступлении (опционально)
                try:
                    send_welcome_notification(instance.member)
                except Exception as e:
                    print(f"⚠️ Ошибка при отправке уведомления: {e}")

        except Exception as e:
            print(f"❌ Ошибка при активации участника: {e}")


def send_welcome_notification(member):
    """Отправляем приветственное уведомление новому участнику"""
    try:
        subject = f'🎉 Добро пожаловать в клуб "{member.club.name}"!'

        message = f"""
Поздравляем!

Вы успешно вступили в клуб "{member.club.name}".

Теперь вы можете:
✓ Участвовать во всех мероприятиях клуба
✓ Получать доступ к эксклюзивным ресурсам
✓ Общаться с единомышленниками
✓ Развивать свои навыки и интересы

Добро пожаловать в наше сообщество!

Ссылка на клуб: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/panel/club/{member.club.slug}/

С уважением,
Команда JoinUP
        """.strip()

        # Отправка email (если настроен)
        if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                  'DEFAULT_FROM_EMAIL') else 'noreply@sdu.edu.kz',
                recipient_list=[member.user.email] if hasattr(member.user, 'email') else [],
                fail_silently=True
            )

    except Exception as e:
        print(f"Ошибка при отправке приветственного уведомления: {e}")


# Очистка истекших контрактов
@receiver(post_save, sender=ClubMemberContract)
def cleanup_expired_contracts(sender, instance, **kwargs):
    """Очистка истекших контрактов"""
    if instance.status == 'expired':
        try:
            # Обновляем статус участника
            if instance.member.status in ['approved', 'contract_pending']:
                instance.member.status = 'rejected'
                instance.member.rejection_reason = 'Контракт не был подписан в установленные сроки'
                instance.member.save()

                print(f"⏰ Контракт для {instance.member.user.full_name} истек")

        except Exception as e:
            print(f"❌ Ошибка при обработке истекшего контракта: {e}")


# Валидация подписи контракта
def validate_digital_signature(signature_data):
    """Валидация данных ЭЦП"""
    try:
        required_fields = ['full_name', 'iin', 'valid_from', 'valid_to', 'issuer', 'serial_number']

        for field in required_fields:
            if not signature_data.get(field):
                return False, f"Отсутствует поле: {field}"

        # Проверка срока действия сертификата
        from datetime import datetime
        valid_to = datetime.strptime(signature_data['valid_to'], '%Y-%m-%d').date()
        if valid_to < timezone.now().date():
            return False, "Срок действия сертификата истек"

        # Проверка ИИН (12 цифр)
        iin = signature_data.get('iin', '')
        if not iin.isdigit() or len(iin) != 12:
            return False, "Некорректный ИИН"

        return True, "Подпись валидна"

    except Exception as e:
        return False, f"Ошибка валидации: {str(e)}"


# Логирование активности для аудита
@receiver(post_save, sender=ClubMember)
def log_membership_changes(sender, instance, created, **kwargs):
    """Логирование изменений в членстве для аудита"""
    try:
        if created:
            action = "Создана заявка"
        else:
            action = f"Статус изменен на: {instance.get_status_display()}"

        # Здесь можно добавить логирование в файл или базу данных
        print(f"📋 АУДИТ: {action} для {instance.user.full_name} в клубе {instance.club.name}")

    except Exception as e:
        print(f"❌ Ошибка логирования: {e}")


@receiver(post_save, sender=ClubMemberContract)
def log_contract_changes(sender, instance, created, **kwargs):
    """Логирование изменений в контрактах для аудита"""
    try:
        if created:
            action = "Создан контракт"
        else:
            action = f"Контракт: {instance.get_status_display()}"

        print(f"📋 АУДИТ: {action} для {instance.member.user.full_name} в клубе {instance.member.club.name}")

    except Exception as e:
        print(f"❌ Ошибка логирования контракта: {e}")


@receiver(post_save, sender=ClubMemberContract)
def generate_qr_code_on_sign(sender, instance, created, **kwargs):
    """Генерирует QR код при подписании контракта"""
    if instance.status == 'signed' and not instance.qr_code:
        try:
            # Получаем request из threadlocal или используем базовый URL
            instance.generate_qr_code()
            instance.save(update_fields=['qr_code', 'verification_url'])
            print(f"✅ QR код сгенерирован для контракта #{instance.id}")
        except Exception as e:
            print(f"❌ Ошибка при генерации QR кода для контракта #{instance.id}: {e}")