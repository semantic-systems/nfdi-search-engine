$(function () {      

    $('input[name="report-daterange"]').daterangepicker({
        // autoUpdateInput: false,
        locale: {
            cancelLabel: 'Clear',
            format: 'MMMM D, YYYY',
        },
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    });

    $('input[name="report-daterange"]').on('apply.daterangepicker', function (ev, picker) {
        $(this).val(picker.startDate.format('MMMM D, YYYY') + ' - ' + picker.endDate.format('MMMM D, YYYY'));
    });

    $('input[name="report-daterange"]').on('cancel.daterangepicker', function (ev, picker) {
        alert('Date filter will be set to Last 7 days.')
        $(this).val(moment().subtract(6, 'days').format('MMMM D, YYYY') + ' - ' + moment().format('MMMM D, YYYY'));
    });

    $('#btn_refresh').on('click', function () {
        new_url = $(this).attr('href') + '/' + encodeURIComponent($('input[name="report-daterange"]').val())
        window.location.href = new_url;
        return false;
    });   

});