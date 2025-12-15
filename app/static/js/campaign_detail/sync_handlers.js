/**
 * Sync Handlers - Обработчики синхронизации с Keitaro
 */

$(document).ready(function() {
    // Fetch streams from Keitaro
    $('#fetch-streams-btn').on('click', function() {
        const btn = $(this);
        const originalText = btn.text();
        btn.prop('disabled', true).html('Загрузка... <span class="spinner"></span>');
        
        $.ajax({
            url: `/campaigns/${window.campaignId}/fetch-streams/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    showToast(data.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.error, 'error');
                    btn.prop('disabled', false).text(originalText);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                btn.prop('disabled', false).text(originalText);
            }
        });
    });
    
    // Проверка синхронизации с Keitaro
    function checkSync() {
        $.ajax({
            url: `/campaigns/${window.campaignId}/check-sync/`,
            method: 'GET',
            success: function(data) {
                if (data.success && data.has_differences) {
                    $('#sync-warning').removeClass('hidden');
                }
            }
        });
    }
    
    // Автоматический fetch streams при переходе с параметром auto_fetch
    function autoFetchStreams() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auto_fetch') === 'true') {
            // Убираем параметр из URL
            const newUrl = window.location.pathname;
            window.history.replaceState({}, '', newUrl);
            
            // Автоматически выполняем fetch streams
            const btn = $('#fetch-streams-btn');
            const originalText = btn.text();
            btn.prop('disabled', true).html('Загрузка... <span class="spinner"></span>');
            
            $.ajax({
                url: `/campaigns/${window.campaignId}/fetch-streams/`,
                method: 'POST',
                headers: {'X-CSRFToken': window.csrfToken},
                success: function(data) {
                    if (data.success) {
                        showToast(data.message, 'success');
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showToast(data.error, 'error');
                        btn.prop('disabled', false).text(originalText);
                    }
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                    showToast(error, 'error');
                    btn.prop('disabled', false).text(originalText);
                }
            });
        }
    }
    
    // Проверяем синхронизацию при загрузке
    checkSync();
    
    // Автоматический fetch streams если нужно
    autoFetchStreams();
    
    // Push to Keitaro
    $(document).on('click', '.push-flow-btn', function() {
        const flowId = $(this).closest('.flow-container').data('flow-id');
        const btn = $(this);
        btn.prop('disabled', true).html('Отправка... <span class="spinner"></span>');
        
        $.ajax({
            url: `/campaigns/flow/${flowId}/push/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    showToast(data.message, 'success');
                    // Убираем зелёную подсветку с добавленных офферов после успешного пуша
                    $(`.flow-container[data-flow-id="${flowId}"] .offer-name`).removeClass('text-green-600 font-bold').addClass('text-gray-900');
                    // Убираем зелёную подсветку с изменённых share после успешного пуша
                    $(`.flow-container[data-flow-id="${flowId}"] span.font-medium`).removeClass('text-green-600 font-bold');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.error, 'error');
                    btn.prop('disabled', false).text('Push to Keitaro');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                btn.prop('disabled', false).text('Push to Keitaro');
            }
        });
    });
    
    // Cancel changes
    $(document).on('click', '.cancel-flow-btn', function() {
        const flowId = $(this).closest('.flow-container').data('flow-id');
        
        if (!confirm('Отменить все изменения?')) {
            return;
        }
        
        $.ajax({
            url: `/campaigns/flow/${flowId}/cancel/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    // Убираем зелёную подсветку с добавленных офферов при отмене
                    $(`.flow-container[data-flow-id="${flowId}"] .offer-name`).removeClass('text-green-600 font-bold').addClass('text-gray-900');
                    // Убираем зелёную подсветку с изменённых share при отмене
                    $(`.flow-container[data-flow-id="${flowId}"] span.font-medium`).removeClass('text-green-600 font-bold');
                    // Восстанавливаем удалённые офферы: возвращаем цвет, меняем кнопку, включаем булавку
                    $(`.flow-container[data-flow-id="${flowId}"] tr[data-removed="true"]`).each(function() {
                        const row = $(this);
                        const flowOfferId = row.data('flow-offer-id');
                        row.find('.offer-name').removeClass('text-gray-400').addClass('text-gray-900');
                        row.removeAttr('data-removed');
                        // Заменяем кнопку "Вернуть" на "Удалить"
                        const actionCell = row.find('td:last-child');
                        actionCell.html(`
                            <button class="remove-offer-btn text-red-600 hover:text-red-900"
                                    data-flow-offer-id="${flowOfferId}">
                                Удалить
                            </button>
                        `);
                        // Включаем булавку
                        row.find('.pin-share-btn').prop('disabled', false);
                    });
                    location.reload();
                } else {
                    showToast(data.error, 'error');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
            }
        });
    });
});
