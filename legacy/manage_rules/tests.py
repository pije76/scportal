from django.test import TestCase
from django.test.utils import override_settings

from gridplatform import trackuser
from gridplatform.users.models import User


@override_settings(ENCRYPTION_TESTMODE=True)
class RuleViewTest(TestCase):
    """
    This test setup is an anti-pattern.  Do not make new test cases inherit
    from it.
    """
    fixtures = ['super_user_and_customer.json']

    def setUp(self):
        """
        Setup test fixture as if we are logged in as some user called
        super.
        """
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})

        self.user = User.objects.get(id=self.client.session["_auth_user_id"])
        self.customer = self.user.customer
        trackuser._set_customer(self.customer)
        trackuser._set_user(self.user)

        assert self.user is trackuser.get_user()
        assert self.customer.id and self.customer == trackuser.get_customer()

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_get_rule_list(self):
        response = self.client.get("/rules/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_get_minimize_rule_form(self):
        response = self.client.get("/rules/minimizerule/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_get_triggered_rule_form(self):
        response = self.client.get("/rules/triggeredrule/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'XYZXYZXYZ')
