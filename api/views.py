from django.shortcuts import render


def _page(request, template_name, title, description, **extra):
    context = {
        'page_title': title,
        'page_description': description,
        **extra,
    }
    return render(request, template_name, context)


def login_view(request):
    return _page(request, 'pages/login.html', 'Вход в систему', 'Авторизация пользователей по ролям.')


def dashboard_view(request):
    stats = [
        {'label': 'Активные проекты', 'value': 12},
        {'label': 'Свободные специалисты', 'value': 18},
        {'label': 'Ожидают назначения', 'value': 7},
        {'label': 'Средняя загрузка', 'value': '74%'},
    ]
    return _page(request, 'pages/dashboard.html', 'Дашборд', 'Общий обзор системы.', stats=stats)


def specialists_list_view(request):
    specialists = [
        {'name': 'Анна Смирнова', 'role': 'Frontend Developer', 'stack': 'React, TypeScript, CSS', 'load': '60%'},
        {'name': 'Илья Петров', 'role': 'Backend Developer', 'stack': 'Python, Django, PostgreSQL', 'load': '80%'},
        {'name': 'Мария Орлова', 'role': 'QA Engineer', 'stack': 'Postman, Pytest, Selenium', 'load': '40%'},
    ]
    return _page(request, 'pages/specialists_list.html', 'Специалисты', 'Список всех специалистов и фильтры.', specialists=specialists)


def specialist_detail_view(request, pk=1):
    specialist = {
        'id': pk,
        'name': 'Анна Смирнова',
        'role': 'Frontend Developer',
        'seniority': 'Middle+',
        'experience': '4 года',
        'load': '60%',
        'skills': ['React', 'TypeScript', 'HTML', 'CSS', 'Figma'],
        'projects': ['Neo Staffing Platform', 'Retail Portal'],
    }
    return _page(request, 'pages/specialist_detail.html', 'Карточка специалиста', 'Детальная информация о специалисте.', specialist=specialist)


def specialist_edit_view(request, pk=1):
    return _page(request, 'pages/specialist_edit.html', 'Редактирование специалиста', 'Изменение профиля, навыков и доступности.', specialist_id=pk)


def projects_list_view(request):
    projects = [
        {'name': 'Neo Staffing Platform', 'status': 'В работе', 'manager': 'Егор Ковалёв', 'dates': '01.03 — 30.06'},
        {'name': 'Fintech Core Upgrade', 'status': 'Не начат', 'manager': 'Анна Лебедева', 'dates': '10.04 — 31.08'},
        {'name': 'Mobile Sales App', 'status': 'Завершён', 'manager': 'Марина Фролова', 'dates': '15.01 — 15.03'},
    ]
    return _page(request, 'pages/projects_list.html', 'Проекты', 'Список проектов компании.', projects=projects)


def project_detail_view(request, pk=1):
    project = {
        'id': pk,
        'name': 'Neo Staffing Platform',
        'status': 'В работе',
        'manager': 'Егор Ковалёв',
        'budget': '4 500 000 ₽',
        'period': '01.03.2026 — 30.06.2026',
        'team': ['Анна Смирнова', 'Илья Петров', 'Мария Орлова'],
    }
    return _page(request, 'pages/project_detail.html', 'Карточка проекта', 'Подробная информация о проекте.', project=project)


def project_edit_view(request, pk=None):
    mode = 'Создание проекта' if pk is None else 'Редактирование проекта'
    description = 'Форма создания нового проекта.' if pk is None else 'Форма редактирования проекта.'
    return _page(request, 'pages/project_edit.html', mode, description, project_id=pk)


def project_roles_view(request, pk=1):
    roles = [
        {'title': 'Frontend Developer', 'count': 2, 'must_have': 'React, TypeScript', 'status': 'Открыта'},
        {'title': 'Backend Developer', 'count': 1, 'must_have': 'Python, Django, PostgreSQL', 'status': 'Закрыта'},
    ]
    return _page(request, 'pages/project_roles.html', 'Роли и требования проекта', 'Настройка ролей, количества специалистов и навыков.', project_id=pk, roles=roles)


def recommendations_view(request, role_id=1):
    recommendations = [
        {'name': 'Анна Смирнова', 'score': '94%', 'reason': 'Совпадают React, TypeScript, доступна на 40%'},
        {'name': 'Олег Ким', 'score': '87%', 'reason': 'Сильный стек, но загрузка 70%'},
        {'name': 'София Романова', 'score': '81%', 'reason': 'Есть нужный стек, нужен онбординг по домену'},
    ]
    return _page(request, 'pages/recommendations.html', 'Рекомендации кандидатов', 'Подбор специалистов под конкретную роль.', role_id=role_id, recommendations=recommendations)


def assignments_view(request):
    assignments = [
        {'specialist': 'Анна Смирнова', 'project': 'Neo Staffing Platform', 'role': 'Frontend Developer', 'status': 'Active', 'load': '60%'},
        {'specialist': 'Илья Петров', 'project': 'Fintech Core Upgrade', 'role': 'Backend Developer', 'status': 'Pending', 'load': '100%'},
        {'specialist': 'Мария Орлова', 'project': 'Neo Staffing Platform', 'role': 'QA Engineer', 'status': 'Accepted', 'load': '40%'},
    ]
    return _page(request, 'pages/assignments.html', 'Назначения', 'Управление назначениями специалистов на проекты.', assignments=assignments)


def workload_view(request):
    workload = [
        {'name': 'Анна Смирнова', 'current': '60%', 'free_from': '15.05.2026'},
        {'name': 'Илья Петров', 'current': '100%', 'free_from': '01.07.2026'},
        {'name': 'Мария Орлова', 'current': '40%', 'free_from': 'Уже доступна'},
    ]
    return _page(request, 'pages/workload.html', 'Загрузка специалистов', 'Календарь занятости и доступности.', workload=workload)


def feedback_view(request):
    feedback_items = [
        {'author': 'ООО ФинТех', 'target': 'Илья Петров', 'rating': '5/5', 'comment': 'Отлично справился с критичным релизом.'},
        {'author': 'Егор Ковалёв', 'target': 'Анна Смирнова', 'rating': '4/5', 'comment': 'Сильный фронтенд, быстро влилась в проект.'},
    ]
    return _page(request, 'pages/feedback.html', 'Отзывы и обратная связь', 'Сбор и просмотр отзывов по проектам и специалистам.', feedback_items=feedback_items)


def analytics_view(request):
    metrics = [
        {'label': 'Среднее время закрытия роли', 'value': '3.2 дня'},
        {'label': 'Процент успешных назначений', 'value': '89%'},
        {'label': 'Средняя оценка клиентов', 'value': '4.7/5'},
        {'label': 'Проекты в риске перегрузки', 'value': '2'},
    ]
    return _page(request, 'pages/analytics.html', 'Аналитика и отчёты', 'Сводные отчёты и метрики по системе.', metrics=metrics)


def profile_view(request):
    profile = {
        'name': 'Костя Иванов',
        'role': 'Frontend Developer',
        'email': 'kostya@example.com',
        'phone': '+7 (999) 000-00-00',
    }
    return _page(request, 'pages/profile.html', 'Профиль пользователя', 'Личные данные текущего пользователя.', profile=profile)
