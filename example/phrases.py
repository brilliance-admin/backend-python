RU_ADMIN_DESCRIPTION = '''
Используется для демонстрации возможностей админ панели.<br>
<br>
Данные и действия в этом режиме не влияют на рабочее окружение и периодически сбрасываются.
'''
EN_ADMIN_DESCRIPTION = '''
Used to demonstrate the capabilities of the admin panel.<br>
<br>
Data and actions in this mode do not affect the production environment and are periodically reset.
'''

RU_LOGIN_GREETINGS_MESSAGE = '''
<div class="text-h6 mb-1">
  Демо режим
</div>
<div class="text-caption">
  Логин: admin<br>
  Пароль: admin
</div>
'''
EN_LOGIN_GREETINGS_MESSAGE = '''
<div class="text-h6 mb-1">
  Demo mode
</div>
<div class="text-caption">
  Login: admin<br>
  Password: admin
</div>
'''

RU_PAYMENT_CREATE_RESULT = '''
<h3>Платеж успешно создан!</h3>
%(desctiption)s<br>
<br>
Данные платежа:<br>
gateway_id=%(gateway_id)s<br>
redirect_url: <a href="%(redirect_url)s" target="_blank"/>%(redirect_url)s</a>
'''
EN_PAYMENT_CREATE_RESULT = '''
<h3>The payment was created successfully!</h3>
%(desctiption)s<br>
<br>
Payment details:
gateway_id=%(gateway_id)s<br>
redirect_url: <a href="%(redirect_url)s" target="_blank"/>%(redirect_url)s</a>
'''
LANGUAGES_PHRASES = {
    'ru': {
        'admin_title': 'Brilliance Admin Демо',
        'admin_description': RU_ADMIN_DESCRIPTION,
        'login_greetings_message': RU_LOGIN_GREETINGS_MESSAGE,
        'created_at': 'Время создания',
        'graphs_example': 'Пример графиков',
        'amount': 'Сумма',
        'registry_checked': 'Реестр проверен',
        'registry_info_checked': 'Информация по реестру провайдера',
        'payments': 'Платежи',
        'payments_description': 'Статичные данные',
        'statistics': 'Статистика',
        'image': 'Изображение',
        'payments_search_fields': 'Доступные поля для поиска: id',
        'create_payment': 'Создать платеж',
        'create_payment_description': 'Создать платеж и отправить его на обработку в платежную систему.',
        'payment_create_result': RU_PAYMENT_CREATE_RESULT,
        'description': 'Описание',
        'status': 'Статус',
        'endpoint': 'Эндпоинт',
        'action_with_exception': 'Действие с ошибкой',
        'is_throw_error': 'Выбросить ошибку?',
        'throw_error': 'Пример ошибки валидации поля.',
        'exception_example': 'Пример ошибки исключения.',
        'merchants': 'Мерчанты',
        'terminals': 'Терминалы',
        'currencies': 'Валюты',
        'whitelist_ips': 'Белый список IP',
        'users': 'Пользователи',
        'field_not_found_in_schema': 'Поле "{field_slug}" не найдено среди доступных: {available}',
        'related_not_found': 'Ошибка при обновлении связей поля {field_slug}: запись {model} с ключем pk={pk} не найдена. Возможно запись более недоступна.',
    },
    'en': {
        'admin_title': 'Brilliance Admin Demo',
        'admin_description': EN_ADMIN_DESCRIPTION,
        'login_greetings_message': EN_LOGIN_GREETINGS_MESSAGE,
        'created_at': 'Created time',
        'graphs_example': 'Graphs example',
        'amount': 'Amount',
        'registry_checked': 'Registry checked',
        'registry_info_checked': 'Registry info checked',
        'payments': 'Payments',
        'payments_description': 'Static data',
        'statistics': 'Statistics',
        'create_payment_description': 'Create a payment and send it to the payment system for processing.',
        'image': 'Image',
        'payments_search_fields': 'Search fields: id',
        'create_payment': 'Create payment',
        'payment_create_result': EN_PAYMENT_CREATE_RESULT,
        'description': 'Description',
        'status': 'Status',
        'endpoint': 'Endpoint',
        'action_with_exception': 'Action with exception',
        'is_throw_error': 'Is throw error?',
        'throw_error': 'Example of a field validation error.',
        'exception_example': 'Exception example.',
        'merchants': 'Merchants',
        'terminals': 'Terminals',
        'currencies': 'Currencies',
        'whitelist_ips': 'Whitelist IPs',
        'users': 'Users',
        'field_not_found_in_schema': 'The field "{field_slug}" was not found among the available fields: {available}',
        'related_not_found': 'Error updating related field {field_slug}: {model} record with pk={pk} was not found. The record may no longer be available.',
    },
}
