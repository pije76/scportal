from django.contrib import admin

from gridplatform.customer_datasources.models import CustomerDataSource


class CustomerDataSourceAdmin(admin.ModelAdmin):
    pass

admin.site.register(CustomerDataSource, CustomerDataSourceAdmin)