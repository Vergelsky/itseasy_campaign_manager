/**
 * Campaign Detail JavaScript
 * Управление офферами в потоках кампании
 */

// Toast notification helper
function showToast(message, type = 'success') {
    const toast = $(`
        <div class="toast ${type}">
            <p class="font-semibold">${type === 'success' ? '✓ Успешно' : type === 'error' ? '✗ Ошибка' : '⚠ Внимание'}</p>
            <p class="text-sm mt-1">${message}</p>
        </div>
    `);
    
    $('body').append(toast);
    
    setTimeout(() => {
        toast.fadeOut(300, function() {
            $(this).remove();
        });
    }, 3000);
}

$(document).ready(function() {
    let selectedOfferId = null;
    let originalFlowData = {};  // Для отмены изменений
    
    // Сохраняем оригинальные данные потоков
    $('.flow-container').each(function() {
        const flowId = $(this).data('flow-id');
        originalFlowData[flowId] = $(this).html();
    });
    
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
    
    // Проверяем синхронизацию при загрузке
    checkSync();
    
    // Автодополнение офферов
    $('.offer-autocomplete').on('input', function() {
        const input = $(this);
        const query = input.val().trim();
        
        if (query.length < 2) {
            input.next('.autocomplete-results').remove();
            return;
        }
        
        $.ajax({
            url: '/campaigns/offers/autocomplete/',
            method: 'GET',
            data: {q: query},
            success: function(data) {
                // Удаляем старые результаты
                input.next('.autocomplete-results').remove();
                
                if (data.results && data.results.length > 0) {
                    const resultsDiv = $('<div class="autocomplete-results absolute z-10 bg-white border border-gray-300 rounded-lg shadow-lg mt-1 max-h-60 overflow-y-auto"></div>');
                    
                    data.results.forEach(function(offer) {
                        const item = $('<div class="px-4 py-2 hover:bg-gray-100 cursor-pointer">' + offer.name + '</div>');
                        item.on('click', function() {
                            input.val(offer.name);
                            input.data('selected-offer-id', offer.id);
                            selectedOfferId = offer.id;
                            resultsDiv.remove();
                        });
                        resultsDiv.append(item);
                    });
                    
                    input.after(resultsDiv);
                }
            }
        });
    });
    
    // Добавление оффера
    $('.add-offer-btn').on('click', function() {
        const flowId = $(this).data('flow-id');
        const input = $(`.offer-autocomplete[data-flow-id="${flowId}"]`);
        const offerId = input.data('selected-offer-id') || selectedOfferId;
        
        if (!offerId) {
            showToast('Пожалуйста, выберите оффер из списка', 'warning');
            return;
        }
        
        const btn = $(this);
        btn.prop('disabled', true).html('Добавление... <span class="spinner"></span>');
        
        $.ajax({
            url: `/campaigns/flow/${flowId}/add-offer/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            data: {offer_id: offerId},
            success: function(data) {
                if (data.success) {
                    markFlowAsEdited(flowId);
                    showToast('Оффер добавлен', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.error, 'error');
                    btn.prop('disabled', false).text('Добавить');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                btn.prop('disabled', false).text('Добавить');
            }
        });
    });
    
    // Удаление оффера
    $(document).on('click', '.remove-offer-btn', function() {
        const flowOfferId = $(this).data('flow-offer-id');
        const flowId = $(this).closest('.flow-container').data('flow-id');
        const row = $(this).closest('tr');
        
        if (!confirm('Удалить этот оффер?')) {
            return;
        }
        
        // Визуально отмечаем как удаляемый
        row.find('.offer-name').addClass('text-removed');
        row.find('.share-input').val(0).prop('disabled', true);
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/remove/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    markFlowAsEdited(flowId);
                    showToast('Оффер удалён', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.error, 'error');
                    row.find('.offer-name').removeClass('text-removed');
                    row.find('.share-input').prop('disabled', false);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                row.find('.offer-name').removeClass('text-removed');
                row.find('.share-input').prop('disabled', false);
            }
        });
    });
    
    // Обновление share
    $(document).on('change', '.share-input', function() {
        const flowOfferId = $(this).data('flow-offer-id');
        const share = $(this).val();
        const flowId = $(this).closest('.flow-container').data('flow-id');
        const isPinned = $(`.pin-share-btn[data-flow-offer-id="${flowOfferId}"]`).data('pinned');
        const input = $(this);
        
        // Подсветка изменения
        input.addClass('share-changed');
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/update-share/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            data: {
                share: share,
                is_pinned: isPinned
            },
            success: function(data) {
                if (data.success && data.is_valid) {
                    markFlowAsEdited(flowId);
                    showToast('Share обновлён', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    input.addClass('invalid-input');
                    showToast('Ошибка валидации: ' + (data.error || 'Неверное значение'), 'error');
                    setTimeout(() => {
                        input.removeClass('invalid-input');
                        location.reload();
                    }, 2000);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                input.addClass('invalid-input');
                showToast(error, 'error');
                setTimeout(() => {
                    input.removeClass('invalid-input');
                }, 2000);
            }
        });
    });
    
    // Фиксация share
    $(document).on('click', '.pin-share-btn', function() {
        const flowOfferId = $(this).data('flow-offer-id');
        const isPinned = $(this).data('pinned');
        const newPinned = !isPinned;
        const share = $(`.share-input[data-flow-offer-id="${flowOfferId}"]`).val();
        const flowId = $(this).closest('.flow-container').data('flow-id');
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/update-share/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            data: {
                share: share,
                is_pinned: newPinned
            },
            success: function(data) {
                if (data.success) {
                    $(this).data('pinned', newPinned);
                    $(this).toggleClass('text-blue-600 text-gray-400');
                    markFlowAsEdited(flowId);
                }
            }.bind(this),
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                alert('Ошибка: ' + error);
            }
        });
    });
    
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
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                alert('Ошибка: ' + error);
            }
        });
    });
    
    // Отметить поток как редактированный
    function markFlowAsEdited(flowId) {
        const flowContainer = $(`.flow-container[data-flow-id="${flowId}"]`);
        flowContainer.addClass('edited-flow');
        flowContainer.find('.flow-actions').show();
    }
    
    // Скрыть автодополнение при клике вне
    $(document).on('click', function(e) {
        if (!$(e.target).hasClass('offer-autocomplete')) {
            $('.autocomplete-results').remove();
        }
    });
});

