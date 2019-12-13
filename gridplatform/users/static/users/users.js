$(function() {
	// Cancel button
	$('body').on('click', '#userprofile-modal .btn-warning', function(event) {
		event.preventDefault();
		$('#userprofile-modal').modal('hide');
	});

	$('body').on('submit', '#userprofile-modal form', function(event) {
		var form = $(this)
		event.preventDefault();
		jQuery.post(form.attr('action'), form.serialize(), function(data) {
			if (data === "success"){
				$('#userprofile-modal').modal('hide');
			} else {
				$('#userprofile-modal .profileform').html(data);
			}
		});
	});


	$('body').on('show.bs.modal', '#userprofile-modal', function() {
		var modal = $(this)
		jQuery.get(modal.data('form-url'), function(data) {
			$('#userprofile-modal .profileform').html(data);
		});
	});
});
