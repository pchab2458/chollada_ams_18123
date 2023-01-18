from django.db import models
from django.urls import reverse

from django.contrib.auth import get_user_model

CUser = get_user_model()  # Custom User


class Room_type(models.Model):
    desc = models.CharField(max_length=250)
    rate = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    def __str__(self):
        return self.desc


class Room(models.Model):
    room_type = models.ForeignKey(Room_type, on_delete=models.CASCADE)
    room_no = models.CharField(max_length=4)

    def __str__(self):
        return self.room_no


class Extra(models.Model):
    desc = models.CharField(max_length=100)
    cpu = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    def __str__(self):
        return self.desc


class Billing(models.Model):
    STATUS_CHOICE = (('open', 'OPEN'), ('close', 'CLOSE'),)

    bill_ref = models.CharField(max_length=6)
    bill_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=5, choices=STATUS_CHOICE, default='open')
    tenant_name = models.CharField(max_length=100)
    room_no = models.CharField(max_length=4)
    room_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    room_acc_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    electricity_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    water_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    common_ser_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    other_ser_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    overdue_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    adjust = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    bill_total = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    payment_date = models.DateField(blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    cf_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    late_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    maint_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        ordering = ('-bill_date',)

    def __str__(self):
        return 'Bill for room number: {} Status: {}'.format(self.room_no, self.status)

    def get_absolute_url(self):
        return reverse('pay_bill', args=[str(self.bill_ref)])


class TenantProfile(models.Model):
    # tenant = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.OneToOneField(CUser, on_delete=models.CASCADE)
    pin = models.CharField(max_length=13, unique=True)
    phone = models.CharField(max_length=10)
    room_no = models.OneToOneField(Room, on_delete=models.CASCADE, unique=True)
    term = models.PositiveSmallIntegerField(default=12)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    deposit = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    deduct = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    cum_ovd = models.DecimalField(max_digits=7, decimal_places=2, blank=True, default=0)
    adjust = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)
    extra = models.ManyToManyField(Extra)
    bill_date = models.DateField(auto_now=True, blank=True)
    # USE PLACEHOLDER (NO DEFAULT VALUE) INITIAL VALUE TO BE PROVIDED WHEN SAVE TO DB
    elec_unit = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    water_unit = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    late_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)  # no need to use placeholder
    maint_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    def __str__(self):
        return 'Profile for user {}'.format(self.tenant.first_name)

    def get_absolute_url(self):
        return reverse('fill_bill', args=[self.room_no])

    #
    # def get_absolute_url(self):
    #     return reverse('fill_bill', args=[self.room_no])

    # def get_absolute_url(self):
    #     return reverse('blog:post_detail',
    #                    args=[self.publish.year,
    #                          self.publish.month,
    #                          self.publish.day,
    #                          self.slug])


class MaintenanceCharge(models.Model):
    STATUS_CHOICE = (('open', 'OPEN'), ('close', 'CLOSE'),)

    room_no = models.ForeignKey(Room, on_delete=models.CASCADE)
    desc = models.CharField(max_length=100)
    # job_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    job_cost = models.DecimalField(max_digits=7, decimal_places=2)  # use placeholder (no default)
    status = models.CharField(max_length=5, choices=STATUS_CHOICE, default='open')
    job_date = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-job_date',)
