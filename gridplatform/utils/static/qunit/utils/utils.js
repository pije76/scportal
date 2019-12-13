test('Test utils.hashHelpers.updateLocation', function () {
    var form = $('<form>');
    form.append('<input type="textfield" name="from_date" value="test_from_date">');
    form.append('<input type="textfield" name="to_date" value="test_to_date">');
    form.append('<input type="textfield" name="from_hour" value="test_from_hour">');
    form.append('<input type="textfield" name="to_hour" value="test_to_hour">');
    utils.hashHelpers.updateLocation('test', form);

    unit = ui.getHashValueFromKey('test');

    equal('test_from_date', unit['from_date']);
    equal('test_to_date', unit['to_date']);
    equal('test_from_hour', unit['from_hour']);
    equal('test_to_hour', unit['to_hour']);
});

test('Test utils.hashHelpers.setFormValues', function () {
    var form = $('<form>')
        formValues = {
            from_date: 'test_from_date',
            from_hour: 'test_from_hour',
            to_date: 'test_to_date',
            to_hour: 'test_to_hour'
        };
    form.append('<input type="textfield" name="from_date">');
    form.append('<input type="textfield" name="to_date">');
    form.append('<input type="textfield" name="from_hour">');
    form.append('<input type="textfield" name="to_hour">');

    utils.hashHelpers.setFormValues(formValues, form);

    equal('test_from_date', form.find('[name=from_date]').val());
    equal('test_to_date', form.find('[name=to_date]').val());
    equal('test_from_hour', form.find('[name=from_hour]').val());
    equal('test_to_hour', form.find('[name=to_hour]').val());
});

test('Test utils.hashHelpers.loadFromUrlHash', function() {
    var form = $('<form>'),
        callbackRan = false;
    form.append('<input type="textfield" name="from_date" value="test_from_date">');
    form.append('<input type="textfield" name="to_date" value="test_to_date">');
    form.append('<input type="textfield" name="from_hour" value="test_from_hour">');
    form.append('<input type="textfield" name="to_hour" value="test_to_hour">');
    utils.hashHelpers.updateLocation('test', form);

    utils.hashHelpers.loadFromUrlHash('test', form, function() {
        callbackRan = true;
    });

    ok(callbackRan, 'Callback called');
    equal('test_from_date', form.find('[name=from_date]').val());
    equal('test_to_date', form.find('[name=to_date]').val());
    equal('test_from_hour', form.find('[name=from_hour]').val());
    equal('test_to_hour', form.find('[name=to_hour]').val());

});
