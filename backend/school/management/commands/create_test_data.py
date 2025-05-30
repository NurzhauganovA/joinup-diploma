from django.core.management.base import BaseCommand
from school.models import (
    Club, ClubCategory, Faculty, JoinTest, JoinTestQuestion, JoinTestAnswer, School
)


class Command(BaseCommand):
    help = 'Создает тестовые данные для системы тестирования клубов'

    def handle(self, *args, **options):
        # Создаем категории клубов если их нет
        tech_category, created = ClubCategory.objects.get_or_create(
            name='Технологии',
            defaults={'description': 'Клубы связанные с технологиями и программированием'}
        )

        sport_category, created = ClubCategory.objects.get_or_create(
            name='Спорт',
            defaults={'description': 'Спортивные клубы и активности'}
        )

        # Создаем факультеты если их нет
        cs_faculty, created = Faculty.objects.get_or_create(
            name='Computer Science',
            defaults={'abbreviation': 'CS'}
        )

        math_faculty, created = Faculty.objects.get_or_create(
            name='Mathematics',
            defaults={'abbreviation': 'MATH'}
        )

        # Создаем клуб программирования с тестом
        programming_club, created = Club.objects.get_or_create(
            school=School.objects.first(),  # Предполагаем, что школа уже создана
            name='Programming Club',
            defaults={
                'slug': 'programming-club',
                'description': 'Клуб для изучения программирования и разработки проектов',
                'short_description': 'Изучаем программирование вместе',
                'establishment_date': '2024-01-01',
                'category': tech_category,
                'status': 'active',
                'email': 'programming@sdu.edu.kz',
                'accepting_members': True,
            }
        )

        if created:
            programming_club.associated_faculties.add(cs_faculty, math_faculty)

        # Создаем тест для клуба программирования
        programming_test, created = JoinTest.objects.get_or_create(
            club=programming_club,
            defaults={
                'title': 'Тест для вступления в Programming Club',
                'description': 'Базовые знания программирования и логики',
                'is_active': True,
                'passing_score': 70,
                'time_limit': 15,  # 15 минут
                'max_attempts': 3,
            }
        )

        if created:
            # Создаем вопросы для теста
            # Вопрос 1 - одиночный выбор
            q1 = JoinTestQuestion.objects.create(
                test=programming_test,
                question_text='Что такое переменная в программировании?',
                question_type='single',
                points=10,
                order=1,
                is_required=True
            )

            JoinTestAnswer.objects.create(
                question=q1,
                answer_text='Область памяти для хранения данных',
                is_correct=True,
                order=1
            )
            JoinTestAnswer.objects.create(
                question=q1,
                answer_text='Функция для вывода данных',
                is_correct=False,
                order=2
            )
            JoinTestAnswer.objects.create(
                question=q1,
                answer_text='Тип данных',
                is_correct=False,
                order=3
            )
            JoinTestAnswer.objects.create(
                question=q1,
                answer_text='Команда компилятора',
                is_correct=False,
                order=4
            )

            # Вопрос 2 - множественный выбор
            q2 = JoinTestQuestion.objects.create(
                test=programming_test,
                question_text='Какие из следующих языков являются объектно-ориентированными?',
                question_type='multiple',
                points=15,
                order=2,
                is_required=True
            )

            JoinTestAnswer.objects.create(
                question=q2,
                answer_text='Java',
                is_correct=True,
                order=1
            )
            JoinTestAnswer.objects.create(
                question=q2,
                answer_text='Python',
                is_correct=True,
                order=2
            )
            JoinTestAnswer.objects.create(
                question=q2,
                answer_text='C',
                is_correct=False,
                order=3
            )
            JoinTestAnswer.objects.create(
                question=q2,
                answer_text='JavaScript',
                is_correct=True,
                order=4
            )

            # Вопрос 3 - текстовый
            q3 = JoinTestQuestion.objects.create(
                test=programming_test,
                question_text='Объясните своими словами, что такое алгоритм?',
                question_type='text',
                points=25,
                order=3,
                is_required=True
            )

            # Вопрос 4 - одиночный выбор
            q4 = JoinTestQuestion.objects.create(
                test=programming_test,
                question_text='Какая временная сложность у алгоритма линейного поиска?',
                question_type='single',
                points=20,
                order=4,
                is_required=True
            )

            JoinTestAnswer.objects.create(
                question=q4,
                answer_text='O(1)',
                is_correct=False,
                order=1
            )
            JoinTestAnswer.objects.create(
                question=q4,
                answer_text='O(n)',
                is_correct=True,
                order=2
            )
            JoinTestAnswer.objects.create(
                question=q4,
                answer_text='O(log n)',
                is_correct=False,
                order=3
            )
            JoinTestAnswer.objects.create(
                question=q4,
                answer_text='O(n²)',
                is_correct=False,
                order=4
            )

            # Вопрос 5 - одиночный выбор
            q5 = JoinTestQuestion.objects.create(
                test=programming_test,
                question_text='Что выведет код: print(2 + 3 * 4)?',
                question_type='single',
                points=10,
                order=5,
                is_required=True
            )

            JoinTestAnswer.objects.create(
                question=q5,
                answer_text='20',
                is_correct=False,
                order=1
            )
            JoinTestAnswer.objects.create(
                question=q5,
                answer_text='14',
                is_correct=True,
                order=2
            )
            JoinTestAnswer.objects.create(
                question=q5,
                answer_text='234',
                is_correct=False,
                order=3
            )
            JoinTestAnswer.objects.create(
                question=q5,
                answer_text='Ошибка',
                is_correct=False,
                order=4
            )

        # Создаем второй клуб без теста для демонстрации
        chess_club, created = Club.objects.get_or_create(
            school=School.objects.first(),  # Предполагаем, что школа уже создана
            name='Chess Club',
            defaults={
                'slug': 'chess-club',
                'description': 'Клуб любителей шахмат. Играем, учимся, участвуем в турнирах',
                'short_description': 'Шахматный клуб для всех уровней',
                'establishment_date': '2024-02-01',
                'category': sport_category,
                'status': 'active',
                'email': 'chess@sdu.edu.kz',
                'accepting_members': True,
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно созданы тестовые данные:\n'
                f'- Клуб: {programming_club.name} (с тестом из {programming_test.questions.count()} вопросов)\n'
                f'- Клуб: {chess_club.name} (без теста)\n'
                f'- Категории: {ClubCategory.objects.count()}\n'
                f'- Факультеты: {Faculty.objects.count()}'
            )
        )