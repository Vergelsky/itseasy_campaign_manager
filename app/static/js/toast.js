/**
 * Toast notification system
 * Универсальная система уведомлений для всего приложения
 */

function showToast(message, type = 'success') {
    // Удаляем предыдущие toast, чтобы не накапливались
    $('.toast').remove();
    
    const icons = {
        'success': '✓',
        'error': '✗',
        'warning': '⚠',
        'info': 'ℹ'
    };
    
    const titles = {
        'success': 'Успешно',
        'error': 'Ошибка',
        'warning': 'Внимание',
        'info': 'Информация'
    };
    
    const toast = $(`
        <div class="toast ${type}">
            <p class="font-semibold">${icons[type] || 'ℹ'} ${titles[type] || 'Уведомление'}</p>
            <p class="text-sm mt-1">${message}</p>
        </div>
    `);
    
    $('body').append(toast);
    
    // Показываем с анимацией
    setTimeout(() => {
        toast.addClass('show');
    }, 10);
    
    // Автоматически скрываем через разное время в зависимости от типа
    const duration = type === 'error' ? 5000 : type === 'warning' ? 4000 : 3000;
    
    setTimeout(() => {
        toast.removeClass('show');
        setTimeout(() => {
            toast.fadeOut(300, function() {
                $(this).remove();
            });
        }, 100);
    }, duration);
}

