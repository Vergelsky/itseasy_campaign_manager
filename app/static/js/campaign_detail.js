/**
 * Campaign Detail JavaScript
 * Управление офферами в потоках кампании
 * 
 * Использует общую функцию showToast из toast.js
 */

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
        const container = input.parent(); // Контейнер с position: relative
        const query = input.val().trim();
        
        if (query.length < 2) {
            container.find('.autocomplete-results').remove();
            return;
        }
        
        $.ajax({
            url: '/campaigns/offers/autocomplete/',
            method: 'GET',
            data: {q: query},
            success: function(data) {
                // Удаляем старые результаты
                container.find('.autocomplete-results').remove();
                
                if (data.results && data.results.length > 0) {
                    const resultsDiv = $('<div class="autocomplete-results"></div>');
                    
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
                    
                    // Вставляем результаты в контейнер с position: relative
                    container.append(resultsDiv);
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
                    // Очищаем поле ввода
                    input.val('').data('selected-offer-id', null);
                    selectedOfferId = null;
                    btn.prop('disabled', false).text('Добавить');
                    // Добавляем строку в таблицу динамически
                    const tbody = $(`.flow-container[data-flow-id="${flowId}"] .flow-offers-tbody`);
                    const newRow = $(`
                        <tr data-flow-offer-id="${data.flow_offer_id}">
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 offer-name">
                                ${data.offer_name}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                <div class="flex items-center space-x-2">
                                    <span class="font-medium">${data.share}%</span>
                                    <button class="pin-share-btn text-gray-400" 
                                            data-flow-offer-id="${data.flow_offer_id}"
                                            data-pinned="false"
                                            title="Не закреплён - нажмите чтобы закрепить">
                                        📌
                                    </button>
                                </div>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                    active
                                </span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <button class="remove-offer-btn text-red-600 hover:text-red-900"
                                        data-flow-offer-id="${data.flow_offer_id}">
                                    Удалить
                                </button>
                            </td>
                        </tr>
                    `);
                    tbody.append(newRow);
                    // Применяем зелёный стиль Tailwind к добавленному офферу
                    newRow.find('.offer-name').removeClass('text-gray-900').addClass('text-green-600 font-bold');
                    
                    // Обновляем share для всех офферов в потоке
                    if (data.all_shares) {
                        Object.keys(data.all_shares).forEach(function(foId) {
                            // Ищем span с share (не td с названием оффера)
                            const shareSpan = $(`tr[data-flow-offer-id="${foId}"] span.font-medium`);
                            if (shareSpan.length) {
                                shareSpan.text(data.all_shares[foId] + '%');
                            }
                        });
                    }
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
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/remove/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    markFlowAsEdited(flowId);
                    showToast('Оффер помечен для удаления', 'success');
                    // Отмечаем строку красным цветом (используя Tailwind)
                    row.find('.offer-name').removeClass('text-gray-900 text-green-600 font-bold').addClass('text-red-600 font-bold');
                    // Добавляем атрибут для идентификации удалённых строк
                    row.attr('data-removed', 'true');
                    
                    // Обновляем share для всех офферов в потоке
                    if (data.all_shares) {
                        Object.keys(data.all_shares).forEach(function(foId) {
                            // Ищем span с share (не td с названием оффера)
                            const shareSpan = $(`tr[data-flow-offer-id="${foId}"] span.font-medium`);
                            if (shareSpan.length) {
                                shareSpan.text(data.all_shares[foId] + '%');
                            }
                        });
                    }
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
    
    // Переключение закрепления оффера
    $(document).on('click', '.pin-share-btn', function() {
        const pinBtn = $(this);
        if (pinBtn.prop('disabled')) {
            return; // Не обрабатываем клики по заблокированным булавкам
        }
        
        const flowOfferId = pinBtn.data('flow-offer-id');
        // Корректно определяем текущее состояние (может быть 'true', 'false', true, false)
        const currentPinned = pinBtn.data('pinned');
        const isPinned = currentPinned === 'true' || currentPinned === true;
        const flowId = pinBtn.closest('.flow-container').data('flow-id');
        
        // Оптимистичное обновление UI сразу при клике
        const newPinned = !isPinned;
        pinBtn.data('pinned', newPinned);
        pinBtn.removeClass('text-gray-400 text-blue-600');
        if (newPinned) {
            pinBtn.addClass('text-blue-600');
            pinBtn.attr('title', 'Закреплён - нажмите чтобы раззакрепить');
        } else {
            pinBtn.addClass('text-gray-400');
            pinBtn.attr('title', 'Не закреплён - нажмите чтобы закрепить');
        }
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/toggle-pin/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            success: function(data) {
                if (data.success) {
                    // Обновляем состояние булавки на основе ответа сервера
                    const pinned = data.is_pinned !== undefined ? data.is_pinned : newPinned;
                    pinBtn.data('pinned', pinned);
                    pinBtn.removeClass('text-gray-400 text-blue-600');
                    if (pinned) {
                        pinBtn.addClass('text-blue-600');
                        pinBtn.attr('title', 'Закреплён - нажмите чтобы раззакрепить');
                    } else {
                        pinBtn.addClass('text-gray-400');
                        pinBtn.attr('title', 'Не закреплён - нажмите чтобы закрепить');
                    }
                    markFlowAsEdited(flowId);
                    showToast(pinned ? 'Оффер закреплён' : 'Оффер раззакреплён', 'success');
                    
                    // Обновляем share для всех офферов в потоке
                    if (data.all_shares) {
                        Object.keys(data.all_shares).forEach(function(foId) {
                            // Ищем span с share (не td с названием оффера)
                            const shareSpan = $(`tr[data-flow-offer-id="${foId}"] span.font-medium`);
                            if (shareSpan.length) {
                                shareSpan.text(data.all_shares[foId] + '%');
                            }
                        });
                    }
                } else {
                    // Откатываем визуальное состояние при ошибке
                    pinBtn.data('pinned', isPinned);
                    pinBtn.removeClass('text-gray-400 text-blue-600');
                    if (isPinned) {
                        pinBtn.addClass('text-blue-600');
                        pinBtn.attr('title', 'Закреплён - нажмите чтобы раззакрепить');
                    } else {
                        pinBtn.addClass('text-gray-400');
                        pinBtn.attr('title', 'Не закреплён - нажмите чтобы закрепить');
                    }
                    showToast(data.error || 'Ошибка при изменении закрепления', 'error');
                }
            },
            error: function(xhr) {
                // Откатываем визуальное состояние при ошибке
                pinBtn.data('pinned', isPinned);
                pinBtn.removeClass('text-gray-400 text-blue-600');
                if (isPinned) {
                    pinBtn.addClass('text-blue-600');
                    pinBtn.attr('title', 'Закреплён - нажмите чтобы раззакрепить');
                } else {
                    pinBtn.addClass('text-gray-400');
                    pinBtn.attr('title', 'Не закреплён - нажмите чтобы закрепить');
                }
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
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
                    // Убираем зелёную подсветку с добавленных офферов после успешного пуша
                    $(`.flow-container[data-flow-id="${flowId}"] .offer-name`).removeClass('text-green-600 font-bold').addClass('text-gray-900');
                    // Удаляем строки, помеченные для удаления
                    $(`.flow-container[data-flow-id="${flowId}"] tr[data-removed="true"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
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
                    // Убираем подсветку со всех share в потоке при отмене
                    $(`.flow-container[data-flow-id="${flowId}"] .share-input`).removeClass('share-changed');
                    // Убираем зелёную подсветку с добавленных офферов при отмене
                    $(`.flow-container[data-flow-id="${flowId}"] .offer-name`).removeClass('text-green-600 font-bold').addClass('text-gray-900');
                    // Возвращаем нормальный цвет удалённым офферам и включаем input
                    $(`.flow-container[data-flow-id="${flowId}"] tr[data-removed="true"]`).each(function() {
                        $(this).find('.offer-name').removeClass('text-red-600 font-bold').addClass('text-gray-900');
                        $(this).find('.share-input').prop('disabled', false);
                        $(this).removeAttr('data-removed');
                    });
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
        if (!$(e.target).closest('.offer-autocomplete, .autocomplete-results').length) {
            $('.autocomplete-results').remove();
        }
    });
});

