/**
 * Campaign List JavaScript
 * Управление списком кампаний и созданием новых
 */

$(document).ready(function() {
    let selectedOfferId = null;
    
    // Открытие модального окна создания кампании
    $('#create-campaign-btn, #create-campaign-btn-empty').on('click', function() {
        $('#create-campaign-modal').removeClass('hidden');
    });
    
    // Закрытие модального окна
    $('#close-modal-btn, #cancel-create-btn').on('click', function() {
        $('#create-campaign-modal').addClass('hidden');
        $('#create-campaign-form')[0].reset();
        $('#id_offer_id').val('');
        selectedOfferId = null;
    });
    
    // Закрытие при клике вне модального окна
    $('#create-campaign-modal').on('click', function(e) {
        if ($(e.target).attr('id') === 'create-campaign-modal') {
            $(this).addClass('hidden');
            $('#create-campaign-form')[0].reset();
            $('#id_offer_id').val('');
            selectedOfferId = null;
        }
    });
    
    // Автодополнение офферов
    $('#id_offer_name').on('input', function() {
        const input = $(this);
        const container = input.parent();
        const query = input.val().trim();
        
        if (query.length < 2) {
            container.find('.autocomplete-results').remove();
            return;
        }
        
        $.ajax({
            url: window.offerAutocompleteUrl || '/campaigns/offers/autocomplete/',
            method: 'GET',
            data: {q: query},
            success: function(data) {
                container.find('.autocomplete-results').remove();
                
                if (data.results && data.results.length > 0) {
                    const resultsDiv = $('<div class="autocomplete-results absolute z-10 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"></div>');
                    
                    data.results.forEach(function(offer) {
                        const item = $('<div class="px-4 py-2 hover:bg-gray-100 cursor-pointer">' + offer.name + '</div>');
                        item.on('click', function() {
                            input.val(offer.name);
                            $('#id_offer_id').val(offer.id);
                            selectedOfferId = offer.id;
                            resultsDiv.remove();
                        });
                        resultsDiv.append(item);
                    });
                    
                    container.append(resultsDiv);
                }
            }
        });
    });
    
    // Скрытие автодополнения при клике вне
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.offer-autocomplete, .autocomplete-results').length) {
            $('.autocomplete-results').remove();
        }
    });
    
    // Отправка формы создания кампании
    $('#create-campaign-form').on('submit', function(e) {
        e.preventDefault();
        
        const offerId = $('#id_offer_id').val();
        if (!offerId) {
            showToast('Пожалуйста, выберите оффер из списка', 'warning');
            return;
        }
        
        const formData = {
            name: $('#id_name').val(),
            geo_codes: $('#id_geo_codes').val(),
            offer_id: offerId,
            offer_name: $('#id_offer_name').val()
        };
        
        const submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true).text('Создание...');
        
        $.ajax({
            url: window.createCampaignUrl || '/campaigns/create/',
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken
            },
            data: formData,
            success: function(data) {
                if (data.success) {
                    showToast(data.message, 'success');
                    $('#create-campaign-modal').addClass('hidden');
                    $('#create-campaign-form')[0].reset();
                    setTimeout(() => {
                        if (data.campaign_id) {
                            // Добавляем параметр auto_fetch для автоматического fetch streams
                            const url = (window.campaignDetailUrlTemplate || '/campaigns/0/').replace('0', data.campaign_id) + '?auto_fetch=true';
                            window.location.href = url;
                        } else {
                            location.reload();
                        }
                    }, 1000);
                } else {
                    showToast(data.error, 'error');
                    submitBtn.prop('disabled', false).text('Создать');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                submitBtn.prop('disabled', false).text('Создать');
            }
        });
    });
    
    // Синхронизация кампаний
    $('#sync-campaigns-btn, #sync-campaigns-btn-empty').on('click', function() {
        const btn = $(this);
        btn.prop('disabled', true).text('Синхронизация...');
        
        $.ajax({
            url: window.syncCampaignsUrl || '/campaigns/sync-campaigns/',
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken
            },
            success: function(data) {
                if (data.success) {
                    showToast(data.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast(data.error, 'error');
                    btn.prop('disabled', false).text('Синхронизировать с Keitaro');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Неизвестная ошибка';
                showToast(error, 'error');
                btn.prop('disabled', false).text('Синхронизировать с Keitaro');
            }
        });
    });
    
    // Загрузка статистики
    function loadStats() {
        const campaignIds = [];
        $('tr[data-campaign-id]').each(function() {
            campaignIds.push($(this).data('campaign-id'));
        });
        
        if (campaignIds.length === 0) {
            return;
        }
        
        $.ajax({
            url: window.campaignStatsUrl || '/campaigns/stats/',
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken
            },
            data: {
                'campaign_ids[]': campaignIds
            },
            success: function(data) {
                if (data.success && data.stats) {
                    // Обновляем статистику в таблице
                    $.each(data.stats, function(campaignId, stats) {
                        const row = $(`tr[data-campaign-id="${campaignId}"]`);
                        row.find('.stat-clicks').text(stats.clicks || 0);
                        row.find('.stat-conversions').text(stats.conversions || 0);
                        row.find('.stat-cr').text((stats.cr || 0).toFixed(2));
                        row.find('.stat-revenue').text('$' + (stats.revenue || 0).toFixed(2));
                        row.find('.stat-cost').text('$' + (stats.cost || 0).toFixed(2));
                        
                        const profit = stats.profit || 0;
                        const profitCell = row.find('.stat-profit');
                        profitCell.text('$' + profit.toFixed(2));
                        if (profit > 0) {
                            profitCell.removeClass('text-gray-500').addClass('text-green-600 font-semibold');
                        } else if (profit < 0) {
                            profitCell.removeClass('text-gray-500').addClass('text-red-600 font-semibold');
                        }
                        
                        const roi = stats.roi || 0;
                        const roiCell = row.find('.stat-roi');
                        roiCell.text(roi.toFixed(2));
                        if (roi > 0) {
                            roiCell.removeClass('text-gray-500').addClass('text-green-600 font-semibold');
                        } else if (roi < 0) {
                            roiCell.removeClass('text-gray-500').addClass('text-red-600 font-semibold');
                        }
                    });
                    
                    if (data.warning) {
                        showToast(data.warning, 'warning');
                    }
                }
            },
            error: function(xhr) {
                showToast('Не удалось загрузить статистику', 'error');
            }
        });
    }
    
    // Загружаем статистику при загрузке страницы
    loadStats();
});

