test('Test ui is an object', function () {
    equal(typeof(ui), "object");
});

test('Test ui.parseNumber', function () {
    thousandSeparator = get_format('THOUSAND_SEPARATOR'),
    decimalSeparator = get_format('DECIMAL_SEPARATOR');
    unit = ui.parseNumber("10" + thousandSeparator + "000" + decimalSeparator + "42");
    equal(unit, 10000.42);
});

test('Test ui.formatNumber', function () {
    thousandSeparator = get_format('THOUSAND_SEPARATOR'),
    decimalSeparator = get_format('DECIMAL_SEPARATOR');
    unit = ui.formatNumber(10000.421337, 2);
    equal(unit, "10" + thousandSeparator + "000" + decimalSeparator + "42");
});

test('Test ui.getQueryStrings', function () {
    unit = ui.getQuerystrings('test.html?because=internet&get=beer');
    equal('internet', unit['because']);
    equal('beer', unit['get']);
});

test('Test ui.updateLocationHash with empty hash', function () {
    window.location.hash = "";

	ui.updateLocationHash({something: 'test'});
    unit = JSON.parse(decodeURIComponent(window.location.hash.replace(/^#/, '')));
    equal('test', unit['something']);
    window.location.hash = "";
});

test('Test ui.updateLocationHash no override', function () {
    window.location.hash = encodeURIComponent(JSON.stringify({testing: 'beer'}));

	ui.updateLocationHash({something: 'test'});
    unit = JSON.parse(decodeURIComponent(window.location.hash.replace(/^#/, '')));
    equal('test', unit['something']);
    equal('beer', unit['testing']);
    window.location.hash = "";

});

test('Test ui.updateLocationHash override', function () {
    window.location.hash = encodeURIComponent(JSON.stringify({testing: 'beer'}));

	ui.updateLocationHash({something: 'test'}, true);
    unit = JSON.parse(decodeURIComponent(window.location.hash.replace(/^#/, '')));
    equal('test', unit['something']);
    equal(undefined, unit['testing']);
    window.location.hash = "";

});

test('Test ui.getHashValueFromKey', function () {
    ui.updateLocationHash({something: 'test'}, true);
    unit = ui.getHashValueFromKey('something');
    equal('test', unit);
    window.location.hash = "";
});

test('Test ui.generateStringHash generates same hash for qual strings', function () {
    equal(ui.generateStringHash('string'), ui.generateStringHash('string'));
});

test('Test ui.generateStringHash generates different hash for different strings', function () {
    notEqual(ui.generateStringHash('string1'), ui.generateStringHash('string2'));
});

test('Test ui.icon no size no spin', function () {
    unit = ui.icon('times');
    equal('<i class="fa fa-times"></i>', unit);
});

test('Test ui.icon with size', function () {
    unit = ui.icon('times', 'xl');
    equal('<i class="fa fa-times fa-xl"></i>', unit);
});

test('Test ui.icon with spin', function () {
    unit = ui.icon('times', undefined, true);
    equal('<i class="fa fa-times fa-spin"></i>', unit);
});
