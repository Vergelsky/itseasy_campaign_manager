/**
 * UI Utilities - Утилиты для обновления интерфейса
 */

// Глобальная переменная для хранения выбранного оффера
var selectedOfferId = null;

/**
 * Обновление значений share в UI
 */
function updateShareValues(flowId, allShares, excludeId = null) {
    if (!allShares) return;
    Object.keys(allShares).forEach(function(foId) {
        if (excludeId && parseInt(foId) === parseInt(excludeId)) return;
        const shareSpan = $(`tr[data-flow-offer-id="${foId}"] span.font-medium`);
        if (shareSpan.length) {
            const oldShare = parseInt(shareSpan.text().replace('%', '')) || 0;
            const newShare = parseInt(allShares[foId]) || 0;
            shareSpan.text(newShare + '%');
            if (oldShare !== newShare) {
                shareSpan.addClass('text-green-600 font-bold');
            }
        }
    });
}

/**
 * Отметить поток как редактированный
 */
function markFlowAsEdited(flowId) {
    const flowContainer = $(`.flow-container[data-flow-id="${flowId}"]`);
    flowContainer.addClass('edited-flow');
    flowContainer.find('.flow-actions').show();
}
