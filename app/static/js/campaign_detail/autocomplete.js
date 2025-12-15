/**
 * Autocomplete - Автодополнение офферов
 */

// Инициализация автодополнения офферов
$(document).ready(function() {
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
    
    // Скрыть автодополнение при клике вне
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.offer-autocomplete, .autocomplete-results').length) {
            $('.autocomplete-results').remove();
        }
    });
});
