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
                                    <input type="number" 
                                           class="share-input w-20 px-2 py-1 border border-gray-300 rounded"
                                           value="${data.share}"
                                           min="0" 
                                           max="100"
                                           data-flow-offer-id="${data.flow_offer_id}">
                                    <button class="pin-share-btn text-gray-400" 
                                            data-flow-offer-id="${data.flow_offer_id}"
                                            data-pinned="false"
                                            title="Зафиксировать share">
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
                        Object.keys(data.all_shares).forEach(function(flowOfferId) {
                            const shareInput = $(`.share-input[data-flow-offer-id="${flowOfferId}"]`);
                            if (shareInput.length) {
                                const oldShare = shareInput.val();
                                const newShare = data.all_shares[flowOfferId];
                                // Обновляем только если значение изменилось
                                if (oldShare != newShare) {
                                    shareInput.val(newShare);
                                    // Подсвечиваем измененные share (постоянно, до пуша)
                                    shareInput.addClass('share-changed');
                                }
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
                    row.find('.share-input').val(0).prop('disabled', true);
                    // Добавляем атрибут для идентификации удалённых строк
                    row.attr('data-removed', 'true');
                    
                    // Обновляем share для всех офферов в потоке
                    if (data.all_shares) {
                        Object.keys(data.all_shares).forEach(function(flowOfferId) {
                            const shareInput = $(`.share-input[data-flow-offer-id="${flowOfferId}"]`);
                            if (shareInput.length && !shareInput.prop('disabled')) {
                                const oldShare = shareInput.val();
                                const newShare = data.all_shares[flowOfferId];
                                // Обновляем только если значение изменилось
                                if (oldShare != newShare) {
                                    shareInput.val(newShare);
                                    // Подсвечиваем измененные share (постоянно, до пуша)
                                    shareInput.addClass('share-changed');
                                }
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
    
    // Обновление share
    $(document).on('change', '.share-input', function() {
        const flowOfferId = $(this).data('flow-offer-id');
        const share = $(this).val();
        const flowId = $(this).closest('.flow-container').data('flow-id');
        const pinBtn = $(`.pin-share-btn[data-flow-offer-id="${flowOfferId}"]`);
        const isPinned = pinBtn.data('pinned');
        const input = $(this);
        
        // Сохраняем предыдущее значение для отката при ошибке
        if (!input.data('previous-value')) {
            input.data('previous-value', input.val());
        }
        
        // Подсветка изменения
        input.addClass('share-changed');
        
        $.ajax({
            url: `/campaigns/flow-offer/${flowOfferId}/update-share/`,
            method: 'POST',
            headers: {'X-CSRFToken': window.csrfToken},
            data: {
                share: share,
                // Не передаём is_pinned, чтобы view автоматически закреплял при ручном вводе
            },
            success: function(data) {
                if (data.success && data.is_valid) {
                    markFlowAsEdited(flowId);
                    
                    // Если значение было ограничено - показываем предупреждение
                    if (data.warning) {
                        showToast(data.warning, 'warning');
                        // Обновляем значение в поле, если оно было ограничено
                        if (data.limited_share !== undefined) {
                            input.val(data.limited_share);
                        }
                    } else {
                        showToast('Share обновлён', 'success');
                    }
                    
                    // Автоматически закрепляем оффер (обновляем кнопку pin)
                    pinBtn.data('pinned', 'true');
                    pinBtn.removeClass('text-gray-400').addClass('text-blue-600');
                    
                    // Обновляем share для всех офферов в потоке
                    if (data.all_shares) {
                        Object.keys(data.all_shares).forEach(function(foId) {
                            const shareInput = $(`.share-input[data-flow-offer-id="${foId}"]`);
                            if (shareInput.length && !shareInput.prop('disabled')) {
                                const foIdNum = parseInt(foId);
                                const flowOfferIdNum = parseInt(flowOfferId);
                                const oldShare = shareInput.val();
                                const newShare = data.all_shares[foId];
                                
                                // Обновляем все офферы, включая текущий (если значение было ограничено)
                                if (foIdNum == flowOfferIdNum) {
                                    // Для текущего обновляем только если значение было ограничено
                                    if (data.limited_share !== undefined && oldShare != newShare) {
                                        shareInput.val(newShare);
                                    }
                                } else {
                                    // Для остальных обновляем если значение изменилось
                                    if (oldShare != newShare) {
                                        shareInput.val(newShare);
                                        // Подсвечиваем измененные share (постоянно, до пуша)
                                        shareInput.addClass('share-changed');
                                    }
                                }
                            }
                        });
                    }
                    
                    // Подсветка остается до пуша в Keitaro
                } else {
                    input.addClass('invalid-input');
                    showToast('Ошибка валидации: ' + (data.error || 'Неверное значение'), 'error');
                    setTimeout(() => {
                        input.removeClass('invalid-input');
                        // Восстанавливаем предыдущее значение при ошибке
                        input.val(data.previous_share || input.data('previous-value') || 0);
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
                    // Убираем подсветку со всех share в потоке после успешного пуша
                    $(`.flow-container[data-flow-id="${flowId}"] .share-input`).removeClass('share-changed');
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

